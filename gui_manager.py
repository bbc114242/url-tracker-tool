#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI管理模块
实现主界面的创建和管理功能
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import threading
import webbrowser
from datetime import datetime
from typing import Optional, Callable

from config import Config, SUCCESS_MESSAGES, ERROR_MESSAGES
from logger import logger
from domain_manager import DomainInfo


class DomainListFrame(ttk.Frame):
    """域名列表框架"""
    
    def __init__(self, parent, domain_manager, network_checker):
        super().__init__(parent)
        self.domain_manager = domain_manager
        self.network_checker = network_checker
        
        self.setup_ui()
        self.refresh_list()
    
    def setup_ui(self):
        """设置UI"""
        # 标题
        title_label = ttk.Label(self, text="域名历史记录", font=('Arial', 12, 'bold'))
        title_label.pack(pady=(0, 10))
        
        # 列表框架
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建Treeview
        columns = ('status', 'url', 'added_time', 'last_check', 'check_count')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)
        
        # 设置列标题
        self.tree.heading('status', text='状态')
        self.tree.heading('url', text='域名')
        self.tree.heading('added_time', text='添加时间')
        self.tree.heading('last_check', text='最后检查')
        self.tree.heading('check_count', text='检查次数')
        
        # 设置列宽
        self.tree.column('status', width=60, minwidth=50)
        self.tree.column('url', width=300, minwidth=200)
        self.tree.column('added_time', width=120, minwidth=100)
        self.tree.column('last_check', width=120, minwidth=100)
        self.tree.column('check_count', width=80, minwidth=60)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定事件
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<Button-3>', self.on_right_click)  # 右键菜单
        
        # 创建右键菜单
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="复制域名", command=self.copy_selected_domain)
        self.context_menu.add_command(label="在浏览器中打开", command=self.open_in_browser)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="检查此域名", command=self.check_selected_domain)
        self.context_menu.add_command(label="删除域名", command=self.delete_selected_domain)
    
    def refresh_list(self):
        """刷新域名列表"""
        try:
            from logger import logger
            logger.info(f"GUI：开始刷新域名列表，当前域名数量: {len(self.domain_manager.domains)}")
            
            # 清空现有项目
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # 添加域名项目
            for i, domain in enumerate(self.domain_manager.domains):
                status_text = self.get_status_text(domain.status)
                added_time = self.format_datetime(domain.added_time)
                last_check = self.format_datetime(domain.last_check) if domain.last_check else "未检查"
                
                item_id = self.tree.insert('', 'end', values=(
                    status_text,
                    domain.url,
                    added_time,
                    last_check,
                    domain.check_count
                ))
                
                # 设置行颜色
                if domain.status == 'active':
                    self.tree.set(item_id, 'status', '✓ 可用')
                    self.tree.item(item_id, tags=('active',))
                elif domain.status == 'inactive':
                    self.tree.set(item_id, 'status', '✗ 不可用')
                    self.tree.item(item_id, tags=('inactive',))
                elif domain.status == 'error':
                    self.tree.set(item_id, 'status', '⚠ 错误')
                    self.tree.item(item_id, tags=('error',))
                else:
                    self.tree.set(item_id, 'status', '? 未知')
                    self.tree.item(item_id, tags=('unknown',))
            
            # 配置标签样式
            self.tree.tag_configure('active', background='#E8F5E8')
            self.tree.tag_configure('inactive', background='#FFE8E8')
            self.tree.tag_configure('error', background='#FFF3E0')
            self.tree.tag_configure('unknown', background='#F5F5F5')
            
        except Exception as e:
            logger.error(f"刷新域名列表失败: {e}")
    
    def get_status_text(self, status: str) -> str:
        """获取状态文本"""
        status_map = {
            'active': '✓ 可用',
            'inactive': '✗ 不可用',
            'error': '⚠ 错误',
            'unknown': '? 未知'
        }
        return status_map.get(status, '? 未知')
    
    def format_datetime(self, datetime_str: str) -> str:
        """格式化日期时间"""
        try:
            if not datetime_str:
                return ""
            dt = datetime.fromisoformat(datetime_str)
            return dt.strftime('%m-%d %H:%M')
        except Exception:
            return datetime_str[:16] if len(datetime_str) > 16 else datetime_str
    
    def get_selected_domain(self) -> Optional[str]:
        """获取选中的域名"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            values = self.tree.item(item, 'values')
            return values[1] if len(values) > 1 else None
        return None
    
    def on_double_click(self, event):
        """双击事件"""
        domain_url = self.get_selected_domain()
        if domain_url:
            self.open_in_browser()
    
    def on_right_click(self, event):
        """右键点击事件"""
        # 选中右键点击的项目
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def copy_selected_domain(self):
        """复制选中的域名"""
        domain_url = self.get_selected_domain()
        if domain_url:
            try:
                import pyperclip
                pyperclip.copy(domain_url)
                messagebox.showinfo("成功", f"已复制域名: {domain_url}")
            except Exception as e:
                messagebox.showerror("错误", f"复制失败: {e}")
    
    def open_in_browser(self):
        """在浏览器中打开选中的域名"""
        domain_url = self.get_selected_domain()
        if domain_url:
            try:
                webbrowser.open(domain_url)
                logger.info(f"在浏览器中打开: {domain_url}")
            except Exception as e:
                messagebox.showerror("错误", f"打开浏览器失败: {e}")
    
    def check_selected_domain(self):
        """检查选中的域名"""
        domain_url = self.get_selected_domain()
        if domain_url:
            def check_thread():
                try:
                    is_accessible, message, _ = self.network_checker.check_domain_simple(domain_url)
                    self.domain_manager.update_domain_status(domain_url, is_accessible, None if is_accessible else message)
                    
                    # 在主线程中更新UI
                    self.after(0, self.refresh_list)
                    self.after(0, lambda: messagebox.showinfo("检查结果", f"域名: {domain_url}\n状态: {'可用' if is_accessible else '不可用'}\n信息: {message}"))
                except Exception as e:
                    self.after(0, lambda: messagebox.showerror("错误", f"检查域名失败: {e}"))
            
            threading.Thread(target=check_thread, daemon=True).start()
    
    def delete_selected_domain(self):
        """删除选中的域名"""
        domain_url = self.get_selected_domain()
        if domain_url:
            if messagebox.askyesno("确认删除", f"确定要删除域名 {domain_url} 吗？"):
                if self.domain_manager.remove_domain(domain_url):
                    self.refresh_list()
                    messagebox.showinfo("成功", "域名已删除")
                else:
                    messagebox.showerror("错误", "删除域名失败")


class ControlPanel(ttk.Frame):
    """控制面板"""
    
    def __init__(self, parent, domain_manager, network_checker, on_minimize=None):
        super().__init__(parent)
        self.domain_manager = domain_manager
        self.network_checker = network_checker
        # self.on_minimize = on_minimize  # 已移除最小化功能
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        # 按钮框架
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 第一行按钮
        row1_frame = ttk.Frame(button_frame)
        row1_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(row1_frame, text="添加域名", command=self.add_domain).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(row1_frame, text="获取最新域名", command=self.get_latest_domains).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(row1_frame, text="检查所有域名", command=self.check_all_domains).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(row1_frame, text="复制当前域名", command=self.copy_current_domain).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(row1_frame, text="清理无效域名", command=self.cleanup_domains).pack(side=tk.LEFT, padx=(0, 5))
        
        # 第二行按钮
        row2_frame = ttk.Frame(button_frame)
        row2_frame.pack(fill=tk.X)
        
        ttk.Button(row2_frame, text="导出域名", command=self.export_domains).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(row2_frame, text="导入域名", command=self.import_domains).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(row2_frame, text="域名统计", command=self.show_statistics).pack(side=tk.LEFT, padx=(0, 5))
        
        # 最小化按钮已移除
        # if self.on_minimize:
        #     ttk.Button(row2_frame, text="最小化到托盘", command=self.on_minimize).pack(side=tk.RIGHT)
    
    def add_domain(self):
        """添加域名对话框"""
        dialog = AddDomainDialog(self, self.domain_manager, self.network_checker)
        self.wait_window(dialog)
        
        # 刷新父窗口的域名列表
        if hasattr(self.master, 'domain_list_frame'):
            self.master.domain_list_frame.refresh_list()
        
        # 更新状态栏显示当前域名
        if hasattr(self.master, 'status_bar'):
            self.master.status_bar.update_status()
    
    def get_latest_domains(self):
        """获取最新重定向域名"""
        def get_latest_thread():
            try:
                domains = self.domain_manager.domains
                if not domains:
                    self.after(0, lambda: messagebox.showinfo("提示", "没有域名可以检查重定向"))
                    return
                
                # 显示进度对话框
                progress_dialog = ProgressDialog(self, "获取最新域名", len(domains))
                
                new_domains_found = []
                total_redirects = 0
                
                for i, domain in enumerate(domains):
                    # 更新进度
                    progress_dialog.update_progress(i, f"检查重定向: {domain.url}")
                    
                    # 查找重定向域名
                    redirected_domains = self.network_checker.find_redirected_domains(domain.url)
                    
                    for new_domain in redirected_domains:
                        # 检查是否已存在
                        if not any(d.url == new_domain for d in self.domain_manager.domains):
                            # 添加新域名
                            success, message = self.domain_manager.add_domain(new_domain)
                            if success:
                                new_domains_found.append(new_domain)
                                total_redirects += 1
                
                # 完成检查
                progress_dialog.update_progress(len(domains), "获取完成")
                progress_dialog.close()
                
                # 显示结果
                def show_result():
                    if new_domains_found:
                        domain_list = "\n".join([f"• {domain}" for domain in new_domains_found[:10]])
                        if len(new_domains_found) > 10:
                            domain_list += f"\n... 还有 {len(new_domains_found) - 10} 个域名"
                        
                        messagebox.showinfo(
                            "发现新域名", 
                            f"成功发现并添加了 {total_redirects} 个新域名：\n\n{domain_list}"
                        )
                    else:
                        messagebox.showinfo("完成", "未发现新的重定向域名")
                    
                    # 刷新域名列表
                    # 通过父级组件访问同级的domain_list_frame
                    parent = self.master  # main_frame
                    for child in parent.winfo_children():
                        if isinstance(child, DomainListFrame):
                            child.refresh_list()
                            break
                
                self.after(0, show_result)
                
            except Exception as e:
                def show_error():
                    messagebox.showerror("错误", f"获取最新域名时发生错误: {e}")
                
                self.after(0, show_error)
        
        threading.Thread(target=get_latest_thread, daemon=True).start()
    
    def check_all_domains(self):
        """检查所有域名"""
        def check_thread():
            try:
                domains = self.domain_manager.domains
                if not domains:
                    self.after(0, lambda: messagebox.showinfo("提示", "没有域名需要检查"))
                    return
                
                # 显示进度对话框
                progress_dialog = ProgressDialog(self, "检查域名状态", len(domains))
                
                results = self.network_checker.check_multiple_domains(domains)
                
                active_count = 0
                for i, domain in enumerate(domains):
                    if domain.url in results:
                        is_accessible, message = results[domain.url]
                        self.domain_manager.update_domain_status(
                            domain.url, is_accessible, None if is_accessible else message
                        )
                        if is_accessible:
                            active_count += 1
                    
                    # 更新进度
                    progress_dialog.update_progress(i + 1, f"检查: {domain.url}")
                
                # 清理无效域名
                removed = self.domain_manager.cleanup_invalid_domains()
                self.domain_manager.sort_domains_by_priority()
                
                progress_dialog.close()
                
                # 显示结果
                result_msg = f"检查完成\n可用域名: {active_count}\n总域名数: {len(domains)}"
                if removed:
                    result_msg += f"\n清理无效域名: {len(removed)}"
                
                self.after(0, lambda: messagebox.showinfo("检查结果", result_msg))
                
                # 刷新列表
                if hasattr(self.master, 'domain_list_frame'):
                    self.after(0, self.master.domain_list_frame.refresh_list)
                
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", f"检查域名失败: {e}"))
        
        threading.Thread(target=check_thread, daemon=True).start()
    
    def copy_current_domain(self):
        """复制当前域名"""
        try:
            current_domain_info = self.domain_manager.get_current_domain()
            if current_domain_info:
                import pyperclip
                pyperclip.copy(current_domain_info.url)
                messagebox.showinfo("成功", f"已复制当前域名: {current_domain_info.url}")
            else:
                messagebox.showwarning("提示", "没有可用的域名")
        except Exception as e:
            messagebox.showerror("错误", f"复制域名失败: {e}")
    
    def cleanup_domains(self):
        """清理无效域名"""
        if messagebox.askyesno("确认清理", "确定要清理所有无效域名吗？这将删除错误次数过多的域名。"):
            try:
                removed = self.domain_manager.cleanup_invalid_domains()
                if removed:
                    messagebox.showinfo("清理完成", f"已清理 {len(removed)} 个无效域名")
                    if hasattr(self.master, 'domain_list_frame'):
                        self.master.domain_list_frame.refresh_list()
                else:
                    messagebox.showinfo("清理完成", "没有需要清理的域名")
            except Exception as e:
                messagebox.showerror("错误", f"清理域名失败: {e}")
    
    def export_domains(self):
        """导出域名"""
        try:
            file_path = filedialog.asksaveasfilename(
                title="导出域名列表",
                defaultextension=".json",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
            )
            
            if file_path:
                if self.domain_manager.export_domains(file_path):
                    messagebox.showinfo("成功", f"域名列表已导出到: {file_path}")
                else:
                    messagebox.showerror("错误", "导出域名列表失败")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def import_domains(self):
        """导入域名"""
        try:
            file_path = filedialog.askopenfilename(
                title="导入域名列表",
                filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
            )
            
            if file_path:
                success, message = self.domain_manager.import_domains(file_path)
                if success:
                    messagebox.showinfo("成功", message)
                    if hasattr(self.master, 'domain_list_frame'):
                        self.master.domain_list_frame.refresh_list()
                else:
                    messagebox.showerror("错误", message)
        except Exception as e:
            messagebox.showerror("错误", f"导入失败: {e}")
    
    def show_statistics(self):
        """显示统计信息"""
        try:
            stats = self.domain_manager.get_domain_statistics()
            
            stats_window = tk.Toplevel(self)
            stats_window.title("域名统计")
            stats_window.geometry("300x200")
            stats_window.resizable(False, False)
            
            # 居中显示
            stats_window.transient(self)
            stats_window.grab_set()
            
            main_frame = ttk.Frame(stats_window, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(main_frame, text="域名统计信息", font=('Arial', 12, 'bold')).pack(pady=(0, 15))
            
            stats_text = f"""总域名数: {stats['total']}
