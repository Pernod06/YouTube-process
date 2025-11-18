"""
通过URL访问YouTube视频内容的示例
演示如何从YouTube URL获取视频信息
"""

from youtube_client import YouTubeClient


def example_extract_video_id():
    """示例：从不同格式的URL中提取视频ID"""
    print("\n" + "=" * 60)
    print("示例1: 提取视频ID")
    print("=" * 60)
    
    # 测试不同格式的YouTube URL
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://www.youtube.com/v/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "dQw4w9WgXcQ",  # 直接使用视频ID
    ]
    
    print("\n支持的URL格式：\n")
    for url in test_urls:
        video_id = YouTubeClient.extract_video_id(url)
        print(f"URL: {url}")
        print(f"视频ID: {video_id}\n")


def example_get_video_by_url(url):
    """示例：通过URL获取视频详细信息"""
    print("\n" + "=" * 60)
    print("示例2: 通过URL获取视频信息")
    print("=" * 60)
    
    try:
        # 创建客户端
        client = YouTubeClient()
        
        # 测试URL（这是一个真实的YouTube视频）
        test_url = url
        
        print(f"\n正在获取视频信息...")
        print(f"URL: {test_url}\n")
        
        # 通过URL获取视频信息
        video_info = client.get_video_by_url(test_url)
        
        if video_info:
            print("=" * 60)
            print("视频详细信息：")
            print("=" * 60)
            print(f"标题: {video_info['title']}")
            print(f"频道: {video_info['channel_title']}")
            print(f"发布时间: {video_info['published_at']}")
            print(f"观看次数: {video_info['view_count']}")
            print(f"点赞数: {video_info['like_count']}")
            print(f"评论数: {video_info['comment_count']}")
            print(f"视频时长: {video_info['duration']}")
            
            # 显示缩略图信息（如果可用）
            if 'thumbnails' in video_info:
                thumbnails = video_info['thumbnails']
                best_thumbnail = (thumbnails.get('maxres') or 
                                thumbnails.get('standard') or 
                                thumbnails.get('high') or 
                                thumbnails.get('medium') or 
                                thumbnails.get('default'))
                if best_thumbnail:
                    print(f"缩略图: {best_thumbnail}")
            
            print(f"\n描述:\n{video_info['description'][:200]}...")
        else:
            print("❌ 无法获取视频信息")
            
    except Exception as e:
        print(f"错误: {e}")


def example_batch_process_urls():
    """示例：批量处理多个URL"""
    print("\n" + "=" * 60)
    print("示例3: 批量处理YouTube URL")
    print("=" * 60)
    
    try:
        client = YouTubeClient()
        
        # 要处理的视频URL列表
        urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/jNQXAC9IVRw",  # 另一个示例视频
        ]
        
        print(f"\n正在处理 {len(urls)} 个视频URL...\n")
        
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] 处理: {url}")
            video_info = client.get_video_by_url(url)
            
            if video_info:
                print(f"  ✓ 标题: {video_info['title']}")
                print(f"  ✓ 观看次数: {video_info['view_count']}")
            else:
                print(f"  ✗ 获取失败")
                
    except Exception as e:
        print(f"错误: {e}")


def example_get_comments_by_url():
    """示例：通过URL获取视频评论"""
    print("\n" + "=" * 60)
    print("示例4: 通过URL获取视频评论")
    print("=" * 60)
    
    try:
        client = YouTubeClient()
        
        url = "https://www.youtube.com/watch?v=EF8C4v7JIbA"
        print(f"\nURL: {url}")
        
        # 提取视频ID
        video_id = client.extract_video_id(url)
        print(f"视频ID: {video_id}\n")
        
        # 获取评论
        print("正在获取评论...")
        comments = client.get_video_comments(video_id, max_results=5)
        
        if comments:
            print(f"\n找到 {len(comments)} 条评论:\n")
            for i, comment in enumerate(comments, 1):
                print(f"{i}. {comment['author']}")
                print(f"   {comment['text'][:100]}...")
                print(f"   点赞数: {comment['like_count']}\n")
        else:
            print("该视频没有评论或评论已关闭")
            
    except Exception as e:
        print(f"错误: {e}")


def example_get_video_thumbnails(url):
    """示例：通过URL获取视频缩略图"""
    print("\n" + "=" * 60)
    print("示例5: 获取视频缩略图")
    print("=" * 60)
    
    try:
        # 创建客户端
        client = YouTubeClient()
        
        print(f"\n正在获取视频缩略图...")
        print(f"URL: {url}\n")
        
        # 通过URL获取视频信息
        video_info = client.get_video_by_url(url)
        
        if video_info and 'thumbnails' in video_info:
            print("=" * 60)
            print("视频缩略图信息：")
            print("=" * 60)
            print(f"标题: {video_info['title']}")
            print(f"视频ID: {video_info['video_id']}\n")
            
            thumbnails = video_info['thumbnails']
            
            # 显示所有可用的缩略图尺寸
            print("📸 可用的缩略图尺寸：\n")
            
            thumbnail_sizes = {
                'default': ('默认', '120x90'),
                'medium': ('中等', '320x180'),
                'high': ('高清', '480x360'),
                'standard': ('标准', '640x480'),
                'maxres': ('最高清', '1280x720')
            }
            
            for key, (name, size) in thumbnail_sizes.items():
                url_value = thumbnails.get(key)
                if url_value:
                    print(f"  ✓ {name:6} ({size:10}): {url_value}")
                else:
                    print(f"  ✗ {name:6} ({size:10}): 不可用")
            
            # 推荐使用的缩略图
            print("\n💡 推荐使用：")
            if thumbnails.get('maxres'):
                print(f"  最高清缩略图: {thumbnails['maxres']}")
            elif thumbnails.get('standard'):
                print(f"  标准缩略图: {thumbnails['standard']}")
            elif thumbnails.get('high'):
                print(f"  高清缩略图: {thumbnails['high']}")
            elif thumbnails.get('medium'):
                print(f"  中等缩略图: {thumbnails['medium']}")
            else:
                print(f"  默认缩略图: {thumbnails.get('default', '无')}")
            
        elif video_info:
            print("⚠️  视频信息获取成功，但未找到缩略图数据")
        else:
            print("❌ 无法获取视频信息")
            
    except Exception as e:
        print(f"错误: {e}")


