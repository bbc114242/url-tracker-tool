#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据管理器
统一处理配置文件和数据存储
"""

import os
import json
import configparser
from typing import Dict, List, Any, Optional
from datetime import datetime
from config import Config

class DataManager:
    """数据管理器类"""
    
    def __init__(self):
        """初始化数据管理器"""
        self.config = Config()
        self.ensure_data_directory()
        
        # 文件路径
        self.domains_file = self.config.get_domains_file()
        self.settings_file = os.path.join(self.config.DATA_DIR, "settings.json")
        self.user_config_file = os.path.join(self.config.DATA_DIR, "user_config.ini")
        
    def ensure_data_directory(self):
        """确保数据目录存在"""
        self.config.ensure_data_dir()
        
    # ==================== 域名数据管理 ====================
    
    def load_domains(self) -> List[Dict[str, Any]]:
        """加载域名数据"""
        try:
            if os.path.exists(self.domains_file):
                with open(self.domains_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content.startswith('\ufeff'):  # 移除BOM
                        content = content[1:]
                    return json.loads(content)
            return []
        except (json.JSONDecodeError, FileNotFoundError, UnicodeDecodeError) as e:
            print(f"加载域名数据失败: {e}")
            return []
    
    def save_domains(self, domains: List[Dict[str, Any]]) -> bool:
        """保存域名数据"""
        try:
            with open(self.domains_file, 'w', encoding='utf-8') as f:
                json.dump(domains, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存域名数据失败: {e}")
            return False
    
    def add_domain(self, url: str, status: str = "active") -> bool:
        """添加域名"""
        domains = self.load_domains()
        
        # 检查是否已存在
        for domain in domains:
            if domain.get('url') == url:
                return False
        
        # 添加新域名
        new_domain = {
            "url": url,
            "status": status,
            "last_check": datetime.now().isoformat(),
            "response_time": 0,
            "added_time": datetime.now().isoformat()
        }
        
        domains.insert(0, new_domain)  # 插入到开头
        return self.save_domains(domains)
    
    def remove_domain(self, url: str) -> bool:
        """删除域名"""
        domains = self.load_domains()
        original_count = len(domains)
        
        domains = [d for d in domains if d.get('url') != url]
        
        if len(domains) < original_count:
            return self.save_domains(domains)
        return False
    
    def update_domain_status(self, url: str, status: str, response_time: float = 0) -> bool:
        """更新域名状态"""
        domains = self.load_domains()
        
        for domain in domains:
            if domain.get('url') == url:
                domain['status'] = status
                domain['response_time'] = response_time
                domain['last_check'] = datetime.now().isoformat()
                return self.save_domains(domains)
        
        return False
    
    # ==================== 应用设置管理 ====================
    
    def load_settings(self) -> Dict[str, Any]:
        """加载应用设置"""
        default_settings = {
            "window_geometry": "700x500+100+100",
            "check_interval": 300,
            "auto_start": False,
            "minimize_to_tray": False,
            "theme": "default",
            "language": "zh_CN",
            "notifications_enabled": True,
            "sound_enabled": False
        }
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    # 合并默认设置
                    default_settings.update(settings)
            return default_settings
        except Exception as e:
            print(f"加载设置失败: {e}")
            return default_settings
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """保存应用设置"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存设置失败: {e}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """获取单个设置项"""
        settings = self.load_settings()
        return settings.get(key, default)
    
    def set_setting(self, key: str, value: Any) -> bool:
        """设置单个设置项"""
        settings = self.load_settings()
        settings[key] = value
        return self.save_settings(settings)
    
    # ==================== 用户配置管理 (INI格式) ====================
    
    def load_user_config(self) -> configparser.ConfigParser:
        """加载用户配置文件 (INI格式)"""
        config = configparser.ConfigParser()
        
        # 设置默认配置
        config['DEFAULT'] = {
            'check_interval': '300',
            'request_timeout': '10',
            'max_retries': '3',
            'user_agent': 'DomainTracker/1.0'
        }
        
        config['UI'] = {
            'theme': 'default',
            'language': 'zh_CN',
            'window_width': '700',
            'window_height': '500'
        }
        
        config['NOTIFICATIONS'] = {
            'enabled': 'true',
            'sound': 'false',
            'popup': 'true'
        }
        
        # 加载现有配置
        if os.path.exists(self.user_config_file):
            try:
                config.read(self.user_config_file, encoding='utf-8')
            except Exception as e:
                print(f"加载用户配置失败: {e}")
        
        return config
    
    def save_user_config(self, config: configparser.ConfigParser) -> bool:
        """保存用户配置文件"""
        try:
            with open(self.user_config_file, 'w', encoding='utf-8') as f:
                config.write(f)
            return True
        except Exception as e:
            print(f"保存用户配置失败: {e}")
            return False
    
    def get_user_config_value(self, section: str, key: str, fallback: str = '') -> str:
        """获取用户配置值"""
        config = self.load_user_config()
        return config.get(section, key, fallback=fallback)
    
    def set_user_config_value(self, section: str, key: str, value: str) -> bool:
        """设置用户配置值"""
        config = self.load_user_config()
        
        if section not in config:
            config.add_section(section)
        
        config.set(section, key, value)
        return self.save_user_config(config)
    
    # ==================== 数据导入导出 ====================
    
    def export_data(self, export_path: str) -> bool:
        """导出所有数据"""
        try:
            export_data = {
                'domains': self.load_domains(),
                'settings': self.load_settings(),
                'user_config': dict(self.load_user_config()),
                'export_time': datetime.now().isoformat(),
                'version': '1.0.0'
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"导出数据失败: {e}")
            return False
    
    def import_data(self, import_path: str) -> bool:
        """导入数据"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # 导入域名数据
            if 'domains' in import_data:
                self.save_domains(import_data['domains'])
            
            # 导入设置
            if 'settings' in import_data:
                self.save_settings(import_data['settings'])
            
            # 导入用户配置
            if 'user_config' in import_data:
                config = configparser.ConfigParser()
                config.read_dict(import_data['user_config'])
                self.save_user_config(config)
            
            return True
        except Exception as e:
            print(f"导入数据失败: {e}")
            return False
    
    # ==================== 数据清理 ====================
    
    def cleanup_old_data(self, days: int = 30) -> bool:
        """清理旧数据"""
        try:
            # 这里可以添加清理逻辑，比如清理旧的日志文件等
            # 目前只是一个占位符
            return True
        except Exception as e:
            print(f"清理数据失败: {e}")
            return False
    
    def get_data_statistics(self) -> Dict[str, Any]:
        """获取数据统计信息"""
        try:
            domains = self.load_domains()
            settings = self.load_settings()
            
            stats = {
                'total_domains': len(domains),
                'active_domains': len([d for d in domains if d.get('status') == 'active']),
                'inactive_domains': len([d for d in domains if d.get('status') != 'active']),
                'data_files': {
                    'domains_file_exists': os.path.exists(self.domains_file),
                    'settings_file_exists': os.path.exists(self.settings_file),
                    'user_config_file_exists': os.path.exists(self.user_config_file)
                },
                'data_directory': self.config.DATA_DIR,
                'last_updated': datetime.now().isoformat()
            }
            
            return stats
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {}

# 全局数据管理器实例
data_manager = DataManager()