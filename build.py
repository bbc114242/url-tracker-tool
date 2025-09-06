#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
域名跟踪器打包脚本
用于将Python应用程序打包成可执行文件
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

def clean_build_dirs():
    """清理构建目录"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"已清理目录: {dir_name}")

def create_spec_file():
    """创建PyInstaller规格文件"""
    spec_content = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'requests',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        'json',
        'configparser',
        'threading',
        'queue',
        'webbrowser'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='域名跟踪器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
    
    with open('domain_tracker.spec', 'w', encoding='utf-8') as f:
        f.write(spec_content)
    print("已创建PyInstaller规格文件: domain_tracker.spec")

def build_exe():
    """构建可执行文件"""
    try:
        # 使用规格文件构建
        cmd = ['pyinstaller', '--clean', 'domain_tracker.spec']
        print(f"执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print("\n✅ 构建成功!")
            print(f"可执行文件位置: {os.path.abspath('dist/域名跟踪器.exe')}")
        else:
            print("\n❌ 构建失败!")
            print("错误输出:")
            print(result.stderr)
            
    except FileNotFoundError:
        print("❌ 错误: 未找到pyinstaller命令")
        print("请先安装pyinstaller: pip install pyinstaller")
        return False
    except Exception as e:
        print(f"❌ 构建过程中发生错误: {e}")
        return False
    
    return result.returncode == 0

def create_release_package():
    """创建发布包"""
    if not os.path.exists('dist/域名跟踪器.exe'):
        print("❌ 未找到可执行文件，请先构建")
        return False
    
    # 创建发布目录
    release_dir = 'release'
    if os.path.exists(release_dir):
        shutil.rmtree(release_dir)
    os.makedirs(release_dir)
    
    # 复制可执行文件
    shutil.copy2('dist/域名跟踪器.exe', release_dir)
    
    # 创建使用说明
    readme_content = '''
# 域名跟踪器 v1.0.0

## 使用说明

1. 双击 `域名跟踪器.exe` 启动程序
2. 在界面中添加需要监控的域名
3. 程序会自动检查域名状态
4. 数据文件存储在用户目录下的 `.domain_tracker` 文件夹中

## 功能特性

- 域名状态实时监控
- 响应时间统计
- 域名管理（添加、删除、编辑）
- 自动保存配置
- 简洁的图形界面

## 系统要求

- Windows 10 或更高版本
- 网络连接

## 数据存储

程序数据存储在以下位置：
- 配置文件: `%USERPROFILE%\.domain_tracker\domains.json`
- 日志文件: `%USERPROFILE%\.domain_tracker\app.log`

## 技术支持

如有问题，请检查日志文件或联系开发者。
'''
    
    with open(f'{release_dir}/README.txt', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"\n✅ 发布包创建完成: {os.path.abspath(release_dir)}")
    print("包含文件:")
    for file in os.listdir(release_dir):
        print(f"  - {file}")
    
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("域名跟踪器打包脚本")
    print("=" * 50)
    
    # 检查当前目录
    if not os.path.exists('main.py'):
        print("❌ 错误: 未找到main.py文件，请在项目根目录运行此脚本")
        return
    
    print("\n1. 清理构建目录...")
    clean_build_dirs()
    
    print("\n2. 创建PyInstaller规格文件...")
    create_spec_file()
    
    print("\n3. 开始构建可执行文件...")
    if build_exe():
        print("\n4. 创建发布包...")
        create_release_package()
        print("\n🎉 打包完成！")
    else:
        print("\n❌ 打包失败，请检查错误信息")

if __name__ == '__main__':
    main()