"""
测试YouTube API连接
快速验证API密钥是否正确配置
"""

from youtube_client import YouTubeClient


def test_connection():
    """测试API连接"""
    print("=" * 50)
    print("正在测试YouTube API连接...")
    print("=" * 50)
    
    try:
        # 创建客户端
        client = YouTubeClient()
        print("✓ 客户端创建成功")
        
        # 尝试进行一个简单的搜索测试
        print("\n正在测试API搜索功能...")
        videos = client.search_videos("test", max_results=1)
        
        if videos:
            print("✓ API搜索测试成功")
            print(f"\n找到视频: {videos[0]['title']}")
            print(f"频道: {videos[0]['channel_title']}")
            print("\n" + "=" * 50)
            print("✓ YouTube API连接测试通过！")
            print("=" * 50)
            return True
        else:
            print("⚠ 搜索返回空结果，但连接成功")
            return True
            
    except ValueError as e:
        print(f"✗ 配置错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        print("\n可能的原因：")
        print("1. API密钥无效")
        print("2. API配额已用完")
        print("3. 网络连接问题")
        print("4. YouTube API服务未启用")
        return False


if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)