def example_get_thumbnail_by_quality():
    """示例：通过质量等级直接获取缩略图URL（无需API调用）"""
    print("\n" + "=" * 60)
    print("示例6: 直接构建缩略图URL（无需API调用）")
    print("=" * 60)
    
    # 测试视频ID
    video_id = "EF8C4v7JIbA"
    
    print(f"\n视频ID: {video_id}\n")
    
    # 方法1: 获取特定质量的缩略图
    print("=" * 60)
    print("方法1: 获取特定质量的缩略图")
    print("=" * 60)
    
    maxres_url = YouTubeClient.get_thumbnail_url_by_quality(video_id, 'maxresdefault')
    print(f"最高清 (1920x1080): {maxres_url}")
    
    hq_url = YouTubeClient.get_thumbnail_url_by_quality(video_id, 'hqdefault')
    print(f"高清 (480x360):    {hq_url}")
    
    # 方法2: 获取所有质量的缩略图
    print("\n" + "=" * 60)
    print("方法2: 获取所有可用质量的缩略图")
    print("=" * 60 + "\n")
    
    all_thumbnails = YouTubeClient.get_all_thumbnail_urls(video_id)
    
    quality_info = {
        'maxresdefault': ('最高清', '1920x1080'),
        'sddefault': ('标清', '640x480'),
        'hqdefault': ('高清', '480x360'),
        'mqdefault': ('中等', '320x180'),
        'default': ('默认', '120x90'),
        'frame_0': ('帧0', '变化'),
        'frame_1': ('帧1', '变化'),
        'frame_2': ('帧2', '变化'),
        'frame_3': ('帧3', '变化'),
    }
    
    for key, url in all_thumbnails.items():
        name, size = quality_info.get(key, (key, '未知'))
        print(f"{name:8} ({size:10}): {url}")
    
    print("\n" + "=" * 60)
    print("💡 说明")
    print("=" * 60)
    print("✓ 这些URL可以直接使用，无需API密钥")
    print("✓ 部分视频可能没有maxresdefault（最高清）")
    print("✓ frame_0-3 是视频不同位置的缩略图")
    print("✓ 可以在HTML <img> 标签中直接使用这些URL")
    print("\n示例HTML:")
    print(f'<img src="{maxres_url}" alt="Video Thumbnail">')


def example_url_types():
    """示例：展示所有支持的URL格式"""
    print("\n" + "=" * 60)
    print("示例7: YouTube URL格式说明")
    print("=" * 60)
    
    url_formats = {
        "标准格式": "https://www.youtube.com/watch?v=VIDEO_ID",
        "短链接": "https://youtu.be/VIDEO_ID",
        "嵌入格式": "https://www.youtube.com/embed/VIDEO_ID",
        "旧版格式": "https://www.youtube.com/v/VIDEO_ID",
        "移动端": "https://m.youtube.com/watch?v=VIDEO_ID",
        "纯视频ID": "VIDEO_ID",
    }
    
    print("\n✅ 支持的YouTube URL格式：\n")
    for name, format_url in url_formats.items():
        print(f"  • {name:12} : {format_url}")
    
    print("\n💡 提示：")
    print("  - 所有格式都可以直接使用 get_video_by_url() 方法")
    print("  - 视频ID长度为11个字符（字母、数字、下划线、连字符）")
    print("  - 如果URL包含时间戳（&t=参数），会被自动忽略")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("YouTube URL 访问示例集")
    print("=" * 60)
    
    try:
        # 不需要API密钥的示例
        print("\n" + "=" * 60)
        print("📌 以下示例不需要API密钥")
        print("=" * 60)
        
        # 示例1：提取视频ID（不需要API密钥）
        # example_extract_video_id()
        
        # 示例6：直接构建缩略图URL（不需要API密钥）
        example_get_thumbnail_by_quality()
        
        # 示例7：URL格式说明（不需要API密钥）
        # example_url_types()
        
        # 以下示例需要有效的API密钥
        print("\n" + "=" * 60)
        print("⚠️  以下示例需要有效的YouTube API密钥")
        print("=" * 60)
        
        # 取消注释以下行来运行需要API密钥的示例
        # example_get_video_by_url(url="https://www.youtube.com/watch?v=7ARBJQn6QkM&t=679s")
        # example_get_video_thumbnails(url="https://www.youtube.com/watch?v=7ARBJQn6QkM&t=679s")
        # example_batch_process_urls()
        # example_get_comments_by_url()
        
        print("\n💡 提示：获取API密钥后，取消main()函数中的注释来运行完整示例")
        
    except Exception as e:
        print(f"\n错误: {e}")
        print("\n请确保：")
        print("1. 已安装所有依赖包")
        print("2. API密钥配置正确（config.py）")
        print("3. 网络连接正常")


if __name__ == "__main__":
    main()

