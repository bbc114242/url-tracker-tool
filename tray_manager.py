#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统托盘管理模块
实现系统托盘功能，包括最小化、悬停显示、点击复制等
"""

import threading
import time
from typing import Optional, Callable

import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw, ImageFont
import pyperclip

from config import Config, SUCCESS_MESSAGES
from logger import logger


class TrayManager:
    """系统托盘管理器"""
    
    def __init__(self, domain_manager, network_checker):
        self.domain_manager = domain_manager
        self.network_checker = network_checker
        self.tray_icon: Optional[pystray.Icon] = None
        self.is_running = False
        
        # 回调函数
        self.on_show_window: Optional[Callable] = None
        self.on_quit_app: Optional[Callable] = None
        
        # 托盘图标相关
        self.icon_size = Config.TRAY_ICON_SIZE
        self.icon_color = Config.TRAY_ICON_COLOR
        self.icon_bg_color = Config.TRAY_ICON_BG_COLOR
        
        # 状态缓存
        self._last_domain = None
        self._last_status = None
        
    def create_icon_image(self, status: str = 'unknown') -> Image.Image:
        """创建托盘图标图像"""
        try:
            # 创建基础图像
            image = Image.new('RGBA', self.icon_size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # 根据状态选择颜色
            if status == 'active':
                bg_color = '#4CAF50'  # 绿色
                text_color = 'white'
            elif status == 'inactive':
                bg_color = '#F44336'  # 红色
                text_color = 'white'
            elif status == 'checking':
                bg_color = '#FF9800'  # 橙色
                text_color = 'white'
            else:
                bg_color = '#9E9E9E'  # 灰色
                text_color = 'white'
            
            # 绘制圆形背景
            margin = 4
            draw.ellipse(
                [margin, margin, self.icon_size[0] - margin, self.icon_size[1] - margin],
                fill=bg_color,
                outline='white',
                width=2
            )
            
            # 绘制文字
            try:
                # 尝试使用系统字体
                font_size = 20
                font = ImageFont.truetype("arial.ttf", font_size)
            except (OSError, IOError):
                # 如果系统字体不可用，使用默认字体
                font = ImageFont.load_default()
            
            text = 'D'
            
            # 计算文字位置（居中）
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (self.icon_size[0] - text_width) // 2
            y = (self.icon_size[1] - text_height) // 2
            
            draw.text((x, y), text, fill=text_color, font=font)
            
            return image
            
        except Exception as e:
            logger.error(f"创建托盘图标失败: {e}")
            # 返回简单的默认图标
            image = Image.new('RGBA', self.icon_size, '#2196F3')
            return image
    
    def get_current_status(self) -> tuple[str, str]:
        """获取当前状态和域名"""
        try:
            current_domain_info = self.domain_manager.get_current_domain()
            if current_domain_info:
                return current_domain_info.url, 'active'
            else:
                # 检查是否有域名但都不可用
                if self.domain_manager.domains:
                    return "无可用域名", 'inactive'
                else:
                    return "无域名记录", 'unknown'
        except Exception as e:
            logger.error(f"获取当前状态失败: {e}")
            return "状态未知", 'unknown'
    
    def update_tray_tooltip(self):
        """更新托盘提示信息（线程安全版本）"""
        try:
            current_domain, status = self.get_current_status()
            
            if status == 'active':
                tooltip = f"当前域名: {current_domain}"
            elif status == 'inactive':
                tooltip = "没有可用的域名"
            else:
                tooltip = "域名跟踪器 - 状态未知"
            
            # 只在主线程或托盘事件回调中更新图标属性
            if self.tray_icon and hasattr(self.tray_icon, '_running') and self.tray_icon._running:
                try:
                    self.tray_icon.title = tooltip
                    
                    # 如果状态发生变化，更新图标
                    if status != self._last_status:
                        self.tray_icon.icon = self.create_icon_image(status)
                        self._last_status = status
                except Exception as icon_error:
                    logger.warning(f"托盘图标更新失败（可能是线程安全问题）: {icon_error}")
                    
        except Exception as e:
            logger.error(f"更新托盘提示失败: {e}")
    
    def copy_current_domain(self, icon=None, item=None):
        """复制当前域名到剪贴板"""
        try:
            current_domain_info = self.domain_manager.get_current_domain()
            if current_domain_info:
                pyperclip.copy(current_domain_info.url)
                self.show_notification(f"已复制: {current_domain_info.url}")
                logger.info(f"复制域名到剪贴板: {current_domain_info.url}")
            else:
                self.show_notification("没有可用的域名")
                logger.warning("尝试复制域名但没有可用域名")
        except Exception as e:
            error_msg = f"复制域名失败: {str(e)}"
            self.show_notification(error_msg)
            logger.error(error_msg)
    
    def check_domains_status(self, icon=None, item=None):
        """检查所有域名状态"""
        def check_thread():
            try:
                self.show_notification("正在检查域名状态...")
                
                # 更新图标状态为检查中
                if self.tray_icon:
                    self.tray_icon.icon = self.create_icon_image('checking')
                
                # 检查所有域名
                domains = self.domain_manager.domains
                if domains:
                    results = self.network_checker.check_multiple_domains(domains)
                    
                    # 更新域名状态
                    active_count = 0
                    for domain in domains:
                        if domain.url in results:
                            is_accessible, message = results[domain.url]
                            self.domain_manager.update_domain_status(
                                domain.url, is_accessible, None if is_accessible else message
                            )
                            if is_accessible:
                                active_count += 1
                    
                    # 清理无效域名
                    removed = self.domain_manager.cleanup_invalid_domains()
                    
                    # 排序域名
                    self.domain_manager.sort_domains_by_priority()
                    
                    # 显示结果
                    if active_count > 0:
                        current_domain_info = self.domain_manager.get_current_domain()
                        if current_domain_info:
                            self.show_notification(f"检查完成，当前域名: {current_domain_info.url}")
                        else:
                            self.show_notification(f"检查完成，发现 {active_count} 个可用域名")
                    else:
                        self.show_notification("检查完成，没有可用域名")
                    
                    if removed:
                        logger.info(f"清理了 {len(removed)} 个无效域名")
                else:
                    self.show_notification("没有域名需要检查")
                
                # 更新托盘状态
                self.update_tray_tooltip()
                
            except Exception as e:
                error_msg = f"检查域名状态失败: {str(e)}"
                self.show_notification(error_msg)
                logger.error(error_msg)
        
        # 在后台线程中执行检查
        threading.Thread(target=check_thread, daemon=True).start()
    
    def show_main_window(self, icon=None, item=None):
        """显示主窗口"""
        try:
            logger.info("托盘菜单：尝试显示主窗口")
            if self.on_show_window:
                logger.info("托盘菜单：调用回调函数显示主窗口")
                # 添加防重复调用机制
                if not hasattr(self, '_showing_window') or not self._showing_window:
                    self._showing_window = True
                    try:
                        self.on_show_window()
                        logger.info("托盘菜单：回调函数调用完成")
                    finally:
                        self._showing_window = False
                else:
                    logger.info("托盘菜单：窗口正在显示中，跳过重复调用")
            else:
                logger.warning("托盘菜单：on_show_window回调函数未设置")
            logger.debug("显示主窗口")
        except Exception as e:
            logger.error(f"显示主窗口失败: {e}", exc_info=True)
            if hasattr(self, '_showing_window'):
                self._showing_window = False
    
    def quit_application(self, icon=None, item=None):
        """退出应用程序"""
        try:
            logger.info("用户请求退出应用程序")
            self.stop()
            if self.on_quit_app:
                self.on_quit_app()
        except Exception as e:
            logger.error(f"退出应用程序失败: {e}")
    
    def show_notification(self, message: str, title: str = None):
        """显示系统通知"""
        try:
            if self.tray_icon:
                display_title = title or Config.APP_NAME
                self.tray_icon.notify(message, display_title)
                logger.debug(f"显示通知: {message}")
        except Exception as e:
            logger.error(f"显示通知失败: {e}")
    
    def create_menu(self) -> pystray.Menu:
        """创建托盘菜单"""
        try:
            menu_items = [
                item('显示主界面', self.show_main_window, default=True),
                item('复制当前域名', self.copy_current_domain),
                item('检查域名状态', self.check_domains_status),
                pystray.Menu.SEPARATOR,
                item('域名统计', self.show_domain_statistics),
                pystray.Menu.SEPARATOR,
                item('退出', self.quit_application)
            ]
            
            return pystray.Menu(*menu_items)
        except Exception as e:
            logger.error(f"创建托盘菜单失败: {e}")
            # 返回简单菜单
            return pystray.Menu(
                item('显示主界面', self.show_main_window),
                item('退出', self.quit_application)
            )
    
    def show_domain_statistics(self, icon=None, item=None):
        """显示域名统计信息"""
        try:
            stats = self.domain_manager.get_domain_statistics()
            message = (
                f"域名统计:\n"
                f"总数: {stats['total']}\n"
                f"可用: {stats['active']}\n"
                f"不可用: {stats['inactive']}\n"
                f"错误: {stats['error']}\n"
                f"未知: {stats['unknown']}"
            )
            self.show_notification(message, "域名统计")
        except Exception as e:
            logger.error(f"显示域名统计失败: {e}")
            self.show_notification("获取统计信息失败")
    
    def start(self):
        """启动托盘图标"""
        try:
            if self.is_running:
                logger.warning("托盘图标已在运行")
                return
            
            # 创建初始图标
            initial_icon = self.create_icon_image('unknown')
            
            # 创建托盘图标
            self.tray_icon = pystray.Icon(
                name="domain_tracker",
                icon=initial_icon,
                title="域名跟踪器",
                menu=self.create_menu()
            )
            
            # 设置双击事件
            self.tray_icon.default_action = self.show_main_window
            
            self.is_running = True
            
            # 启动定期更新
            self._start_update_timer()
            
            logger.info("托盘图标已启动")
            
            # 运行托盘图标（阻塞调用）
            self.tray_icon.run()
            
        except Exception as e:
            logger.error(f"启动托盘图标失败: {e}")
            self.is_running = False
    
    def _start_update_timer(self):
        """启动定期更新定时器（已禁用以避免线程安全问题）"""
        # 注释掉定期更新功能以避免GIL错误
        # 托盘图标会在需要时自动更新，无需强制定期更新
        logger.info("托盘定期更新已禁用以确保线程安全")
        pass
    
    def stop(self):
        """停止托盘图标"""
        try:
            self.is_running = False
            if self.tray_icon:
                self.tray_icon.stop()
                self.tray_icon = None
            logger.info("托盘图标已停止")
        except Exception as e:
            logger.error(f"停止托盘图标失败: {e}")
    
    def set_callbacks(self, on_show_window: Callable = None, on_quit_app: Callable = None):
        """设置回调函数"""
        self.on_show_window = on_show_window
        self.on_quit_app = on_quit_app
    
    def is_tray_available(self) -> bool:
        """检查系统托盘是否可用"""
        try:
            # 简单检查，实际可用性可能需要更复杂的检测
            return True
        except Exception:
            return False