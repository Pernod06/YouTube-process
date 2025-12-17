"""
获取并显示完整的YouTube视频字幕
使用 youtube_transcript_api（简洁高效的方案）
"""

import os, requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_client import YouTubeClient

# ========== 配置区域 ==========

# 代理设置 - 根据你的网络环境配置
# 如果你在中国大陆，需要配置代理才能访问 YouTube
# USE_PROXY = True  # 设置为 False 禁用代理
# PROXY_PORT = 50142  # 修改为你的代理端口
# PROXY_URL = f"http://127.0.0.1:{PROXY_PORT}" if USE_PROXY else None

# ========== 配置区域结束 ==========


# def setup_proxy():
#     """设置代理环境变量"""
#     if USE_PROXY and PROXY_URL:
#         os.environ['HTTP_PROXY'] = PROXY_URL
#         os.environ['HTTPS_PROXY'] = PROXY_URL
#         os.environ['http_proxy'] = PROXY_URL
#         os.environ['https_proxy'] = PROXY_URL
#         print(f"✓ 代理已设置: {PROXY_URL}")
#         return True
#     else:
#         # 清除代理环境变量
#         for key in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']:
#             os.environ.pop(key, None)
#         print(f"⚠️  代理已禁用")
#         return False


# # 初始化代理设置
# setup_proxy()


