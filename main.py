#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
域名跟踪工具主程序
用于跟踪和管理网站域名的变化
"""

import sys
import os
import threading
import time
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from logger import logger
from domain_manager import DomainManager
from network_checker import NetworkChecker, DomainMonitor
# from tray_manager import TrayManager  # 已移除托盘功能
from gui_manager import MainWindow
from exception_handler import (
    global_exception_handler, handle_exception, HealthChecker,
    AppException, NetworkException, FileSystemException,
    ErrorCode, safe_execute
)


class DomainTracker:
    """域名跟踪器主类"""
    
    def __init__(self):
        self.config = Config()
        self.domain_manager = None
        self.network_checker = None
        self.domain_monitor = None
        # self.tray_manager = None  # 已移除托盘功能
        self.main_window = None
        self.health_checker = None
        self.running = False
        
        # 设置异常处理回调
        self._setup_exception_handling()
        
        # 初始化组件
        self._initialize_components()
        
    def _setup_exception_handling(self):
        """设置异常处理"""
        try:
            # 注册错误回调
            global_exception_handler.register_error_callback(self._on_error)
            
            # 设置关键错误回调
            global_exception_handler.set_critical_error_callback(self._on_critical_error)
            
            # 初始化健康检查器
            self.health_checker = HealthChecker(global_exception_handler)
            
            # 注册健康检查项目
            self.health_checker.register_health_check("domain_manager", self._check_domain_manager_health)
            self.health_checker.register_health_check("network_checker", self._check_network_health)
            self.health_checker.register_health_check("file_system", self._check_file_system_health)
            
            logger.info("异常处理系统初始化完成")
            
        except Exception as e:
            logger.error(f"异常处理系统初始化失败: {e}")
    
    def _check_domain_manager_health(self) -> bool:
        """检查域名管理器健康状态"""
        try:
            if not self.domain_manager:
                return False
            
            # 检查域名文件是否可访问
            domains_file = Path(self.config.DOMAINS_FILE)
            if not domains_file.exists():
                return False
            
            # 检查是否能正常加载域名
            test_domains = self.domain_manager.domains
            return True
            
        except Exception:
            return False
    
    def _check_network_health(self) -> bool:
        """检查网络健康状态"""
        try:
            if not self.network_checker:
                return False
            
            # 简单的网络连通性检查
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
            
        except Exception:
            return False
    
    def _check_file_system_health(self) -> bool:
        """检查文件系统健康状态"""
        try:
            # 检查数据目录是否可写
            data_dir = Path(self.config.DATA_DIR)
            test_file = data_dir / "health_check.tmp"
            
            test_file.write_text("health check")
            content = test_file.read_text()
            test_file.unlink()
            
            return content == "health check"
            
        except Exception:
            return False
    
    def _on_error(self, exception: Exception, context: str):
        """错误回调处理"""
        try:
            # 记录错误统计
            error_code = getattr(exception, 'error_code', ErrorCode.UNKNOWN_ERROR)
            
            # 根据错误类型采取相应措施
            if isinstance(exception, NetworkException):
                self._handle_network_error(exception, context)
            elif isinstance(exception, FileSystemException):
                self._handle_file_system_error(exception, context)
            
            # 如果是GUI相关错误，尝试重新初始化GUI
            if "GUI" in context and self.main_window:
                self._recover_gui()
                
        except Exception as e:
            logger.error(f"错误回调处理失败: {e}")
    
    def _handle_network_error(self, exception: NetworkException, context: str):
        """处理网络错误"""
        if exception.error_code == ErrorCode.NETWORK_CONNECTION_ERROR:
            # 网络连接错误，暂停监控一段时间
            if self.domain_monitor and self.domain_monitor.running:
                logger.warning("网络连接错误，暂停域名监控30秒")
                threading.Timer(30.0, self.domain_monitor.start_monitoring).start()
                self.domain_monitor.stop_monitoring()
    
    def _handle_file_system_error(self, exception: FileSystemException, context: str):
        """处理文件系统错误"""
        if exception.error_code == ErrorCode.FILE_NOT_FOUND:
            # 文件不存在，尝试重新创建
            file_path = exception.details.get('file_path')
            if file_path and self.domain_manager:
                logger.info(f"尝试重新创建文件: {file_path}")
                safe_execute(self.domain_manager.save_domains, context="重新创建域名文件")
    
    def _recover_gui(self):
        """恢复GUI"""
        try:
            if self.main_window:
                # 尝试重新创建主窗口
                self.main_window.destroy()
                self.main_window = MainWindow(self.domain_manager, self.network_checker)
                self.main_window.set_minimize_callback(self.tray_manager.show_tray if self.tray_manager else None)
                logger.info("GUI已恢复")
        except Exception as e:
            logger.error(f"GUI恢复失败: {e}")
    
    def _on_critical_error(self, exception: Exception):
        """关键错误回调"""
        try:
            logger.critical(f"发生关键错误，准备安全关闭应用程序: {exception}")
            
            # 保存当前状态
            if self.domain_manager:
                safe_execute(self.domain_manager.save_domains, context="关键错误保存")
            
            # 显示错误通知
            if self.tray_manager:
                safe_execute(
                    self.tray_manager.show_notification,
                    "严重错误",
                    "应用程序遇到严重错误，将自动关闭",
                    context="关键错误通知"
                )
            
            # 延迟关闭，给用户时间看到通知
            threading.Timer(3.0, self.shutdown).start()
            
        except Exception as e:
            logger.error(f"关键错误处理失败: {e}")
    
    def _initialize_components(self):
        """初始化各个组件"""
        try:
            logger.info("开始初始化组件...")
            
            # 初始化域名管理器
            self.domain_manager = safe_execute(
                DomainManager,
                context="初始化域名管理器",
                exception_handler=global_exception_handler
            )
            if not self.domain_manager:
                raise AppException("域名管理器初始化失败", ErrorCode.SYSTEM_RESOURCE_ERROR)
            
            # 初始化网络检查器
            self.network_checker = safe_execute(
                NetworkChecker,
                context="初始化网络检查器",
                exception_handler=global_exception_handler
            )
            if not self.network_checker:
                raise AppException("网络检查器初始化失败", ErrorCode.NETWORK_CONNECTION_ERROR)
            
            # 初始化域名监控器
            self.domain_monitor = safe_execute(
                DomainMonitor,
                self.domain_manager,
                self.network_checker,
                context="初始化域名监控器",
                exception_handler=global_exception_handler
            )
            
            # 初始化主窗口
            self.main_window = safe_execute(
                MainWindow,
                self.domain_manager,
                self.network_checker,
                context="初始化主窗口",
                exception_handler=global_exception_handler
            )
            
            # 系统托盘初始化 - 已移除
            logger.info("跳过系统托盘初始化（已禁用托盘功能）")
            
            logger.info("所有组件初始化完成")
            
        except Exception as e:
            logger.error(f"组件初始化失败: {e}")
            handle_exception(e, "组件初始化")
            raise
    
    def start(self):
        """启动应用程序"""
        try:
            logger.info("启动域名跟踪工具")
            
            # 加载域名数据
            if self.domain_manager:
                safe_execute(
                    self.domain_manager.load_domains,
                    context="加载域名数据",
                    exception_handler=global_exception_handler
                )
            
            # 启动健康检查
            if self.health_checker:
                self.health_checker.start_monitoring()
            
            # 启动域名监控
            if self.domain_monitor:
                safe_execute(
                    self.domain_monitor.start_monitoring,
                    context="启动域名监控",
                    exception_handler=global_exception_handler
                )
            
            # 系统托盘启动 - 已移除
            logger.info("跳过系统托盘启动（已禁用托盘功能）")
            
            # 创建主窗口（但不显示）
            if self.main_window:
                root = safe_execute(
                    self.main_window.create_window,
                    context="创建主窗口",
                    exception_handler=global_exception_handler
                )
                
                if root:
                    # 直接显示主窗口
                    self.running = True
                    logger.info("应用程序启动成功，显示主界面")
                    
                    # 运行主循环
                    try:
                        root.mainloop()
                    except Exception as e:
                        handle_exception(e, "主循环运行")
                else:
                    raise AppException("主窗口创建失败", ErrorCode.GUI_INIT_ERROR)
            else:
                raise AppException("主窗口未初始化", ErrorCode.GUI_INIT_ERROR)
            
        except Exception as e:
            logger.error(f"启动应用程序失败: {e}")
            handle_exception(e, "应用程序启动")
            self.shutdown()
            raise
    
    def show_main_window(self):
        """显示主窗口（线程安全版本）"""
        try:
            logger.info("主程序：收到显示主窗口请求")
            if self.main_window:
                logger.info("主程序：主窗口对象存在，检查root状态")
                # 检查root是否存在，如果不存在则先创建
                if self.main_window.root is None:
                    logger.info("主程序：root为None，先创建窗口")
                    self.main_window.create_window()
                
                if self.main_window.root:
                    logger.info("主程序：root存在，调度到主线程执行")
                    # 使用after方法将GUI操作调度到主线程执行，避免GIL错误
                    self.main_window.root.after(0, self._show_window_safe)
                    logger.info("主程序：已调度show_window到主线程")
                else:
                    logger.error("主程序：无法创建root窗口")
            else:
                logger.error("主程序：主窗口对象不存在")
        except Exception as e:
            logger.error(f"主程序：显示主窗口异常: {e}", exc_info=True)
            handle_exception(e, "显示主窗口")
    
    def _show_window_safe(self):
        """在主线程中安全显示窗口"""
        try:
            logger.info("主程序：在主线程中执行show_window")
            self.main_window.show_window()
            logger.info("主程序：show_window方法调用完成")
        except Exception as e:
            logger.error(f"主程序：主线程显示窗口异常: {e}", exc_info=True)
            handle_exception(e, "主线程显示窗口")
    
    def shutdown(self):
        """关闭应用程序"""
        try:
            logger.info("正在关闭应用程序...")
            
            self.running = False
            
            # 停止健康检查
            if self.health_checker:
                safe_execute(
                    self.health_checker.stop_monitoring,
                    context="停止健康检查",
                    exception_handler=global_exception_handler
                )
            
            # 停止域名监控
            if self.domain_monitor:
                safe_execute(
                    self.domain_monitor.stop_monitoring,
                    context="停止域名监控",
                    exception_handler=global_exception_handler
                )
            
            # 保存域名数据
            if self.domain_manager:
                safe_execute(
                    self.domain_manager.save_domains,
                    context="保存域名数据",
                    exception_handler=global_exception_handler
                )
            
            # 系统托盘停止 - 已移除
            logger.info("跳过系统托盘停止（已禁用托盘功能）")
            
            # 销毁主窗口
            if self.main_window:
                safe_execute(
                    self.main_window.destroy,
                    context="销毁主窗口",
                    exception_handler=global_exception_handler
                )
            
            logger.info("应用程序已关闭")
            
        except Exception as e:
            logger.error(f"关闭应用程序时发生错误: {e}")
            handle_exception(e, "应用程序关闭")
        finally:
            # 强制退出
            os._exit(0)
    
    def get_application_status(self) -> dict:
        """获取应用程序状态"""
        try:
            status = {
                'running': self.running,
                'components': {
                    'domain_manager': self.domain_manager is not None,
                    'network_checker': self.network_checker is not None,
                    'domain_monitor': self.domain_monitor is not None and getattr(self.domain_monitor, 'running', False),
                    'tray_manager': self.tray_manager is not None,
                    'main_window': self.main_window is not None,
                    'health_checker': self.health_checker is not None
                },
                'health': self.health_checker.get_health_status() if self.health_checker else {},
                'domain_count': len(self.domain_manager.domains) if self.domain_manager else 0
            }
            return status
        except Exception as e:
            handle_exception(e, "获取应用程序状态")
            return {'error': str(e)}


def main():
    """主函数"""
    try:
        logger.info(f"启动 {Config.APP_NAME} v{Config.VERSION}")
        
        # 创建并启动域名跟踪器
        tracker = DomainTracker()
        tracker.start()
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.critical(f"程序运行时发生严重错误: {e}")
        handle_exception(e, "主程序")
        sys.exit(1)


if __name__ == "__main__":
    main()