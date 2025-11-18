"""
获取YouTube视频字幕（Transcript）和时间戳的示例

注意：YouTube Data API v3的captions.download需要OAuth 2.0认证。
我们使用youtube-transcript-api库，它更简单且不需要API密钥。
"""

from youtube_client import YouTubeClient


def install_transcript_api():
    """检查并提示安装youtube-transcript-api"""
    try:
        import youtube_transcript_api
        return True
    except ImportError:
        print("=" * 60)
        print("⚠️  需要安装 youtube-transcript-api 库")
        print("=" * 60)
        print("\n请运行以下命令安装：")
        print("\n方式1（推荐 - 使用清华源）：")
        print("pip install -i https://pypi.tuna.tsinghua.edu.cn/simple youtube-transcript-api")
        print("\n方式2（标准安装）：")
        print("pip install youtube-transcript-api")
        print("\n或在虚拟环境中：")
        print("source .my_env/bin/activate")
        print("pip install -i https://pypi.tuna.tsinghua.edu.cn/simple youtube-transcript-api")
        print("=" * 60)
        return False


def get_transcript_with_timestamps(video_url: str, language: str = 'en'):
    """
    获取视频字幕和时间戳
    
    Args:
        video_url: YouTube视频URL
        language: 语言代码（en=英文, zh-Hans=简体中文, zh-Hant=繁体中文）
    
    Returns:
        字幕列表，每项包含text（文本）、start（开始时间）、duration（持续时间）
    """
    if not install_transcript_api():
        return None
    
    from youtube_transcript_api import YouTubeTranscriptApi
    
    # 提取视频ID
    video_id = YouTubeClient.extract_video_id(video_url)
    if not video_id:
        print(f"无法从URL提取视频ID: {video_url}")
        return None
    
    print(f"视频ID: {video_id}")
    
    try:
        # 创建API实例并获取字幕列表
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        # 尝试获取指定语言的字幕
        try:
            transcript = transcript_list.find_transcript([language])
            return transcript.fetch()
        except:
            # 如果指定语言不可用，获取第一个可用的字幕
            print(f"语言 '{language}' 不可用，尝试获取其他语言...")
            
            # 显示可用的字幕
            print("\n可用的字幕语言：")
            for t in transcript_list:
                print(f"  - {t.language} ({t.language_code})")
            
            # 获取第一个可用的字幕
            first_transcript = list(transcript_list)[0]
            print(f"\n使用语言: {first_transcript.language} ({first_transcript.language_code})")
            return first_transcript.fetch()
            
    except Exception as e:
        print(f"获取字幕失败: {e}")
        return None


