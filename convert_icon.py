#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图标转换脚本
创建应用程序图标
"""

from PIL import Image, ImageDraw
import os

def create_icon(ico_path, sizes=[16, 32, 48, 64]):
    """
    创建应用程序图标
    
    Args:
        ico_path: 输出ICO文件路径
        sizes: 图标尺寸列表
    """
    try:
        images = []
        
        # 为每个尺寸生成图像
        for size in sizes:
            # 创建新图像
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # 计算比例
            scale = size / 64.0
            
            # 绘制背景圆形
            margin = int(2 * scale)
            circle_size = size - 2 * margin
            draw.ellipse(
                [margin, margin, margin + circle_size, margin + circle_size],
                fill=(74, 144, 226, 255),  # 蓝色背景
                outline=(53, 122, 189, 255),
                width=max(1, int(2 * scale))
            )
            
            # 绘制网络节点
            center = size // 2
            node_size = max(2, int(4 * scale))
            
            # 中心节点
            draw.ellipse(
                [center - node_size, center - node_size, center + node_size, center + node_size],
                fill=(80, 227, 194, 255)  # 青色节点
            )
            
            # 周围节点
            positions = [
                (int(size * 0.25), int(size * 0.3)),
                (int(size * 0.75), int(size * 0.3)),
                (int(size * 0.25), int(size * 0.7)),
                (int(size * 0.75), int(size * 0.7))
            ]
            
            small_node = max(1, int(3 * scale))
            for x, y in positions:
                draw.ellipse(
                    [x - small_node, y - small_node, x + small_node, y + small_node],
                    fill=(80, 227, 194, 255)
                )
                
                # 连接线
                draw.line(
                    [x, y, center, center],
                    fill=(255, 255, 255, 200),
                    width=max(1, int(2 * scale))
                )
            
            # 中心监控圆环
            ring_size = max(4, int(8 * scale))
            draw.ellipse(
                [center - ring_size, center - ring_size, center + ring_size, center + ring_size],
                fill=None,
                outline=(255, 255, 255, 150),
                width=max(1, int(2 * scale))
            )
            
            # 状态指示器
            if size >= 32:
                status_x = int(size * 0.8)
                status_y = int(size * 0.2)
                status_size = max(2, int(6 * scale))
                draw.ellipse(
                    [status_x - status_size, status_y - status_size, 
                     status_x + status_size, status_y + status_size],
                    fill=(126, 211, 33, 255)  # 绿色状态
                )
            
            images.append(img)
        
        # 保存为ICO文件
        images[0].save(
            ico_path,
            format='ICO',
            sizes=[(img.width, img.height) for img in images],
            append_images=images[1:]
        )
        
        print(f"成功创建图标: {ico_path}")
        return True
        
    except Exception as e:
        print(f"创建图标失败: {e}")
        return False

if __name__ == "__main__":
    # 创建图标
    ico_file = "icon.ico"
    
    success = create_icon(ico_file)
    if success:
        print(f"图标已生成: {ico_file}")
    else:
        print("图标创建失败")