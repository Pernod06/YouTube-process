"""
获取并显示完整的YouTube视频字幕
简化版示例，专注于获取全部字幕内容
"""

import os
import requests
from http.cookiejar import MozillaCookieJar
from youtube_client import YouTubeClient
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig

# ========== 配置区域 ==========

# 代理设置
USE_PROXY = True  # 设置为 False 禁用代理
PROXY_PORT = 59891
PROXY_URL = f"http://127.0.0.1:{PROXY_PORT}" if USE_PROXY else None

# Cookies 文件路径（Netscape 格式）
COOKIES_FILE = "cookies.txt"  # 设置为 None 禁用 cookies

# ========== 配置区域结束 ==========

# 设置环境变量代理（用于 YouTubeClient 和其他库）
if USE_PROXY and PROXY_URL:
    os.environ['HTTP_PROXY'] = PROXY_URL
    os.environ['HTTPS_PROXY'] = PROXY_URL
    os.environ['http_proxy'] = PROXY_URL
    os.environ['https_proxy'] = PROXY_URL
    print(f"✓ 代理已设置: {PROXY_URL}")
else:
    print(f"⚠️ 代理已禁用")

# 创建带有 cookies 和代理的 HTTP 客户端
def create_http_client():
    """创建配置好 cookies 和代理的 HTTP 客户端"""
    session = requests.Session()
    
    # 设置代理（如果启用）
    if USE_PROXY and PROXY_URL:
        session.proxies = {
            'http': PROXY_URL,
            'https': PROXY_URL
        }
    
    # 加载 cookies（如果文件存在）
    if COOKIES_FILE and os.path.exists(COOKIES_FILE):
        try:
            cookie_jar = MozillaCookieJar(COOKIES_FILE)
            cookie_jar.load(ignore_discard=True, ignore_expires=True)
            session.cookies.update(cookie_jar)
            print(f"✓ 已加载 cookies 文件: {COOKIES_FILE} ({len(cookie_jar)} 个 cookies)")
        except Exception as e:
            print(f"⚠️ 无法加载 cookies 文件: {e}")
    elif COOKIES_FILE:
        print(f"⚠️ 未找到 cookies 文件: {COOKIES_FILE}")
    
    return session


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
    获取视频的完整字幕
    
    Args:
        video_url: YouTube视频URL
        language: 语言代码（默认'en'）
    
    Returns:
        字幕列表或None
    """
    print("=" * 70)
    print("获取YouTube视频完整字幕")
    print("=" * 70)
    
    # 提取视频ID
    video_id = YouTubeClient.extract_video_id(video_url)
    if not video_id:
        print(f"❌ 无法从URL提取视频ID: {video_url}")
        return None, None
    
    print(f"\n📹 视频ID: {video_id}")
    print(f"🌐 视频链接: https://www.youtube.com/watch?v={video_id}")

    # 尝试获取视频详情（可选，如果失败不影响字幕获取）
    try:
        details = YouTubeClient().get_video_details(video_id)
    except Exception as e:
        print(f"⚠️ 无法获取视频详情: {e}")
        details = {'title': f'Video {video_id}', 'video_id': video_id}
    
    try:
        # 创建 HTTP 客户端（带 cookies 和代理）
        http_client = create_http_client()
        
        # 获取字幕（使用代理和 cookies）
        api = YouTubeTranscriptApi(http_client=http_client)
        transcript_list = api.list(video_id)
        
        # 显示可用语言
        print(f"\n📚 可用的字幕语言：")
        for t in transcript_list:
            marker = "✓" if t.language_code == language else " "
            print(f"  [{marker}] {t.language} ({t.language_code})")
        
        # 获取指定语言的字幕
        try:
            transcript_obj = transcript_list.find_transcript([language])
            print(f"\n✓ 使用语言: {transcript_obj.language} ({transcript_obj.language_code})")
        except:
            # 如果指定语言不可用，使用第一个
            transcript_obj = list(transcript_list)[0]
            print(f"\n⚠️ 语言 '{language}' 不可用，使用: {transcript_obj.language}")
        
        transcript = transcript_obj.fetch()
        
        print(f"\n✓ 成功获取字幕")
        print(f"  总段数: {len(transcript)}")
        
        # 计算统计信息
        if transcript:
            total_duration = sum(entry.duration for entry in transcript)
            total_chars = sum(len(entry.text) for entry in transcript)
            
            print(f"  总时长: {format_timestamp(total_duration)}")
            print(f"  总字符: {total_chars:,}")
            print(f"  平均每段: {total_duration/len(transcript):.2f}秒")
        
        return transcript, details
        
    except Exception as e:
        print(f"\n❌ 获取字幕失败: {e}")
        return None, None


def display_full_transcript(transcript, output_file=None, details=None):
    """
    显示完整字幕内容
    
    Args:
        transcript: 字幕列表
        output_file: 可选，输出到文件的路径
    """
    if not transcript:
        print("没有字幕数据")
        return
    
    print("\n" + "=" * 70)
    print(f"完整字幕内容（共 {len(transcript)} 段）")
    print("=" * 70 + "\n")
    
    # 准备输出内容
    output_lines = []


    for i, entry in enumerate(transcript, 1):
        timestamp = format_timestamp(entry.start)
        text = entry.text
        duration = entry.duration
        
        # 格式化输出
        line1 = f"[{timestamp}] {text}"
        line2 = f"       持续: {duration:.2f}秒 | 起始: {entry.start:.2f}秒"
        
        print(line1)
        print(line2)
        print()
        
        # 保存到列表（用于文件输出）
        output_lines.append(line1)
        # output_lines.append(line2)
        # output_lines.append("")
        # output_text.append(text)
    
    # 如果指定了输出文件，保存到文件
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"{details['title']}\n")
                f.write("=" * 70 + "\n\n")
                f.write('\n'.join(output_lines))
                # f.write('\n'.join(output_text))
            
            print("\n" + "=" * 70)
            print(f"✓ 字幕已保存到: {output_file}")
            print("=" * 70)
        except Exception as e:
            print(f"\n❌ 保存文件失败: {e}")


def main():
    """主函数"""
    # 视频URL
    video_url = "https://www.youtube.com/watch?v=AF8d72mA41M"
    
    # 获取完整字幕
    transcript, details = get_full_transcript(video_url, language='en')
    
    if transcript and details:
        # 显示完整字幕
        # display_full_transcript(transcript)
        
        # 可选：保存到文件
        display_full_transcript(transcript, output_file="How_to_Build_Agent_transcript.txt", details=details)
        
        print("\n" + "=" * 70)
        print("💡 提示：")
        print("  - 取消注释上面的代码可以将字幕保存到文件")
        print("  - 修改 video_url 变量可以获取其他视频的字幕")
        print("  - 修改 language 参数可以获取其他语言的字幕")
        print("=" * 70)


if __name__ == "__main__":
    main()

