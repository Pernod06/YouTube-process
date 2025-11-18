#!/usr/bin/env python3
"""
YouTube 视频信息获取工具
从 YouTube URL 获取完整的视频信息，包括标题、描述、统计数据、缩略图等
"""

import sys
import json
import re
from datetime import timedelta
from youtube_client import YouTubeClient


def parse_duration(duration_str):
    """
    解析 ISO 8601 时长格式为可读格式
    
    Args:
        duration_str: ISO 8601 格式的时长字符串 (例如: PT1H2M30S)
    
    Returns:
        格式化的时长字符串 (例如: 1:02:30)
    """
    # 提取时、分、秒
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
    match = re.match(pattern, duration_str)
    
    if not match:
        return duration_str
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    # 格式化为可读字符串
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"


def format_number(num):
    """
    格式化数字为易读格式（添加千位分隔符）
    
    Args:
        num: 数字或数字字符串
    
    Returns:
        格式化的数字字符串
    """
    try:
        num = int(num)
        return f"{num:,}"
    except (ValueError, TypeError):
        return str(num)


def get_video_information(url):
    """
    获取 YouTube 视频的完整信息
    
    Args:
        url: YouTube 视频 URL 或视频 ID
    
    Returns:
        视频信息字典
    """
    try:
        # 初始化 YouTube 客户端
        print("正在连接 YouTube API...")
        client = YouTubeClient()
        
        # 提取视频 ID
        video_id = client.extract_video_id(url)
        if not video_id:
            print(f"错误: 无法从 URL 中提取视频 ID: {url}")
            return None
        
        print(f"视频 ID: {video_id}")
        print("正在获取视频信息...\n")
        
        # 获取视频详细信息
        video_info = client.get_video_details(video_id)
        
        if not video_info:
            print("错误: 无法获取视频信息")
            return None
        
        return video_info
        
    except ValueError as e:
        print(f"错误: {e}")
        print("提示: 请确保在 config.py 中设置了 YOUTUBE_API_KEY")
        return None
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def display_video_information(video_info):
    """
    以格式化的方式显示视频信息
    
    Args:
        video_info: 视频信息字典
    """
    print("=" * 80)
    print("YouTube 视频信息")
    print("=" * 80)
    print()
    
    # 基本信息
    print("📺 基本信息")
    print("-" * 80)
    print(f"标题:        {video_info['title']}")
    print(f"视频 ID:     {video_info['video_id']}")
    print(f"频道:        {video_info['channel_title']}")
    print(f"发布时间:    {video_info['published_at']}")
    print(f"时长:        {parse_duration(video_info['duration'])}")
    print()
    
    # 统计信息
    print("📊 统计信息")
    print("-" * 80)
    print(f"观看次数:    {format_number(video_info['view_count'])}")
    print(f"点赞数:      {format_number(video_info['like_count'])}")
    print(f"评论数:      {format_number(video_info['comment_count'])}")
    print()
    
    # 描述
    print("📝 描述")
    print("-" * 80)
    description = video_info['description']
    # 限制描述长度，只显示前 500 个字符
    if len(description) > 500:
        print(description[:500] + "...")
        print(f"\n(完整描述共 {len(description)} 字符)")
    else:
        print(description)
    print()
    
    # 缩略图
    print("🖼️  缩略图")
    print("-" * 80)
    thumbnails = video_info['thumbnails']
    for quality, url in thumbnails.items():
        if url:
            print(f"{quality.capitalize():12} {url}")
    print()
    
    # 视频链接
    print("🔗 链接")
    print("-" * 80)
    print(f"观看链接:    https://www.youtube.com/watch?v={video_info['video_id']}")
    print(f"嵌入链接:    https://www.youtube.com/embed/{video_info['video_id']}")
    print(f"短链接:      https://youtu.be/{video_info['video_id']}")
    print()
    
    print("=" * 80)


def save_to_json(video_info, output_file='video_info.json'):
    """
    将视频信息保存为 JSON 文件
    
    Args:
        video_info: 视频信息字典
        output_file: 输出文件路径
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(video_info, f, ensure_ascii=False, indent=2)
        print(f"✓ 视频信息已保存到: {output_file}")
    except Exception as e:
        print(f"✗ 保存文件失败: {e}")


def main():
    """主函数"""
    print("=" * 80)
    print("YouTube 视频信息获取工具")
    print("=" * 80)
    print()
    
    # 获取 URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # 如果没有提供参数，使用示例 URL
        url = input("请输入 YouTube 视频 URL 或视频 ID: ").strip()
        
        if not url:
            print("使用示例 URL: https://www.youtube.com/watch?v=EF8C4v7JIbA")
            url = "https://www.youtube.com/watch?v=EF8C4v7JIbA"
    
    print()
    
    # 获取视频信息
    video_info = get_video_information(url)
    
    if video_info:
        # 显示信息
        display_video_information(video_info)
        
        # 询问是否保存为 JSON
        save_json = input("\n是否保存为 JSON 文件? (y/n): ").strip().lower()
        if save_json == 'y':
            output_file = input("输入文件名 (默认: video_info.json): ").strip()
            if not output_file:
                output_file = 'video_info.json'
            save_to_json(video_info, output_file)
        
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())

