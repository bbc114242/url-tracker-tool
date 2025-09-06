#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
包含应用程序的各种配置参数
"""

import os
from typing import Dict, Any


class Config:
    """应用程序配置类"""
    
    # 基础配置
    APP_NAME = "域名跟踪器"
    VERSION = "1.0.0"
    
    # 文件路径
    DATA_DIR = os.path.join(os.path.expanduser("~"), ".domain_tracker")
    DOMAINS_FILE = os.path.join(DATA_DIR, "domains.json")
    CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
    LOG_FILE = os.path.join(DATA_DIR, "app.log")
    
    # 域名管理配置
    MAX_DOMAINS = 10
    REQUEST_TIMEOUT = 10
    CHECK_INTERVAL = 300  # 5分钟
    RETRY_ATTEMPTS = 3
    
    # 网络配置
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY = 1  # 重试延迟（秒）
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    HEADERS = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    
    # GUI配置
    WINDOW_WIDTH = 700
    WINDOW_HEIGHT = 500
    WINDOW_MIN_WIDTH = 500
    WINDOW_MIN_HEIGHT = 400
    
    # 托盘图标配置
    TRAY_ICON_SIZE = (64, 64)
    TRAY_ICON_COLOR = "#2196F3"
    TRAY_ICON_BG_COLOR = "white"
    
    # 日志配置
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_MAX_SIZE = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    @classmethod
    def ensure_data_dir(cls):
        """确保数据目录存在"""
        if not os.path.exists(cls.DATA_DIR):
            os.makedirs(cls.DATA_DIR, exist_ok=True)
    
    @classmethod
    def get_domains_file(cls) -> str:
        """获取域名文件路径"""
        cls.ensure_data_dir()
        return cls.DOMAINS_FILE
    
    @classmethod
    def get_config_file(cls) -> str:
        """获取配置文件路径"""
        cls.ensure_data_dir()
        return cls.CONFIG_FILE
    
    @classmethod
    def get_log_file(cls) -> str:
        """获取日志文件路径"""
        cls.ensure_data_dir()
        return cls.LOG_FILE


# 默认域名列表（用于初始化）
DEFAULT_DOMAINS = [
    "https://www.k8w4w.com",
    "https://www.z6r0j.com"
]

# 域名验证规则
DOMAIN_VALIDATION_RULES = {
    "min_length": 4,
    "max_length": 253,
    "allowed_schemes": ["http", "https"],
    "required_tld": True
}

# 错误消息
ERROR_MESSAGES = {
    "network_error": "网络连接失败，请检查网络设置",
    "timeout_error": "请求超时，请稍后重试",
    "invalid_domain": "域名格式无效",
    "domain_not_accessible": "域名无法访问",
    "file_error": "文件操作失败",
    "unknown_error": "未知错误"
}

# 成功消息
SUCCESS_MESSAGES = {
    "domain_added": "域名添加成功",
    "domain_updated": "域名状态更新成功",
    "domain_copied": "域名已复制到剪贴板",
    "check_completed": "域名检查完成"
}