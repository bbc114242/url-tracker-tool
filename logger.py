#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志管理模块
提供统一的日志记录功能
"""

import logging
import logging.handlers
import os
from typing import Optional

from config import Config


class Logger:
    """日志管理器"""
    
    _instance: Optional['Logger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is None:
            self._setup_logger()
    
    def _setup_logger(self):
        """设置日志记录器"""
        # 创建日志记录器
        self._logger = logging.getLogger(Config.APP_NAME)
        self._logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        # 避免重复添加处理器
        if self._logger.handlers:
            return
        
        # 创建格式化器
        formatter = logging.Formatter(Config.LOG_FORMAT)
        
        # 文件处理器（带轮转）
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                Config.get_log_file(),
                maxBytes=Config.LOG_MAX_SIZE,
                backupCount=Config.LOG_BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
        except Exception as e:
            print(f"无法创建文件日志处理器: {e}")
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)
    
    def get_logger(self) -> logging.Logger:
        """获取日志记录器"""
        return self._logger
    
    def debug(self, message: str, *args, **kwargs):
        """记录调试信息"""
        self._logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """记录信息"""
        self._logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """记录警告"""
        self._logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """记录错误"""
        self._logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """记录严重错误"""
        self._logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """记录异常信息"""
        self._logger.exception(message, *args, **kwargs)


# 创建全局日志实例
logger = Logger()

# 便捷函数
def debug(message: str, *args, **kwargs):
    logger.debug(message, *args, **kwargs)

def info(message: str, *args, **kwargs):
    logger.info(message, *args, **kwargs)

def warning(message: str, *args, **kwargs):
    logger.warning(message, *args, **kwargs)

def error(message: str, *args, **kwargs):
    logger.error(message, *args, **kwargs)

def critical(message: str, *args, **kwargs):
    logger.critical(message, *args, **kwargs)

def exception(message: str, *args, **kwargs):
    logger.exception(message, *args, **kwargs)