#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常处理和错误管理模块
提供全面的异常处理、错误恢复和监控功能
"""

import sys
import traceback
import threading
import time
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List
from functools import wraps
from pathlib import Path

from config import Config
from logger import logger


class ErrorCode:
    """错误代码定义"""
    # 网络相关错误
    NETWORK_TIMEOUT = "NET_001"
    NETWORK_CONNECTION_ERROR = "NET_002"
    NETWORK_DNS_ERROR = "NET_003"
    NETWORK_SSL_ERROR = "NET_004"
    NETWORK_HTTP_ERROR = "NET_005"
    
    # 域名相关错误
    DOMAIN_INVALID_FORMAT = "DOM_001"
    DOMAIN_NOT_FOUND = "DOM_002"
    DOMAIN_ACCESS_DENIED = "DOM_003"
    DOMAIN_REDIRECT_LOOP = "DOM_004"
    
    # 文件系统错误
    FILE_NOT_FOUND = "FILE_001"
    FILE_PERMISSION_ERROR = "FILE_002"
    FILE_CORRUPTED = "FILE_003"
    FILE_DISK_FULL = "FILE_004"
    
    # 配置错误
    CONFIG_INVALID = "CFG_001"
    CONFIG_MISSING = "CFG_002"
    
    # GUI相关错误
    GUI_INIT_ERROR = "GUI_001"
    GUI_DISPLAY_ERROR = "GUI_002"
    
    # 系统错误
    SYSTEM_MEMORY_ERROR = "SYS_001"
    SYSTEM_PERMISSION_ERROR = "SYS_002"
    SYSTEM_RESOURCE_ERROR = "SYS_003"
    
    # 未知错误
    UNKNOWN_ERROR = "UNK_001"


class AppException(Exception):
    """应用程序基础异常类"""
    
    def __init__(self, message: str, error_code: str = ErrorCode.UNKNOWN_ERROR, 
                 details: Optional[Dict[str, Any]] = None, cause: Optional[Exception] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'message': self.message,
            'error_code': self.error_code,
            'details': self.details,
            'timestamp': self.timestamp,
            'cause': str(self.cause) if self.cause else None
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"


class NetworkException(AppException):
    """网络相关异常"""
    pass


class DomainException(AppException):
    """域名相关异常"""
    pass


class FileSystemException(AppException):
    """文件系统异常"""
    pass


class ConfigException(AppException):
    """配置异常"""
    pass


class GUIException(AppException):
    """GUI异常"""
    pass


class SystemException(AppException):
    """系统异常"""
    pass


class ErrorRecoveryStrategy:
    """错误恢复策略"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0, 
                 backoff_factor: float = 2.0, recovery_action: Optional[Callable] = None):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        self.recovery_action = recovery_action
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """判断是否应该重试"""
        if attempt >= self.max_retries:
            return False
        
        # 根据异常类型决定是否重试
        if isinstance(exception, (NetworkException, FileSystemException)):
            return True
        
        return False
    
    def get_retry_delay(self, attempt: int) -> float:
        """获取重试延迟时间"""
        return self.retry_delay * (self.backoff_factor ** attempt)
    
    def execute_recovery(self, exception: Exception) -> bool:
        """执行恢复操作"""
        if self.recovery_action:
            try:
                self.recovery_action(exception)
                return True
            except Exception as e:
                logger.error(f"恢复操作失败: {e}")
        return False