def format_timestamp(seconds: float) -> str:
    """将秒数转换为时间戳格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def get_full_transcript(video_url: str, language: str = 'en'):
    """
    获取视频的完整字幕（使用 youtube_transcript_api）
    
    Args:
        video_url: YouTube视频URL
        language: 语言代码（默认'en'）
    
    Returns:
        (字幕列表, 视频详情) 或 (None, None)
    """
    print("=" * 70)
    print("获取YouTube视频完整字幕 (使用 youtube_transcript_api)")
    print("=" * 70)
    
    # 提取视频ID
    video_id = YouTubeClient.extract_video_id(video_url)
    if not video_id:
        print(f"❌ 无法从URL提取视频ID: {video_url}")
        return None, None
    
    print(f"\n📹 视频ID: {video_id}")
    print(f"🌐 视频链接: https://www.youtube.com/watch?v={video_id}")
    print(f"🔍 正在获取字幕...")
    
    try:
        # 获取 API 密钥（支持新旧两种环境变量名）
        API_KEY = os.getenv('TranscriptAPI_KEY') or os.getenv('TRANSCRIPT_API_KEY')
        if not API_KEY:
            print(f"⚠️ 环境变量 TranscriptAPI_KEY 未设置，使用默认密钥...")
            # 默认密钥（可能有使用限制）
            API_KEY = 'sk_xEEnrdnWKBMM4zt6wI8klBfnaX3KspU86fGw1V0oMnU'
            
        url = 'https://transcriptapi.com/api/v2/youtube/transcript'
        params = {'video_url': video_id, 'format': 'json'}
        r = requests.get(url, params=params, headers={'Authorization': 'Bearer ' + API_KEY}, timeout=30)
        response_json = r.json()
        
        # 检查 API 是否返回错误
        if 'error' in response_json:
            print(f"❌ TranscriptAPI 错误: {response_json.get('error')}")
            print(f"   详情: {response_json.get('message', 'N/A')}")
            return None, None
        
        # 检查是否有 detail 字段（API v2 错误格式）
        if 'detail' in response_json and 'transcript' not in response_json:
            print(f"❌ TranscriptAPI 错误: {response_json.get('detail')}")
            return None, None
        
        if 'transcript' not in response_json:
            print(f"❌ API 响应中没有 transcript 字段")
            print(f"   响应内容: {str(response_json)[:200]}...")
            return None, None
            
        transcript = response_json['transcript']
        
        if not transcript or len(transcript) == 0:
            print(f"❌ 该视频没有可用的字幕")
            return None, None
        
        # 使用 YouTubeClient 获取视频标题
        video_title = f'Video {video_id}'
        try:
            yt_client = YouTubeClient()
            video_details = yt_client.get_video_details(video_id)
            if video_details and video_details.get('title'):
                video_title = video_details['title']
                print(f"  ✓ 从 YouTube API 获取标题: {video_title}")
        except Exception as e:
            print(f"  ⚠️ 无法从 YouTube API 获取标题: {e}")
            # 回退到 API 响应中的标题
            video_title = response_json.get('title', f'Video {video_id}')
        
        details = {
            'title': video_title,
            'video_id': video_id,
            'duration': video_details.get('duration', 0) if video_details else 0,
            'view_count': video_details.get('view_count', 0) if video_details else 0,
        }
        
        print(f"\n✓ 成功获取字幕")
        print(f"  总段数: {len(transcript)}")
        
        # 计算统计信息
        # if transcript:
        #     total_duration = sum(entry['duration'] for entry in transcript)
        #     total_chars = sum(len(entry['text']) for entry in transcript)
            
        #     print(f"  总时长: {format_timestamp(total_duration)}")
        #     print(f"  总字符: {total_chars:,}")
        #     print(f"  平均每段: {total_duration/len(transcript):.2f}秒")
        
        return transcript, details
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ 获取字幕失败: {e}")
        
        # 提供更有用的错误提示
        if "ProxyError" in error_msg or "proxy" in error_msg.lower():
            print("\n💡 代理连接失败，请检查:")
            print(f"   1. 代理服务是否正在运行（当前配置: {PROXY_URL}）")
            print(f"   2. 修改 PROXY_PORT = {PROXY_PORT} 为正确的端口")
            print("   3. 或设置 USE_PROXY = False 禁用代理")
        elif "SSL" in error_msg or "ssl" in error_msg.lower():
            print("\n💡 SSL 连接错误，可能原因:")
            print("   1. 网络环境无法直接访问 YouTube")
            print("   2. 需要配置代理访问")
            print(f"   3. 当前代理设置: USE_PROXY={USE_PROXY}, PORT={PROXY_PORT}")
        elif "timeout" in error_msg.lower():
            print("\n💡 连接超时，请检查网络连接")
        
        return None, None


def display_full_transcript(transcript, output_file=None, details=None):
    """
    格式化字幕内容（不打印到控制台）
    
    Args:
        transcript: 字幕列表
        output_file: 可选，输出到文件的路径
        details: 视频详情
    """
    if not transcript:
        return []
    
    # 准备输出内容
    output_lines = []

    for i, entry in enumerate(transcript, 1):
        timestamp = format_timestamp(entry['start'])
        text = entry['text']
        
        # 格式化输出
        line1 = f"[{timestamp}] {text}"
        
        # 保存到列表
        output_lines.append(line1)
    
    # 如果指定了输出文件，保存到文件
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                if details:
                    f.write(f"{details.get('title', 'Unknown Title')}\n")
                    f.write("=" * 70 + "\n\n")
                f.write('\n'.join(output_lines))
        except Exception as e:
            pass  # 静默处理文件保存错误
            
    return output_lines


def main():
    """主函数"""
    # 视频URL
    video_url = "https://www.youtube.com/watch?v=98DcoXwGX6I"
    
    # 获取完整字幕
    transcript, details = get_full_transcript(video_url, language='en')
    
    if transcript and details:
        # 显示完整字幕
        # display_full_transcript(transcript)
        
        # 可选：保存到文件
        output_filename = f"{details.get('title', 'transcript').replace('/', '-')}_transcript_1.txt"
        display_full_transcript(transcript, output_file=output_filename, details=details)

    else:
        print("\n❌ 无法获取字幕")

def test():
    import os, requests
    API_KEY = os.getenv('API_KEY', 'sk_xEEnrdnWKBMM4zt6wI8klBfnaX3KspU86fGw1V0oMnU')
    url = 'https://transcriptapi.com/api/v2/youtube/transcript'
    params = {'video_url': '98DcoXwGX6I', 'format': 'json'}
    r = requests.get(url, params=params, headers={'Authorization': 'Bearer ' + API_KEY}, timeout=30)
    r.raise_for_status()
    print(r.json()['transcript'])

if __name__ == "__main__":
    test()