def format_timestamp(seconds: float) -> str:
    """
    将秒数转换为时间戳格式 HH:MM:SS
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的时间戳字符串
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def example_basic_transcript(video_url: str):
    """示例1：获取基本字幕"""
    print("\n" + "=" * 60)
    print("示例1: 获取视频字幕和时间戳")
    print("=" * 60)
    
    print(f"\n视频URL: {video_url}")
    
    # 获取字幕（先尝试中文，如果没有则获取英文）
    transcript = get_transcript_with_timestamps(video_url, language='zh-Hans')
    
    if not transcript:
        print("尝试获取英文字幕...")
        transcript = get_transcript_with_timestamps(video_url, language='en')
    
    if transcript:
        print(f"\n✓ 成功获取字幕，共 {len(transcript)} 段\n")
        print("前5段字幕预览：\n")
        
        for i, entry in enumerate(transcript, 1):
            timestamp = format_timestamp(entry.start)
            text = entry.text
            duration = entry.duration
            
            print(f"[{timestamp}] {text}")
            print(f"         (持续时间: {duration:.2f}秒)\n")
    else:
        print("❌ 无法获取字幕")


def example_search_in_transcript(video_url: str, keyword: str):
    """示例2：在字幕中搜索关键词"""
    print("\n" + "=" * 60)
    print("示例2: 在字幕中搜索关键词")
    print("=" * 60)
    
    transcript = get_transcript_with_timestamps(video_url, language='zh-Hans')
    
    if not transcript:
        transcript = get_transcript_with_timestamps(video_url, language='en')
    
    if transcript:
        print(f"\n搜索关键词: '{keyword}'\n")
        
        results = []
        for entry in transcript:
            if keyword.lower() in entry.text.lower():
                results.append(entry)
        
        if results:
            print(f"找到 {len(results)} 处匹配：\n")
            for i, entry in enumerate(results[:10], 1):  # 只显示前10个结果
                timestamp = format_timestamp(entry.start)
                print(f"{i}. [{timestamp}] {entry.text}")
        else:
            print(f"未找到包含 '{keyword}' 的字幕")
    else:
        print("❌ 无法获取字幕")


def example_export_transcript(video_url: str, output_file: str = "transcript.txt"):
    """示例3：导出字幕到文件"""
    print("\n" + "=" * 60)
    print("示例3: 导出字幕到文件")
    print("=" * 60)
    
    transcript = get_transcript_with_timestamps(video_url, language='zh-Hans')
    
    if not transcript:
        transcript = get_transcript_with_timestamps(video_url, language='en')
    
    if transcript:
        with open(output_file, 'w', encoding='utf-8') as f:
            # 写入标题
            f.write(f"YouTube视频字幕\n")
            f.write(f"视频URL: {video_url}\n")
            f.write(f"总段落数: {len(transcript)}\n")
            f.write("=" * 60 + "\n\n")
            
            # 写入字幕内容
            for entry in transcript:
                timestamp = format_timestamp(entry.start)
                f.write(f"[{timestamp}] {entry.text}\n")
        
        print(f"✓ 字幕已导出到: {output_file}")
        print(f"  共 {len(transcript)} 段")
    else:
        print("❌ 无法获取字幕")


def example_transcript_summary(video_url: str):
    """示例4：生成字幕摘要统计"""
    print("\n" + "=" * 60)
    print("示例4: 字幕统计信息")
    print("=" * 60)
    
    transcript = get_transcript_with_timestamps(video_url, language='zh-Hans')
    
    if not transcript:
        transcript = get_transcript_with_timestamps(video_url, language='en')
    
    if transcript:
        total_duration = sum(entry.duration for entry in transcript)
        total_words = sum(len(entry.text.split()) for entry in transcript)
        total_chars = sum(len(entry.text) for entry in transcript)
        
        print(f"\n字幕统计：")
        print(f"  • 总段落数: {len(transcript)}")
        print(f"  • 总时长: {format_timestamp(total_duration)}")
        print(f"  • 总字数: {total_words} 词")
        print(f"  • 总字符数: {total_chars} 字符")
        print(f"  • 平均每段时长: {total_duration/len(transcript):.2f} 秒")
        
        # 显示最长的3段字幕
        longest_entries = sorted(transcript, key=lambda x: len(x.text), reverse=True)[:3]
        print(f"\n最长的3段字幕：")
        for i, entry in enumerate(longest_entries, 1):
            timestamp = format_timestamp(entry.start)
            text_preview = entry.text[:50] + "..." if len(entry.text) > 50 else entry.text
            print(f"  {i}. [{timestamp}] {text_preview} ({len(entry.text)} 字符)")
    else:
        print("❌ 无法获取字幕")


def example_get_transcript_at_time(video_url: str, target_time: int):
    """示例5：获取特定时间点的字幕"""
    print("\n" + "=" * 60)
    print("示例5: 获取特定时间点的字幕")
    print("=" * 60)
    
    transcript = get_transcript_with_timestamps(video_url, language='zh-Hans')
    
    if not transcript:
        transcript = get_transcript_with_timestamps(video_url, language='en')
    
    if transcript:
        print(f"\n目标时间: {format_timestamp(target_time)}\n")
        
        # 找到目标时间对应的字幕
        for entry in transcript:
            if entry.start <= target_time < entry.start + entry.duration:
                print(f"找到对应字幕：")
                print(f"  时间: {format_timestamp(entry.start)}")
                print(f"  内容: {entry.text}")
                
                # 显示前后文（上下各2条）
                idx = transcript.index(entry)
                print(f"\n上下文：")
                
                start_idx = max(0, idx - 2)
                end_idx = min(len(transcript), idx + 3)
                
                for i in range(start_idx, end_idx):
                    prefix = ">>> " if i == idx else "    "
                    ts = format_timestamp(transcript[i].start)
                    print(f"{prefix}[{ts}] {transcript[i].text}")
                return
        
        print(f"在时间 {format_timestamp(target_time)} 未找到字幕")
    else:
        print("❌ 无法获取字幕")


def main():
    """运行示例"""
    print("\n" + "=" * 60)
    print("YouTube 字幕获取示例")
    print("=" * 60)
    
    # 测试视频URL
    video_url = "https://www.youtube.com/watch?v=kMhle4o0uk0"
    
    # 运行示例
    example_basic_transcript(video_url)
    
    # 取消注释以下行运行其他示例
    # example_search_in_transcript(video_url, keyword="Python")
    # example_export_transcript(video_url, output_file="transcript.txt")
    # example_transcript_summary(video_url)
    # example_get_transcript_at_time(video_url, target_time=120)  # 2分钟处
    
    print("\n" + "=" * 60)
    print("💡 提示：")
    print("  • 取消main()中的注释来运行更多示例")
    print("  • 可以修改video_url变量测试其他视频")
    print("=" * 60)


if __name__ == "__main__":
    main()