class ExceptionHandler:
    """异常处理器"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.recovery_strategies: Dict[str, ErrorRecoveryStrategy] = {}
        self.error_callbacks: List[Callable] = []
        self.critical_error_callback: Optional[Callable] = None
        self.lock = threading.Lock()
        
        # 设置默认恢复策略
        self._setup_default_strategies()
        
        # 设置全局异常处理
        self._setup_global_exception_handler()
    
    def _setup_default_strategies(self):
        """设置默认恢复策略"""
        # 网络错误策略
        self.recovery_strategies[ErrorCode.NETWORK_TIMEOUT] = ErrorRecoveryStrategy(
            max_retries=3, retry_delay=2.0, backoff_factor=1.5
        )
        self.recovery_strategies[ErrorCode.NETWORK_CONNECTION_ERROR] = ErrorRecoveryStrategy(
            max_retries=2, retry_delay=3.0, backoff_factor=2.0
        )
        
        # 文件系统错误策略
        self.recovery_strategies[ErrorCode.FILE_NOT_FOUND] = ErrorRecoveryStrategy(
            max_retries=1, retry_delay=0.5, recovery_action=self._create_missing_file
        )
        self.recovery_strategies[ErrorCode.FILE_PERMISSION_ERROR] = ErrorRecoveryStrategy(
            max_retries=0  # 权限错误不重试
        )
        
        # 域名错误策略
        self.recovery_strategies[ErrorCode.DOMAIN_NOT_FOUND] = ErrorRecoveryStrategy(
            max_retries=1, retry_delay=1.0
        )
    
    def _setup_global_exception_handler(self):
        """设置全局异常处理"""
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
            
            error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
            logger.critical(f"未捕获的异常: {error_msg}")
            
            # 调用关键错误回调
            if self.critical_error_callback:
                try:
                    self.critical_error_callback(exc_value)
                except Exception as e:
                    logger.error(f"关键错误回调失败: {e}")
        
        sys.excepthook = handle_exception
    
    def _create_missing_file(self, exception: Exception):
        """创建缺失的文件"""
        if isinstance(exception, FileSystemException) and exception.error_code == ErrorCode.FILE_NOT_FOUND:
            file_path = exception.details.get('file_path')
            if file_path:
                try:
                    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(file_path).touch()
                    logger.info(f"创建缺失文件: {file_path}")
                except Exception as e:
                    logger.error(f"创建文件失败: {e}")
                    raise
    
    def register_recovery_strategy(self, error_code: str, strategy: ErrorRecoveryStrategy):
        """注册恢复策略"""
        self.recovery_strategies[error_code] = strategy
    
    def register_error_callback(self, callback: Callable):
        """注册错误回调"""
        self.error_callbacks.append(callback)
    
    def set_critical_error_callback(self, callback: Callable):
        """设置关键错误回调"""
        self.critical_error_callback = callback
    
    def handle_exception(self, exception: Exception, context: str = "") -> bool:
        """处理异常"""
        with self.lock:
            try:
                # 记录异常
                self._log_exception(exception, context)
                
                # 更新错误计数
                error_code = getattr(exception, 'error_code', ErrorCode.UNKNOWN_ERROR)
                self.error_counts[error_code] = self.error_counts.get(error_code, 0) + 1
                
                # 调用错误回调
                for callback in self.error_callbacks:
                    try:
                        callback(exception, context)
                    except Exception as e:
                        logger.error(f"错误回调失败: {e}")
                
                # 尝试恢复
                if error_code in self.recovery_strategies:
                    strategy = self.recovery_strategies[error_code]
                    return strategy.execute_recovery(exception)
                
                return False
                
            except Exception as e:
                logger.critical(f"异常处理器本身发生错误: {e}")
                return False
    
    def _log_exception(self, exception: Exception, context: str):
        """记录异常"""
        if isinstance(exception, AppException):
            logger.error(f"应用异常 [{context}]: {exception}")
            if exception.details:
                logger.error(f"异常详情: {exception.details}")
        else:
            logger.error(f"系统异常 [{context}]: {exception}")
            logger.error(f"异常堆栈: {traceback.format_exc()}")
    
    def get_error_statistics(self) -> Dict[str, int]:
        """获取错误统计"""
        with self.lock:
            return self.error_counts.copy()
    
    def reset_error_counts(self):
        """重置错误计数"""
        with self.lock:
            self.error_counts.clear()


def retry_on_exception(max_retries: int = 3, retry_delay: float = 1.0, 
                      backoff_factor: float = 2.0, exceptions: tuple = (Exception,)):
    """重试装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        delay = retry_delay * (backoff_factor ** attempt)
                        logger.warning(f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败，{delay}秒后重试: {e}")
                        time.sleep(delay)
                    else:
                        logger.error(f"函数 {func.__name__} 重试 {max_retries} 次后仍然失败: {e}")
                        break
            
            raise last_exception
        
        return wrapper
    return decorator


def safe_execute(func: Callable, *args, default_return=None, 
                exception_handler: Optional[ExceptionHandler] = None, 
                context: str = "", **kwargs):
    """安全执行函数"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if exception_handler:
            exception_handler.handle_exception(e, context)
        else:
            logger.error(f"安全执行失败 [{context}]: {e}")
        return default_return


def exception_to_app_exception(exception: Exception) -> AppException:
    """将标准异常转换为应用异常"""
    if isinstance(exception, AppException):
        return exception
    
    # 网络相关异常
    if isinstance(exception, (ConnectionError, TimeoutError)):
        if "timeout" in str(exception).lower():
            return NetworkException(
                f"网络超时: {exception}",
                ErrorCode.NETWORK_TIMEOUT,
                cause=exception
            )
        else:
            return NetworkException(
                f"网络连接错误: {exception}",
                ErrorCode.NETWORK_CONNECTION_ERROR,
                cause=exception
            )
    
    # 文件系统异常
    if isinstance(exception, FileNotFoundError):
        return FileSystemException(
            f"文件未找到: {exception}",
            ErrorCode.FILE_NOT_FOUND,
            details={'file_path': str(exception.filename) if exception.filename else None},
            cause=exception
        )
    
    if isinstance(exception, PermissionError):
        return FileSystemException(
            f"文件权限错误: {exception}",
            ErrorCode.FILE_PERMISSION_ERROR,
            cause=exception
        )
    
    if isinstance(exception, OSError):
        if exception.errno == 28:  # No space left on device
            return FileSystemException(
                f"磁盘空间不足: {exception}",
                ErrorCode.FILE_DISK_FULL,
                cause=exception
            )
        else:
            return SystemException(
                f"系统错误: {exception}",
                ErrorCode.SYSTEM_RESOURCE_ERROR,
                cause=exception
            )
    
    # 内存错误
    if isinstance(exception, MemoryError):
        return SystemException(
            f"内存不足: {exception}",
            ErrorCode.SYSTEM_MEMORY_ERROR,
            cause=exception
        )
    
    # 默认转换为未知错误
    return AppException(
        f"未知错误: {exception}",
        ErrorCode.UNKNOWN_ERROR,
        cause=exception
    )


class HealthChecker:
    """健康检查器"""
    
    def __init__(self, exception_handler: ExceptionHandler):
        self.exception_handler = exception_handler
        self.health_checks: Dict[str, Callable] = {}
        self.last_check_results: Dict[str, bool] = {}
        self.check_interval = 60  # 秒
        self.running = False
        self.check_thread: Optional[threading.Thread] = None
    
    def register_health_check(self, name: str, check_func: Callable[[], bool]):
        """注册健康检查"""
        self.health_checks[name] = check_func
    
    def start_monitoring(self):
        """开始监控"""
        if self.running:
            return
        
        self.running = True
        self.check_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.check_thread.start()
        logger.info("健康检查监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.running = False
        if self.check_thread:
            self.check_thread.join(timeout=5)
        logger.info("健康检查监控已停止")
    
    def _monitoring_loop(self):
        """监控循环"""
        while self.running:
            try:
                self.run_health_checks()
                time.sleep(self.check_interval)
            except Exception as e:
                self.exception_handler.handle_exception(e, "健康检查监控")
                time.sleep(self.check_interval)
    
    def run_health_checks(self) -> Dict[str, bool]:
        """运行所有健康检查"""
        results = {}
        
        for name, check_func in self.health_checks.items():
            try:
                result = check_func()
                results[name] = result
                self.last_check_results[name] = result
                
                if not result:
                    logger.warning(f"健康检查失败: {name}")
                
            except Exception as e:
                results[name] = False
                self.last_check_results[name] = False
                self.exception_handler.handle_exception(e, f"健康检查: {name}")
        
        return results
    
    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        return {
            'overall_healthy': all(self.last_check_results.values()),
            'checks': self.last_check_results.copy(),
            'error_counts': self.exception_handler.get_error_statistics()
        }


# 全局异常处理器实例
global_exception_handler = ExceptionHandler()


# 便捷函数
def handle_exception(exception: Exception, context: str = "") -> bool:
    """处理异常的便捷函数"""
    return global_exception_handler.handle_exception(exception, context)


def get_error_statistics() -> Dict[str, int]:
    """获取错误统计的便捷函数"""
    return global_exception_handler.get_error_statistics()


def reset_error_counts():
    """重置错误计数的便捷函数"""
    global_exception_handler.reset_error_counts()