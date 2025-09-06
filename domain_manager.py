#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
域名管理模块
负责域名的记录、验证、清理等核心功能
"""

import json
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, urljoin

from config import Config, DEFAULT_DOMAINS, DOMAIN_VALIDATION_RULES
from logger import logger
from data_manager import data_manager


class DomainInfo:
    """域名信息类"""
    
    def __init__(self, url: str, added_time: str = None, last_check: str = None, 
                 status: str = 'unknown', check_count: int = 0, error_count: int = 0):
        self.url = self._normalize_url(url)
        self.added_time = added_time or datetime.now().isoformat()
        self.last_check = last_check
        self.status = status  # active, inactive, unknown, error
        self.check_count = check_count
        self.error_count = error_count
    
    def _normalize_url(self, url: str) -> str:
        """标准化URL格式"""
        if not url:
            return url
        
        # 移除末尾的斜杠
        url = url.rstrip('/')
        
        # 如果没有协议，添加https
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        return url
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'url': self.url,
            'added_time': self.added_time,
            'last_check': self.last_check,
            'status': self.status,
            'check_count': self.check_count,
            'error_count': self.error_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DomainInfo':
        """从字典创建实例"""
        return cls(
            url=data.get('url', ''),
            added_time=data.get('added_time'),
            last_check=data.get('last_check'),
            status=data.get('status', 'unknown'),
            check_count=data.get('check_count', 0),
            error_count=data.get('error_count', 0)
        )
    
    def update_check_result(self, is_active: bool, error_msg: str = None):
        """更新检查结果"""
        self.last_check = datetime.now().isoformat()
        self.check_count += 1
        
        if is_active:
            self.status = 'active'
            self.error_count = 0  # 重置错误计数
        else:
            self.error_count += 1
            if error_msg:
                self.status = 'error'
            else:
                self.status = 'inactive'
    
    def is_recently_checked(self, minutes: int = 5) -> bool:
        """检查是否最近已经检查过"""
        if not self.last_check:
            return False
        
        try:
            last_check_time = datetime.fromisoformat(self.last_check)
            return datetime.now() - last_check_time < timedelta(minutes=minutes)
        except ValueError:
            return False
    
    def get_domain_name(self) -> str:
        """获取域名部分"""
        try:
            parsed = urlparse(self.url)
            return parsed.netloc
        except Exception:
            return self.url


class DomainManager:
    """域名管理器"""
    
    def __init__(self):
        self.domains_file = Config.get_domains_file()
        self.max_domains = Config.MAX_DOMAINS
        self.domains: List[DomainInfo] = []
        self.load_domains()
    
    def load_domains(self) -> bool:
        """加载域名记录"""
        try:
            data = data_manager.load_domains()
            if data:
                self.domains = [DomainInfo.from_dict(item) for item in data]
                logger.info(f"加载了 {len(self.domains)} 个域名记录")
            else:
                # 初始化默认域名
                self._initialize_default_domains()
            return True
        except Exception as e:
            logger.error(f"加载域名记录失败: {e}")
            self._initialize_default_domains()
            return False
    
    def _initialize_default_domains(self):
        """初始化默认域名"""
        logger.info("初始化默认域名")
        for url in DEFAULT_DOMAINS:
            domain_info = DomainInfo(url)
            self.domains.append(domain_info)
        self.save_domains()
    
    def save_domains(self) -> bool:
        """保存域名记录"""
        try:
            data = [domain.to_dict() for domain in self.domains]
            success = data_manager.save_domains(data)
            if success:
                logger.debug(f"保存了 {len(self.domains)} 个域名记录")
            return success
        except Exception as e:
            logger.error(f"保存域名记录失败: {e}")
            return False
    
    def validate_domain(self, url: str) -> Tuple[bool, str]:
        """验证域名格式"""
        if not url:
            return False, "域名不能为空"
        
        # 标准化URL
        normalized_url = DomainInfo(url).url
        
        # 长度检查
        if len(normalized_url) < DOMAIN_VALIDATION_RULES['min_length']:
            return False, "域名太短"
        
        if len(normalized_url) > DOMAIN_VALIDATION_RULES['max_length']:
            return False, "域名太长"
        
        # 解析URL
        try:
            parsed = urlparse(normalized_url)
        except Exception:
            return False, "域名格式无效"
        
        # 协议检查
        if parsed.scheme not in DOMAIN_VALIDATION_RULES['allowed_schemes']:
            return False, f"不支持的协议: {parsed.scheme}"
        
        # 域名部分检查
        if not parsed.netloc:
            return False, "缺少域名部分"
        
        # 简单的域名格式检查
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        if not re.match(domain_pattern, parsed.netloc):
            return False, "域名格式不正确"
        
        # TLD检查
        if DOMAIN_VALIDATION_RULES['required_tld'] and '.' not in parsed.netloc:
            return False, "域名必须包含顶级域名"
        
        return True, "域名格式正确"
    
    def add_domain(self, url: str) -> Tuple[bool, str]:
        """添加新域名"""
        # 验证域名格式
        is_valid, message = self.validate_domain(url)
        if not is_valid:
            logger.warning(f"域名格式验证失败: {url} - {message}")
            return False, message
        
        # 创建域名信息对象
        new_domain = DomainInfo(url)
        
        # 检查是否已存在
        existing_domain = self.find_domain(new_domain.url)
        if existing_domain:
            # 更新现有域名的时间戳
            existing_domain.added_time = datetime.now().isoformat()
            # 移动到列表开头
            self.domains.remove(existing_domain)
            self.domains.insert(0, existing_domain)
            logger.info(f"更新现有域名: {new_domain.url}")
        else:
            # 添加新域名到列表开头
            self.domains.insert(0, new_domain)
            logger.info(f"添加新域名: {new_domain.url}")
        
        # 保持最大域名数量限制
        if len(self.domains) > self.max_domains:
            removed_domains = self.domains[self.max_domains:]
            self.domains = self.domains[:self.max_domains]
            logger.info(f"移除超出限制的域名: {[d.url for d in removed_domains]}")
        
        # 使用数据管理器保存
        success = data_manager.save_domains([domain.to_dict() for domain in self.domains])
        if success:
            return True, "域名添加成功"
        else:
            return False, "保存域名失败"
    
    def find_domain(self, url: str) -> Optional[DomainInfo]:
        """查找域名"""
        normalized_url = DomainInfo(url).url
        for domain in self.domains:
            if domain.url == normalized_url:
                return domain
        return None
    
    def remove_domain(self, url: str) -> bool:
        """移除域名"""
        domain = self.find_domain(url)
        if domain:
            self.domains.remove(domain)
            # 使用数据管理器保存
            success = data_manager.save_domains([domain.to_dict() for domain in self.domains])
            if success:
                logger.info(f"移除域名: {url}")
                return True
            else:
                # 保存失败，恢复域名
                self.domains.append(domain)
                return False
        return False
    
    def get_active_domains(self) -> List[DomainInfo]:
        """获取活跃域名列表"""
        return [domain for domain in self.domains if domain.status == 'active']
    
    def get_current_domain(self) -> Optional[DomainInfo]:
        """获取当前最优域名（优先返回最新添加的域名，其次是第一个活跃域名）"""
        # 优先返回最新添加的域名（列表第一个）
        if self.domains:
            return self.domains[0]
        return None
    
    def update_domain_status(self, url: str, is_active: bool, error_msg: str = None) -> bool:
        """更新域名状态"""
        domain = self.find_domain(url)
        if domain:
            domain.update_check_result(is_active, error_msg)
            # 使用数据管理器保存
            success = data_manager.save_domains([domain.to_dict() for domain in self.domains])
            if success:
                logger.debug(f"更新域名状态: {url} -> {domain.status}")
                return True
            else:
                logger.error(f"保存域名状态失败: {url}")
                return False
        return False
    
    def cleanup_invalid_domains(self, max_error_count: int = 5) -> List[str]:
        """清理无效域名"""
        removed_domains = []
        
        # 移除错误次数过多的域名
        domains_to_remove = []
        for domain in self.domains:
            if domain.error_count >= max_error_count:
                domains_to_remove.append(domain)
                removed_domains.append(domain.url)
        
        for domain in domains_to_remove:
            self.domains.remove(domain)
        
        if removed_domains:
            logger.info(f"清理无效域名: {removed_domains}")
            self.save_domains()
        
        return removed_domains
    
    def get_domains_by_status(self, status: str) -> List[DomainInfo]:
        """根据状态获取域名列表"""
        return [domain for domain in self.domains if domain.status == status]
    
    def get_domain_statistics(self) -> Dict[str, int]:
        """获取域名统计信息"""
        stats = {
            'total': len(self.domains),
            'active': len(self.get_domains_by_status('active')),
            'inactive': len(self.get_domains_by_status('inactive')),
            'error': len(self.get_domains_by_status('error')),
            'unknown': len(self.get_domains_by_status('unknown'))
        }
        return stats
    
    def sort_domains_by_priority(self):
        """按优先级排序域名（活跃域名优先，然后按添加时间）"""
        def sort_key(domain: DomainInfo):
            # 活跃域名优先级最高
            if domain.status == 'active':
                priority = 0
            elif domain.status == 'unknown':
                priority = 1
            elif domain.status == 'inactive':
                priority = 2
            else:  # error
                priority = 3
            
            # 在同一优先级内，按添加时间倒序（新的在前）
            try:
                added_time = datetime.fromisoformat(domain.added_time)
                time_priority = -added_time.timestamp()
            except (ValueError, TypeError):
                time_priority = 0
            
            return (priority, time_priority)
        
        self.domains.sort(key=sort_key)
        self.save_domains()
    
    def export_domains(self, file_path: str) -> bool:
        """导出域名列表"""
        try:
            data = {
                'export_time': datetime.now().isoformat(),
                'app_version': Config.APP_VERSION,
                'domains': [domain.to_dict() for domain in self.domains]
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"导出域名列表到: {file_path}")
            return True
        except Exception as e:
            logger.error(f"导出域名列表失败: {e}")
            return False
    
    def import_domains(self, file_path: str) -> Tuple[bool, str]:
        """导入域名列表"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'domains' not in data:
                return False, "无效的导入文件格式"
            
            imported_count = 0
            for domain_data in data['domains']:
                try:
                    domain = DomainInfo.from_dict(domain_data)
                    if not self.find_domain(domain.url):
                        self.domains.append(domain)
                        imported_count += 1
                except Exception as e:
                    logger.warning(f"跳过无效域名记录: {e}")
            
            # 保持域名数量限制
            if len(self.domains) > self.max_domains:
                self.domains = self.domains[:self.max_domains]
            
            self.save_domains()
            logger.info(f"导入了 {imported_count} 个域名")
            return True, f"成功导入 {imported_count} 个域名"
        
        except Exception as e:
            logger.error(f"导入域名列表失败: {e}")
            return False, f"导入失败: {str(e)}"