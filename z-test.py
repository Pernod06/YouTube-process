"""
测试文件 - 包含多个测试功能
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv()

# ==================== 测试 YouTube Search (SerpAPI) ====================

async def test_youtube_search():
    """测试 YouTube 搜索服务 (SerpAPI)"""
    print("=" * 60)
    print("🔍 测试 YouTube Search (SerpAPI)")
    print("=" * 60)
    
    # 添加路径以导入服务
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend', 'python-fastapi'))
    
    from youtube_search_service import (
        get_youtube_search_service,
        SearchYouTubeParams,
        search_youtube_videos
    )
    
    # 获取服务实例
    service = get_youtube_search_service()
    
    # 检查 API Key
    if not service.serp_api_key:
        print("❌ 错误: SERP_API_KEY 未配置！")
        print("   请在 .env 文件中添加: SERP_API_KEY=your_key_here")
        return
    
    print(f"✅ SERP API Key 已配置 (长度: {len(service.serp_api_key)})")
    
    # 测试搜索
    search_query = "Python FastAPI tutorial"
    print(f"\n📹 搜索关键词: {search_query}")
    print("-" * 40)
    
    try:
        # 方法1: 使用服务类
        params = SearchYouTubeParams(
            search_query=search_query,
            engine="youtube",
            gl="us",
            hl="en"
        )
        response = await service.search_youtube(params)
        
        print(f"\n✅ 搜索成功! 找到 {len(response.video_results)} 个视频\n")
        
        # 显示前5个结果
        for i, video in enumerate(response.video_results[:5], 1):
            title = video.get('title', 'N/A')
            link = video.get('link', 'N/A')
            channel = video.get('channel', {})
            channel_name = channel.get('name', 'N/A') if isinstance(channel, dict) else channel
            length = video.get('length', 'N/A')
            views = video.get('views', 'N/A')
            
            print(f"  {i}. {title}")
            print(f"     📺 频道: {channel_name}")
            print(f"     ⏱️  时长: {length}")
            print(f"     👁️  观看: {views}")
            print(f"     🔗 链接: {link}")
            print()
        
        # 测试缓存
        print("-" * 40)
        print("🔄 测试缓存功能...")
        
        # 再次搜索（应该命中缓存）
        response2 = await service.search_youtube(params)
        print(f"✅ 第二次搜索完成（应使用缓存）")
        
        # 显示缓存统计
        stats = service.get_cache_stats()
        print(f"📊 缓存统计: 大小={stats['size']}, 最大={stats['maxsize']}, TTL={stats['ttl']}秒")
        
        # 方法2: 使用便捷函数
        print("\n" + "-" * 40)
        print("🔧 测试便捷函数 search_youtube_videos()...")
        results = await search_youtube_videos("machine learning", gl="us")
        print(f"✅ 便捷函数返回 {len(results)} 个结果")
        
    except Exception as e:
        print(f"❌ 搜索失败: {e}")
        import traceback
        traceback.print_exc()


# ==================== 测试 Transcript API ====================

def test_transcript_api():
    """测试 Transcript API"""
    print("\n" + "=" * 60)
    print("📝 测试 Transcript API")
    print("=" * 60)
    
    import requests
    
    API_KEY = os.getenv('TranscriptAPI_KEY')
    if not API_KEY:
        print("❌ 错误: TranscriptAPI_KEY 未配置！")
        return
    
    url = 'https://transcriptapi.com/api/v2/youtube/transcript'
    params = {'video_url': 'YRvf00NooN8', 'format': 'json'}
    
    try:
        r = requests.get(url, params=params, headers={'Authorization': 'Bearer ' + API_KEY}, timeout=30)
        r.raise_for_status()
        transcript = r.json().get('transcript', [])
        print(f"✅ 获取到 {len(transcript) if isinstance(transcript, list) else 'N/A'} 条字幕")
    except Exception as e:
        print(f"❌ 获取字幕失败: {e}")


# ==================== 测试 YouTube Comments ====================

def test_youtube_comments():
    """测试 YouTube 评论获取"""
    print("\n" + "=" * 60)
    print("💬 测试 YouTube Comments")
    print("=" * 60)
    
    try:
        from youtube_client import YouTubeClient
        
        print("[INFO] 正在初始化 YouTube 客户端...")
        client = YouTubeClient()
        
        max_results = 5
        video_id = "zsOYK-sb3Qo"
        
        print(f"[INFO] 正在获取视频 {video_id} 的 {max_results} 条评论...")
        comments = client.get_video_comments(video_id, max_results=max_results)
        
        if comments:
            print(f"✅ 获取到 {len(comments)} 条评论")
            for i, comment in enumerate(comments[:3], 1):
                author = comment.get('author', 'N/A')
                text = comment.get('text', '')[:100]
                print(f"  {i}. {author}: {text}...")
        else:
            print("⚠️ 未获取到评论")
    except Exception as e:
        print(f"❌ 获取评论失败: {e}")


# ==================== 主函数 ====================

if __name__ == "__main__":
    print("\n🚀 开始测试...\n")
    
    # 测试 YouTube Search (SerpAPI) - 主要测试
    asyncio.run(test_youtube_search())
    
    # 取消注释以运行其他测试:
    # test_transcript_api()
    # test_youtube_comments()
    
    print("\n" + "=" * 60)
    print("✨ 测试完成!")
    print("=" * 60)