可用域名: {stats['active']}
不可用域名: {stats['inactive']}
错误域名: {stats['error']}
未知状态: {stats['unknown']}"""
            
            ttk.Label(main_frame, text=stats_text, justify=tk.LEFT).pack()
            
            ttk.Button(main_frame, text="关闭", command=stats_window.destroy).pack(pady=(15, 0))
            
        except Exception as e:
            messagebox.showerror("错误", f"显示统计信息失败: {e}")


class AddDomainDialog(tk.Toplevel):
    """添加域名对话框"""
    
    def __init__(self, parent, domain_manager, network_checker):
        super().__init__(parent)
        self.domain_manager = domain_manager
        self.network_checker = network_checker
        
        self.title("添加域名")
        self.geometry("400x200")
        self.resizable(False, False)
        
        # 居中显示
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui()
        
        # 焦点设置
        self.url_entry.focus_set()
    
    def setup_ui(self):
        """设置UI"""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        ttk.Label(main_frame, text="添加新域名", font=('Arial', 12, 'bold')).pack(pady=(0, 15))
        
        # 输入框
        ttk.Label(main_frame, text="域名地址:").pack(anchor=tk.W)
        self.url_entry = ttk.Entry(main_frame, width=50)
        self.url_entry.pack(fill=tk.X, pady=(5, 10))
        self.url_entry.bind('<Return>', lambda e: self.add_domain())
        
        # 验证选项
        self.verify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text="添加前验证域名可访问性", variable=self.verify_var).pack(anchor=tk.W, pady=(0, 15))
        
        # 按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="添加", command=self.add_domain).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT)
    
    def add_domain(self):
        """添加域名"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "请输入域名地址")
            return
        
        def add_thread():
            try:
                # 验证域名格式
                is_valid, message = self.domain_manager.validate_domain(url)
                if not is_valid:
                    self.after(0, lambda: messagebox.showerror("错误", f"域名格式无效: {message}"))
                    return
                
                # 如果需要验证可访问性
                if self.verify_var.get():
                    is_accessible, check_message, _ = self.network_checker.check_domain_simple(url)
                    if not is_accessible:
                        result = messagebox.askyesno(
                            "域名不可访问", 
                            f"域名验证失败: {check_message}\n\n是否仍要添加此域名？"
                        )
                        if not result:
                            return
                
                # 添加域名
                success, add_message = self.domain_manager.add_domain(url)
                if success:
                    self.after(0, lambda: messagebox.showinfo("成功", add_message))
                    self.after(0, self.destroy)
                else:
                    self.after(0, lambda: messagebox.showerror("错误", add_message))
                
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("错误", f"添加域名失败: {e}"))
        
        threading.Thread(target=add_thread, daemon=True).start()


