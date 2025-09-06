#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
网络检查模块
负责域名的网络连接检查、重定向处理等功能
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional, Set
from urllib.parse import urlparse, urljoin

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from config import Config, ERROR_MESSAGES
from logger import logger
from domain_manager import DomainInfo


class NetworkChecker:
    """网络检查器"""
    
    def __init__(self):
        self.timeout = Config.REQUEST_TIMEOUT
        self.retry_attempts = Config.RETRY_ATTEMPTS
        self.headers = Config.HEADERS.copy()
        self.session = self._create_session()
        
        # 线程池用于并发检查
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # 缓存最近的检查结果
        self.check_cache: Dict[str, Tuple[bool, float]] = {}
        self.cache_duration = 300  # 5分钟缓存
    
    def _create_session(self) -> requests.Session:
        """创建配置好的requests会话"""
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=Config.MAX_RETRIES,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 设置默认headers
        session.headers.update(self.headers)
        
        return session
    
    def _is_cache_valid(self, url: str) -> bool:
        """检查缓存是否有效"""
        if url not in self.check_cache:
            return False
        
        _, timestamp = self.check_cache[url]
        return time.time() - timestamp < self.cache_duration
    
    def _get_cached_result(self, url: str) -> Optional[bool]:
        """获取缓存的检查结果"""
        if self._is_cache_valid(url):
            result, _ = self.check_cache[url]
            return result
        return None
    
    def _cache_result(self, url: str, result: bool):
        """缓存检查结果"""
        self.check_cache[url] = (result, time.time())
    
    def check_domain_simple(self, url: str) -> Tuple[bool, str, Optional[str]]:
        """简单的域名检查（HEAD请求）"""
        try:
            # 检查缓存
            cached_result = self._get_cached_result(url)
            if cached_result is not None:
                logger.debug(f"使用缓存结果: {url} -> {cached_result}")
                return cached_result, "缓存结果", None
            
            logger.debug(f"开始检查域名: {url}")
            
            # 首先尝试HEAD请求（更快）
            response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            
            is_success = response.status_code < 400
            final_url = response.url if response.history else url
            
            # 缓存结果
            self._cache_result(url, is_success)
            
            if is_success:
                logger.debug(f"域名检查成功: {url} -> {response.status_code}")
                return True, f"HTTP {response.status_code}", final_url
            else:
                logger.debug(f"域名检查失败: {url} -> {response.status_code}")
                return False, f"HTTP {response.status_code}", final_url
        
        except requests.exceptions.Timeout:
            error_msg = ERROR_MESSAGES['timeout_error']
            logger.warning(f"域名检查超时: {url}")
            self._cache_result(url, False)
            return False, error_msg, None
        
        except requests.exceptions.ConnectionError:
            error_msg = ERROR_MESSAGES['network_error']
            logger.warning(f"域名连接失败: {url}")
            self._cache_result(url, False)
            return False, error_msg, None
        
        except requests.exceptions.RequestException as e:
            error_msg = f"请求异常: {str(e)}"
            logger.warning(f"域名检查异常: {url} - {error_msg}")
            self._cache_result(url, False)
            return False, error_msg, None
        
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.error(f"域名检查出错: {url} - {error_msg}")
            self._cache_result(url, False)
            return False, error_msg, None
    
    def check_domain_detailed(self, url: str) -> Dict[str, any]:
        """详细的域名检查（包含重定向信息）"""
        result = {
            'url': url,
            'is_accessible': False,
            'status_code': None,
            'final_url': None,
            'redirect_chain': [],
            'response_time': None,
            'error_message': None,
            'content_type': None,
            'server': None
        }
        
        try:
            start_time = time.time()
            
            # 发送GET请求获取详细信息
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            
            result['response_time'] = time.time() - start_time
            result['status_code'] = response.status_code
            result['final_url'] = response.url
            result['is_accessible'] = response.status_code < 400
            
            # 记录重定向链
            if response.history:
                result['redirect_chain'] = [resp.url for resp in response.history]
                result['redirect_chain'].append(response.url)
            
            # 获取响应头信息
            result['content_type'] = response.headers.get('content-type', '')
            result['server'] = response.headers.get('server', '')
            
            logger.debug(f"详细检查完成: {url} -> {result['status_code']} ({result['response_time']:.2f}s)")
        
        except requests.exceptions.Timeout:
            result['error_message'] = ERROR_MESSAGES['timeout_error']
            logger.warning(f"详细检查超时: {url}")
        
        except requests.exceptions.ConnectionError:
            result['error_message'] = ERROR_MESSAGES['network_error']
            logger.warning(f"详细检查连接失败: {url}")
        
        except requests.exceptions.RequestException as e:
            result['error_message'] = f"请求异常: {str(e)}"
            logger.warning(f"详细检查异常: {url} - {result['error_message']}")
        
        except Exception as e:
            result['error_message'] = f"未知错误: {str(e)}"
            logger.error(f"详细检查出错: {url} - {result['error_message']}")
        
        return result
    
    def check_multiple_domains(self, domains: List[DomainInfo], max_workers: int = 3) -> Dict[str, Tuple[bool, str]]:
        """并发检查多个域名"""
        results = {}
        
        if not domains:
            return results
        
        logger.info(f"开始并发检查 {len(domains)} 个域名")
        
        # 使用线程池并发检查
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有检查任务
            future_to_domain = {
                executor.submit(self.check_domain_simple, domain.url): domain
                for domain in domains
            }
            
            # 收集结果
            for future in as_completed(future_to_domain):
                domain = future_to_domain[future]
                try:
                    is_accessible, message, final_url = future.result()
                    results[domain.url] = (is_accessible, message)
                    logger.debug(f"并发检查结果: {domain.url} -> {is_accessible}")
                except Exception as e:
                    error_msg = f"检查异常: {str(e)}"
                    results[domain.url] = (False, error_msg)
                    logger.error(f"并发检查出错: {domain.url} - {error_msg}")
        
        logger.info(f"并发检查完成，成功: {sum(1 for r in results.values() if r[0])} / {len(results)}")
        return results
    
    def find_redirected_domains(self, url: str) -> List[str]:
        """查找重定向后的域名"""
        redirected_domains = []
        
        try:
            detailed_result = self.check_domain_detailed(url)
            
            if detailed_result['redirect_chain']:
                # 从重定向链中提取域名
                seen_domains = set()
                for redirect_url in detailed_result['redirect_chain']:
                    parsed = urlparse(redirect_url)
                    domain = f"{parsed.scheme}://{parsed.netloc}"
                    if domain not in seen_domains and domain != url:
                        seen_domains.add(domain)
                        redirected_domains.append(domain)
            
            # 添加最终域名
            if detailed_result['final_url'] and detailed_result['final_url'] != url:
                parsed = urlparse(detailed_result['final_url'])
                final_domain = f"{parsed.scheme}://{parsed.netloc}"
                if final_domain not in redirected_domains:
                    redirected_domains.append(final_domain)
        
        except Exception as e:
            logger.error(f"查找重定向域名失败: {url} - {str(e)}")
        
        return redirected_domains
    
    def discover_new_domains(self, base_url: str) -> List[str]:
        """发现新的可能域名（通过重定向）"""
        new_domains = []
        
        try:
            # 检查原始域名的重定向
            redirected = self.find_redirected_domains(base_url)
            new_domains.extend(redirected)
            
            # 尝试常见的域名变体
            parsed = urlparse(base_url)
            base_domain = parsed.netloc
            
            # 尝试不同的子域名
            common_subdomains = ['www', 'new', 'latest', 'current', 'main']
            for subdomain in common_subdomains:
                if not base_domain.startswith(subdomain + '.'):
                    variant_url = f"{parsed.scheme}://{subdomain}.{base_domain}"
                    if self.check_domain_simple(variant_url)[0]:
                        new_domains.append(variant_url)
            
            # 尝试不同的协议
            if parsed.scheme == 'https':
                http_url = base_url.replace('https://', 'http://')
                if self.check_domain_simple(http_url)[0]:
                    new_domains.append(http_url)
            elif parsed.scheme == 'http':
                https_url = base_url.replace('http://', 'https://')
                if self.check_domain_simple(https_url)[0]:
                    new_domains.append(https_url)
        
        except Exception as e:
            logger.error(f"发现新域名失败: {base_url} - {str(e)}")
        
        return list(set(new_domains))  # 去重
    
    def get_domain_health_score(self, domain: DomainInfo) -> float:
        """计算域名健康度评分（0-100）"""
        score = 0.0
        
        # 基础可访问性（50分）
        if domain.status == 'active':
            score += 50
        elif domain.status == 'unknown':
            score += 25
        
        # 检查频率奖励（20分）
        if domain.check_count > 0:
            success_rate = max(0, (domain.check_count - domain.error_count) / domain.check_count)
            score += success_rate * 20
        
        # 错误次数惩罚（-30分）
        error_penalty = min(30, domain.error_count * 5)
        score -= error_penalty
        
        # 最近检查奖励（10分）
        if domain.is_recently_checked(60):  # 1小时内
            score += 10
        elif domain.is_recently_checked(1440):  # 24小时内
            score += 5
        
        # 响应时间检查（20分）
        try:
            start_time = time.time()
            is_accessible, _, _ = self.check_domain_simple(domain.url)
            response_time = time.time() - start_time
            
            if is_accessible:
                if response_time < 2:
                    score += 20
                elif response_time < 5:
                    score += 15
                elif response_time < 10:
                    score += 10
                else:
                    score += 5
        except Exception:
            pass
        
        return max(0, min(100, score))
    
    def cleanup_cache(self):
        """清理过期的缓存"""
        current_time = time.time()
        expired_keys = [
            url for url, (_, timestamp) in self.check_cache.items()
            if current_time - timestamp > self.cache_duration
        ]
        
        for key in expired_keys:
            del self.check_cache[key]
        
        if expired_keys:
            logger.debug(f"清理了 {len(expired_keys)} 个过期缓存")
    
    def close(self):
        """关闭网络检查器"""
        if hasattr(self, 'session'):
            self.session.close()
        
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
        
        logger.info("网络检查器已关闭")


class DomainMonitor:
    """域名监控器（定期检查）"""
    
    def __init__(self, domain_manager, network_checker: NetworkChecker):
        self.domain_manager = domain_manager
        self.network_checker = network_checker
        self.check_interval = Config.CHECK_INTERVAL
        self.is_monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """开始监控"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        import threading
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("域名监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("域名监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                self._check_all_domains()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                time.sleep(60)  # 出错后等待1分钟再继续
    
    def _check_all_domains(self):
        """检查所有域名"""
        domains = self.domain_manager.domains
        if not domains:
            return
        
        logger.info(f"定期检查 {len(domains)} 个域名")
        
        # 并发检查
        results = self.network_checker.check_multiple_domains(domains)
        
        # 更新域名状态
        for domain in domains:
            if domain.url in results:
                is_accessible, message = results[domain.url]
                self.domain_manager.update_domain_status(
                    domain.url, is_accessible, None if is_accessible else message
                )
        
        # 清理无效域名
        removed = self.domain_manager.cleanup_invalid_domains()
        if removed:
            logger.info(f"清理了 {len(removed)} 个无效域名")
        
        # 排序域名
        self.domain_manager.sort_domains_by_priority()
        
        # 清理网络检查器缓存
        self.network_checker.cleanup_cache()