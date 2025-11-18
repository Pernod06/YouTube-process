"""
生成使用YouTube缩略图版本的HTML页面
适用于无法嵌入视频的情况
"""

from youtube_client import YouTubeClient
from youtube_transcript_api import YouTubeTranscriptApi


def format_timestamp(seconds: float) -> str:
    """将秒数转换为时间戳格式"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def generate_thumbnail_page(video_url: str, duration_minutes: int = 5):
    """生成使用缩略图的版本"""
    
    print(f"正在生成缩略图版本...")
    
    video_id = YouTubeClient.extract_video_id(video_url)
    if not video_id:
        print(f"无法提取视频ID")
        return None
    
    # 获取字幕
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        transcript_obj = list(transcript_list)[0]
        transcript = transcript_obj.fetch()
    except Exception as e:
        print(f"获取字幕失败: {e}")
        return None
    
    max_seconds = duration_minutes * 60
    filtered_transcript = [entry for entry in transcript if entry.start < max_seconds]
    
    # 生成HTML
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube视频内容 - 缩略图版本</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2em;
            margin-bottom: 10px;
        }}
        
        .main-content {{
            display: grid;
            grid-template-columns: 40% 60%;
            gap: 0;
        }}
        
        .video-section {{
            padding: 30px;
            background: #f8f9fa;
            border-right: 1px solid #e0e0e0;
        }}
        
        .thumbnail-wrapper {{
            position: relative;
            cursor: pointer;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }}
        
        .thumbnail-wrapper img {{
            width: 100%;
            display: block;
        }}
        
        .play-overlay {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 80px;
            height: 80px;
            background: rgba(255, 0, 0, 0.9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 30px;
            color: white;
            transition: transform 0.3s;
        }}
        
        .thumbnail-wrapper:hover .play-overlay {{
            transform: translate(-50%, -50%) scale(1.1);
        }}
        
        .video-links {{
            margin-top: 20px;
            padding: 20px;
            background: white;
            border-radius: 8px;
        }}
        
        .youtube-button {{
            display: block;
            width: 100%;
            padding: 15px;
            background: #ff0000;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            margin-bottom: 10px;
            font-weight: 600;
            text-align: center;
            transition: background 0.3s;
        }}
        
        .youtube-button:hover {{
            background: #cc0000;
        }}
        
        .youtube-button.secondary {{
            background: #667eea;
        }}
        
        .youtube-button.secondary:hover {{
            background: #5568d3;
        }}
        
        .timestamp-links {{
            margin-top: 20px;
            padding: 15px;
            background: #e3f2fd;
            border-radius: 8px;
            border-left: 4px solid #2196f3;
        }}
        
        .timestamp-links h3 {{
            color: #1976d2;
            margin-bottom: 10px;
            font-size: 1.1em;
        }}
        
        .timestamp-link {{
            display: block;
            padding: 8px;
            color: #1976d2;
            text-decoration: none;
            transition: background 0.2s;
        }}
        
        .timestamp-link:hover {{
            background: rgba(33, 150, 243, 0.1);
        }}
        
        .transcript-section {{
            padding: 30px;
            background: white;
        }}
        
        .transcript-header {{
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid #667eea;
        }}
        
        .transcript-header h2 {{
            color: #333;
            font-size: 1.8em;
        }}
        
        .search-box {{
            margin-bottom: 25px;
        }}
        
        .search-box input {{
            width: 100%;
            padding: 15px;
            font-size: 1em;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
        }}
        
        .search-box input:focus {{
            outline: none;
            border-color: #667eea;
        }}
        
        .transcript-list {{
            list-style: none;
        }}
        
        .transcript-item {{
            display: flex;
            gap: 15px;
            padding: 15px;
            margin-bottom: 10px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        
        .timestamp {{
            flex-shrink: 0;
            width: 70px;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            color: #667eea;
        }}
        
        .timestamp-youtube-link {{
            color: #ff0000;
            text-decoration: none;
        }}
        
        .timestamp-youtube-link:hover {{
            text-decoration: underline;
        }}
        
        .transcript-text {{
            flex: 1;
            color: #333;
            line-height: 1.6;
        }}
        
        .highlight {{
            background: #ffeb3b;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        
        @media (max-width: 968px) {{
            .main-content {{
                grid-template-columns: 1fr;
            }}
            
            .video-section {{
                border-right: none;
                border-bottom: 1px solid #e0e0e0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 YouTube 视频内容展示</h1>
            <p>前 {duration_minutes} 分钟字幕与时间戳（缩略图版本）</p>
        </div>
        
        <div class="main-content">
            <div class="video-section">
                <a href="https://www.youtube.com/watch?v={video_id}" target="_blank" class="thumbnail-wrapper">
                    <img src="https://img.youtube.com/vi/{video_id}/maxresdefault.jpg" 
                         alt="Video Thumbnail"
                         onerror="this.src='https://img.youtube.com/vi/{video_id}/hqdefault.jpg'">
                    <div class="play-overlay">▶</div>
                </a>
                
                <div class="video-links">
                    <a href="https://www.youtube.com/watch?v={video_id}" target="_blank" class="youtube-button">
                        ▶️ 在YouTube上观看完整视频
                    </a>
                    <a href="https://www.youtube.com/embed/{video_id}" target="_blank" class="youtube-button secondary">
                        🎥 嵌入播放器版本
                    </a>
                </div>
                
                <div class="timestamp-links">
                    <h3>⏰ 快速跳转</h3>
                    <a href="https://www.youtube.com/watch?v={video_id}&t=0s" target="_blank" class="timestamp-link">
                        ▶ 00:00 - 开始
                    </a>
                    <a href="https://www.youtube.com/watch?v={video_id}&t=60s" target="_blank" class="timestamp-link">
                        ▶ 01:00 - 1分钟处
                    </a>
                    <a href="https://www.youtube.com/watch?v={video_id}&t=120s" target="_blank" class="timestamp-link">
                        ▶ 02:00 - 2分钟处
                    </a>
                    <a href="https://www.youtube.com/watch?v={video_id}&t=180s" target="_blank" class="timestamp-link">
                        ▶ 03:00 - 3分钟处
                    </a>
                    <a href="https://www.youtube.com/watch?v={video_id}&t=240s" target="_blank" class="timestamp-link">
                        ▶ 04:00 - 4分钟处
                    </a>
                </div>
            </div>
            
            <div class="transcript-section">
                <div class="transcript-header">
                    <h2>📝 字幕内容（共 {len(filtered_transcript)} 段）</h2>
                </div>
                
                <div class="search-box">
                    <input type="text" id="searchInput" placeholder="🔍 搜索字幕内容..." onkeyup="searchTranscript()">
                </div>
                
                <ul class="transcript-list" id="transcriptList">
"""
    
    # 添加字幕
    for entry in filtered_transcript:
        timestamp = format_timestamp(entry.start)
        text = entry.text.replace('<', '&lt;').replace('>', '&gt;')
        timestamp_seconds = int(entry.start)
        youtube_link = f"https://www.youtube.com/watch?v={video_id}&t={timestamp_seconds}s"
        
        html_content += f"""
                    <li class="transcript-item">
                        <a href="{youtube_link}" target="_blank" class="timestamp timestamp-youtube-link" title="在YouTube中跳转到此时间">{timestamp}</a>
                        <span class="transcript-text">{text}</span>
                    </li>
"""
    
    html_content += """
                </ul>
            </div>
        </div>
    </div>
    
    <script>
        function searchTranscript() {
            const input = document.getElementById('searchInput');
            const filter = input.value.toLowerCase();
            const list = document.getElementById('transcriptList');
            const items = list.getElementsByClassName('transcript-item');
            
            for (let i = 0; i < items.length; i++) {
                const text = items[i].getElementsByClassName('transcript-text')[0];
                const txtValue = text.textContent || text.innerText;
                
                if (txtValue.toLowerCase().indexOf(filter) > -1) {
                    items[i].style.display = "";
                    
                    if (filter) {
                        const regex = new RegExp(`(${filter})`, 'gi');
                        const highlighted = txtValue.replace(regex, '<span class="highlight">$1</span>');
                        text.innerHTML = highlighted;
                    } else {
                        text.textContent = txtValue;
                    }
                } else {
                    items[i].style.display = "none";
                }
            }
        }
    </script>
</body>
</html>
"""
    
    output_file = "video_thumbnail_version.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✓ 缩略图版本已生成: {output_file}")
    return output_file


if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=7ARBJQn6QkM"
    generate_thumbnail_page(video_url, duration_minutes=5)
    
    print("\n" + "=" * 60)
    print("✅ 缩略图版本生成成功！")
    print("=" * 60)
    print("\n此版本特点：")
    print("  ✓ 使用YouTube缩略图")
    print("  ✓ 所有链接直接跳转到YouTube")
    print("  ✓ 支持时间戳跳转")
    print("  ✓ 无嵌入限制问题")
    print("\n点击缩略图或按钮即可在YouTube上观看！")