class ProgressDialog(tk.Toplevel):
    """进度对话框"""
    
    def __init__(self, parent, title: str, max_value: int):
        super().__init__(parent)
        self.title(title)
        self.geometry("400x120")
        self.resizable(False, False)
        
        # 居中显示
        self.transient(parent)
        self.grab_set()
        
        self.max_value = max_value
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 状态标签
        self.status_label = ttk.Label(main_frame, text="准备中...")
        self.status_label.pack(pady=(0, 10))
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, length=350, mode='determinate')
        self.progress.pack(fill=tk.X)
        self.progress['maximum'] = self.max_value
    
    def update_progress(self, value: int, status: str = None):
        """更新进度"""
        self.progress['value'] = value
        if status:
            self.status_label.config(text=status)
        self.update()
    
    def close(self):
        """关闭对话框"""
        self.destroy()


class StatusBar(ttk.Frame):
    """状态栏"""
    
    def __init__(self, parent, domain_manager):
        super().__init__(parent)
        self.domain_manager = domain_manager
        
        self.setup_ui()
        self.update_status()
    
    def setup_ui(self):
        """设置UI"""
        # 状态标签
        self.status_label = ttk.Label(self, text="就绪")
        self.status_label.pack(side=tk.LEFT)
        
        # 分隔符
        ttk.Separator(self, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # 当前域名标签
        self.current_domain_label = ttk.Label(self, text="当前域名: 无")
        self.current_domain_label.pack(side=tk.LEFT)
        
        # GitHub链接按钮
        github_frame = ttk.Frame(self)
        github_frame.pack(side=tk.RIGHT, padx=(10, 0))
        
        github_btn = ttk.Button(
            github_frame, 
            text="📁 GitHub", 
            command=self.open_github,
            width=10
        )
        github_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 时间标签
        self.time_label = ttk.Label(self, text="")
        self.time_label.pack(side=tk.RIGHT)
        
        # 定期更新时间
        self.update_time()
    
    def update_status(self, status: str = "就绪"):
        """更新状态"""
        self.status_label.config(text=status)
        
        # 更新当前域名
        try:
            current_domain_info = self.domain_manager.get_current_domain()
            if current_domain_info:
                domain_text = current_domain_info.url
                if len(domain_text) > 50:
                    domain_text = domain_text[:47] + "..."
                self.current_domain_label.config(text=f"当前域名: {domain_text}")
            else:
                self.current_domain_label.config(text="当前域名: 无可用域名")
        except Exception as e:
            logger.error(f"更新状态栏失败: {e}")
    
    def update_time(self):
        """更新时间显示"""
        try:
            current_time = datetime.now().strftime('%H:%M:%S')
            self.time_label.config(text=current_time)
            self.after(1000, self.update_time)  # 每秒更新
        except Exception:
            pass
    
    def open_github(self):
        """打开GitHub链接"""
        try:
            github_url = "https://github.com/bbc114242/url-tracker-tool"
            webbrowser.open(github_url)
            logger.info(f"打开GitHub链接: {github_url}")
        except Exception as e:
            logger.error(f"打开GitHub链接失败: {e}")
            messagebox.showerror("错误", f"无法打开GitHub链接: {e}")


class MainWindow:
    """主窗口管理器"""
    
    def __init__(self, domain_manager, network_checker):
        self.domain_manager = domain_manager
        self.network_checker = network_checker
        self.root = None
        self.on_minimize_callback = None
        
    def create_window(self):
        """创建主窗口"""
        from logger import logger
        logger.info("GUI：开始创建主窗口")
        
        if self.root is not None:
            logger.info("GUI：窗口已存在，直接显示")
            self.root.deiconify()
            self.root.lift()
            return self.root
        
        logger.info("GUI：创建新的Tk窗口")
        self.root = tk.Tk()
        self.root.title(Config.APP_NAME)
        self.root.geometry(f"{Config.WINDOW_WIDTH}x{Config.WINDOW_HEIGHT}")
        self.root.minsize(Config.WINDOW_MIN_WIDTH, Config.WINDOW_MIN_HEIGHT)
        logger.info("GUI：主窗口基本属性设置完成")
        
        # 设置窗口图标
        try:
            import os
            icon_path = os.path.join(os.path.dirname(__file__), 'icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                logger.info(f"GUI：成功设置窗口图标: {icon_path}")
            else:
                logger.warning(f"GUI：图标文件不存在: {icon_path}")
        except Exception as e:
            logger.warning(f"GUI：设置窗口图标失败: {e}")
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 域名列表框架
        self.domain_list_frame = DomainListFrame(main_frame, self.domain_manager, self.network_checker)
        self.domain_list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 控制面板
        self.control_panel = ControlPanel(
            main_frame, 
            self.domain_manager, 
            self.network_checker, 
            on_minimize=None  # 移除最小化功能
        )
        self.control_panel.pack(fill=tk.X, pady=(0, 10))
        
        # 状态栏
        self.status_bar = StatusBar(main_frame, self.domain_manager)
        self.status_bar.pack(fill=tk.X)
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.quit_application)
        
        return self.root
    
    def quit_application(self):
        """退出应用程序"""
        if self.root:
            self.root.quit()
            self.root.destroy()
    
    def show_window(self):
        """显示窗口"""
        try:
            from logger import logger
            logger.info("GUI管理器：开始显示窗口")
            
            # 检查窗口是否存在且有效
            if self.root is None or not self.root.winfo_exists():
                logger.warning("GUI管理器：root窗口不存在或无效，重新创建窗口")
                self.create_window()
            
            if self.root:
                logger.info("GUI管理器：root窗口存在，执行显示操作")
                try:
                    self.root.deiconify()
                    self.root.lift()
                    self.root.focus_force()
                    logger.info("GUI管理器：窗口显示操作完成")
                    
                    # 刷新数据
                    if hasattr(self, 'domain_list_frame'):
                        self.domain_list_frame.refresh_list()
                    if hasattr(self, 'status_bar'):
                        self.status_bar.update_status()
                    logger.info("GUI管理器：数据刷新完成")
                except tk.TclError as e:
                    logger.error(f"GUI管理器：tkinter错误，重新创建窗口: {e}")
                    self.root = None
                    self.create_window()
                    if self.root:
                        self.root.deiconify()
                        self.root.lift()
                        self.root.focus_force()
            else:
                logger.error("GUI管理器：无法创建或显示窗口")
        except Exception as e:
            from logger import logger
            logger.error(f"GUI管理器：显示窗口异常: {e}", exc_info=True)
    
    def set_minimize_callback(self, callback: Callable):
        """设置最小化回调"""
        self.on_minimize_callback = callback
    
    def destroy(self):
        """销毁窗口"""
        if self.root:
            self.root.destroy()
            self.root = None