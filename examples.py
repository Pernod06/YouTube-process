"""
YouTube API 使用示例
展示各种常见的API操作
"""

from youtube_client import YouTubeClient
import json


def example_1_search_videos():
    """示例1: 搜索视频"""
    print("\n" + "=" * 60)
    print("示例1: 搜索视频")
    print("=" * 60)
    
    client = YouTubeClient()
    
    # 搜索Python相关视频
    videos = client.search_videos("Python编程教程", max_results=5)
    
    print(f"\n找到 {len(videos)} 个视频:\n")
    for i, video in enumerate(videos, 1):
        print(f"{i}. {video['title']}")
        print(f"   频道: {video['channel_title']}")
        print(f"   视频ID: {video['video_id']}")
        print(f"   发布时间: {video['published_at']}")
        print()


def example_2_video_details():
    """示例2: 获取视频详细信息"""
    print("\n" + "=" * 60)
    print("示例2: 获取视频详细信息")
    print("=" * 60)
    
    client = YouTubeClient()
    
    # 首先搜索一个视频
    videos = client.search_videos("Python tutorial", max_results=1)
    
    if videos:
        video_id = videos[0]['video_id']
        print(f"\n获取视频 {video_id} 的详细信息...\n")
        
        # 获取详细信息
        details = client.get_video_details(video_id)
        
        if details:
            print(f"标题: {details['title']}")
            print(f"频道: {details['channel_title']}")
            print(f"发布时间: {details['published_at']}")
            print(f"时长: {details['duration']}")
            print(f"观看次数: {details['view_count']}")
            print(f"点赞数: {details['like_count']}")
            print(f"评论数: {details['comment_count']}")
            print(f"\n描述: {details['description'][:200]}...")


def example_3_video_comments():
    """示例3: 获取视频评论"""
    print("\n" + "=" * 60)
    print("示例3: 获取视频评论")
    print("=" * 60)
    
    client = YouTubeClient()
    
    # 搜索一个视频
    videos = client.search_videos("popular video", max_results=1)
    
    if videos:
        video_id = videos[0]['video_id']
        print(f"\n获取视频 {video_id} 的评论...\n")
        
        # 获取评论
        comments = client.get_video_comments(video_id, max_results=5)
        
        if comments:
            print(f"找到 {len(comments)} 条评论:\n")
            for i, comment in enumerate(comments, 1):
                print(f"{i}. {comment['author']}")
                print(f"   {comment['text'][:100]}...")
                print(f"   点赞数: {comment['like_count']}")
                print()
        else:
            print("该视频没有评论或评论已关闭")


def example_4_channel_info():
    """示例4: 获取频道信息"""
    print("\n" + "=" * 60)
    print("示例4: 获取频道信息")
    print("=" * 60)
    
    client = YouTubeClient()
    
    # 先搜索一个视频，从中获取频道ID
    videos = client.search_videos("programming", max_results=1)
    
    if videos:
        # 需要先获取视频详情来找到频道ID
        # 注意：search结果中没有直接的频道ID
        print("\n提示：要获取频道信息，需要频道ID")
        print("频道ID可以从视频详情或YouTube频道页面URL中获取")
        print("\n示例频道ID格式: UC_x5XG1OV2P6uZZ5FSM9Ttw")


def example_5_trending_search():
    """示例5: 搜索不同类型的内容"""
    print("\n" + "=" * 60)
    print("示例5: 搜索不同类型的内容")
    print("=" * 60)
    
    client = YouTubeClient()
    
    # 搜索不同主题
    topics = ["人工智能", "机器学习", "Web开发", "数据科学"]
    
    for topic in topics:
        print(f"\n搜索主题: {topic}")
        videos = client.search_videos(topic, max_results=3)
        
        if videos:
            print(f"找到 {len(videos)} 个视频:")
            for video in videos:
                print(f"  - {video['title']}")


def example_6_export_to_json():
    """示例6: 导出搜索结果到JSON文件"""
    print("\n" + "=" * 60)
    print("示例6: 导出搜索结果到JSON")
    print("=" * 60)
    
    client = YouTubeClient()
    
    # 搜索视频
    videos = client.search_videos("Python数据分析", max_results=10)
    
    # 导出到JSON文件
    output_file = "search_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)
    
    print(f"\n✓ 已导出 {len(videos)} 个视频信息到 {output_file}")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("YouTube API 使用示例集")
    print("=" * 60)
    
    try:
        # 运行各个示例
        example_1_search_videos()
        
        # 其他示例可以根据需要启用
        # example_2_video_details()
        # example_3_video_comments()
        # example_4_channel_info()
        # example_5_trending_search()
        # example_6_export_to_json()
        
        print("\n" + "=" * 60)
        print("示例运行完成！")
        print("=" * 60)
        print("\n提示：取消注释 main() 函数中的其他示例来运行更多功能")
        
    except Exception as e:
        print(f"\n错误: {e}")
        print("\n请确保：")
        print("1. 已安装所有依赖包")
        print("2. API密钥配置正确")
        print("3. 网络连接正常")


if __name__ == "__main__":
    main()

