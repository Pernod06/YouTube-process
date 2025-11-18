"""
生成YouTube视频前N分钟内容的HTML页面
包含视频播放器和字幕展示
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


def generate_html_page(video_url: str, duration_minutes: int = 5, output_file: str = "video_transcript.html"):
    """
    生成显示视频和字幕的HTML页面
    
    Args:
        video_url: YouTube视频URL
        duration_minutes: 显示前N分钟的内容
        output_file: 输出的HTML文件名
    """
    print(f"正在处理视频: {video_url}")
    print(f"提取前 {duration_minutes} 分钟的内容...")
    
    # 提取视频ID
    video_id = YouTubeClient.extract_video_id(video_url)
    if not video_id:
        print(f"无法提取视频ID")
        return None
    
    print(f"视频ID: {video_id}")
    
    # 获取视频信息
    try:
        client = YouTubeClient()
        video_info = client.get_video_details(video_id)
    except:
        video_info = None
        print("⚠️ 无法获取视频详情（需要有效的API密钥）")
    
    # 获取字幕
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        # 尝试获取英文字幕
        try:
            transcript_obj = transcript_list.find_transcript(['en'])
        except:
            # 如果没有英文，获取第一个可用的
            transcript_obj = list(transcript_list)[0]
        
        print(f"使用字幕语言: {transcript_obj.language}")
        transcript = transcript_obj.fetch()
        
    except Exception as e:
        print(f"获取字幕失败: {e}")
        return None
    
    # 筛选前N分钟的字幕
    max_seconds = duration_minutes * 60
    filtered_transcript = [entry for entry in transcript if entry.start < max_seconds]
    
    print(f"✓ 成功获取 {len(filtered_transcript)} 段字幕（前{duration_minutes}分钟）")
    
    # 生成HTML
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube视频前{duration_minutes}分钟内容</title>
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
        
        .header p {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        
        .main-content {{
            display: grid;
            grid-template-columns: 40% 60%;
            gap: 0;
            height: calc(100vh - 120px);
            max-height: calc(100vh - 120px);
        }}
        
        .video-section {{
            padding: 30px;
            background: #f8f9fa;
            border-right: 1px solid #e0e0e0;
            overflow-y: auto;
        }}
        
        .video-wrapper {{
            position: relative;
            padding-bottom: 56.25%; /* 16:9 */
            height: 0;
            overflow: hidden;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            position: sticky;
            top: 30px;
        }}
        
        .video-wrapper iframe {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
        }}
        
        .video-link {{
            margin-top: 20px;
            padding: 15px;
            background: #fff3cd;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
        }}
        
        .video-link p {{
            color: #856404;
            margin-bottom: 10px;
            font-size: 0.9em;
        }}
        
        .youtube-button {{
            display: inline-block;
            padding: 10px 20px;
            background: #ff0000;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin-right: 10px;
            margin-top: 5px;
            font-weight: 600;
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
        
        .video-info {{
            margin-top: 20px;
            padding: 20px;
            background: white;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        
        .video-info h2 {{
            color: #333;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        
        .info-grid {{
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 15px;
        }}
        
        .info-item {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 6px;
        }}
        
        .info-label {{
            font-size: 0.85em;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .info-value {{
            font-size: 1.1em;
            color: #333;
            font-weight: 600;
            margin-top: 5px;
        }}
        
        .transcript-section {{
            padding: 30px;
            background: white;
            overflow-y: auto;
            height: 100%;
            max-height: calc(100vh - 120px);
        }}
        
        .transcript-section::-webkit-scrollbar {{
            width: 10px;
        }}
        
        .transcript-section::-webkit-scrollbar-track {{
            background: #f1f1f1;
            border-radius: 10px;
        }}
        
        .transcript-section::-webkit-scrollbar-thumb {{
            background: #667eea;
            border-radius: 10px;
        }}
        
        .transcript-section::-webkit-scrollbar-thumb:hover {{
            background: #5568d3;
        }}
        
        @media (max-width: 968px) {{
            .main-content {{
                grid-template-columns: 1fr;
                height: auto;
                max-height: none;
            }}
            
            .video-section {{
                height: auto;
                border-right: none;
                border-bottom: 1px solid #e0e0e0;
            }}
            
            .transcript-section {{
                height: auto;
                max-height: none;
            }}
        }}
        
        .transcript-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #667eea;
            position: sticky;
            top: 0;
            background: white;
            z-index: 10;
            padding-top: 10px;
        }}
        
        .transcript-header h2 {{
            color: #333;
            font-size: 1.8em;
        }}
        
        .transcript-stats {{
            background: #667eea;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
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
            transition: all 0.3s ease;
            cursor: pointer;
        }}
        
        .transcript-item:hover {{
            background: #e9ecef;
            transform: translateX(5px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }}
        
        .timestamp {{
            flex-shrink: 0;
            width: 70px;
            font-family: 'Courier New', monospace;
            font-weight: bold;
            color: #667eea;
            font-size: 1em;
        }}
        
        .transcript-text {{
            flex: 1;
            color: #333;
            line-height: 1.6;
        }}
        
        .search-box {{
            margin-bottom: 20px;
            position: sticky;
            top: 80px;
            background: white;
            z-index: 9;
            padding-bottom: 10px;
        }}
        
        .search-box input {{
            width: 100%;
            padding: 15px 50px 15px 20px;
            font-size: 1em;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            transition: border-color 0.3s;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .search-box input:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }}
        
        .search-icon {{
            position: absolute;
            right: 20px;
            top: 50%;
            transform: translateY(-50%);
            color: #999;
        }}
        
        .highlight {{
            background: #ffeb3b;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        
        .footer {{
            background: #2c3e50;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }}
        
        .footer a {{
            color: #667eea;
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎬 YouTube 视频内容展示</h1>
            <p>前 {duration_minutes} 分钟字幕与时间戳</p>
        </div>
        
        <div class="main-content">
            <div class="video-section">
            <div class="video-wrapper">
                <iframe 
                    id="videoPlayer"
                    src="https://www.youtube.com/embed/{video_id}?enablejsapi=1&origin=file://" 
                    frameborder="0" 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
                    allowfullscreen
                    referrerpolicy="strict-origin-when-cross-origin">
                </iframe>
            </div>
            
            <div class="video-link">
                <p>如果视频无法播放，请：</p>
                <a href="https://www.youtube.com/watch?v={video_id}" target="_blank" class="youtube-button">
                    ▶️ 在YouTube上观看
                </a>
                <a href="https://www.youtube.com/embed/{video_id}" target="_blank" class="youtube-button secondary">
                    🔗 在新标签页打开
                </a>
            </div>
            
            <div class="video-info">
                <h2>📹 视频信息</h2>
"""
    
    # 添加视频详情（如果有）
    if video_info:
        html_content += f"""
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">标题</div>
                        <div class="info-value">{video_info.get('title', 'N/A')[:50]}...</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">频道</div>
                        <div class="info-value">{video_info.get('channel_title', 'N/A')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">观看次数</div>
                        <div class="info-value">{int(video_info.get('view_count', 0)):,}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">点赞数</div>
                        <div class="info-value">{int(video_info.get('like_count', 0)):,}</div>
                    </div>
                </div>
"""
    else:
        html_content += f"""
                <p style="color: #666; font-style: italic;">
                    视频ID: {video_id} | 
                    <a href="{video_url}" target="_blank" style="color: #667eea;">在YouTube上观看</a>
                </p>
"""
    
    html_content += """
            </div>
            </div>
            
            <div class="transcript-section">
            <div class="transcript-header">
                <h2>📝 字幕内容</h2>
                <div class="transcript-stats">
"""
    
    html_content += f"                    共 {len(filtered_transcript)} 段字幕\n"
    html_content += """                </div>
            </div>
            
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="🔍 搜索字幕内容..." onkeyup="searchTranscript()">
                <span class="search-icon">🔍</span>
            </div>
            
            <ul class="transcript-list" id="transcriptList">
"""
    
    # 添加字幕条目
    for entry in filtered_transcript:
        timestamp = format_timestamp(entry.start)
        text = entry.text.replace('<', '&lt;').replace('>', '&gt;')  # 转义HTML
        timestamp_seconds = int(entry.start)
        
        html_content += f"""
                <li class="transcript-item" onclick="seekTo({timestamp_seconds})">
                    <span class="timestamp">{timestamp}</span>
                    <span class="transcript-text">{text}</span>
                </li>
"""
    
    html_content += """
            </ul>
            </div>
        </div>
        
        <div class="footer">
            <p>通过 YouTube Data API 和 youtube-transcript-api 生成</p>
            <p>视频来源: <a href="https://www.youtube.com" target="_blank">YouTube</a></p>
        </div>
    </div>
    
    <script>
        // 搜索功能
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
                    
                    // 高亮搜索词
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
        
        // 点击字幕跳转到视频对应时间
        function seekTo(seconds) {
            const iframe = document.querySelector('iframe');
            const currentSrc = iframe.src;
            
            // 检查是否已经包含时间参数
            if (currentSrc.includes('?')) {
                // 移除旧的时间参数并添加新的
                const baseSrc = currentSrc.split('?')[0];
                iframe.src = baseSrc + '?start=' + seconds + '&autoplay=1';
            } else {
                iframe.src = currentSrc + '?start=' + seconds + '&autoplay=1';
            }
        }
        
        // 添加键盘快捷键
        document.addEventListener('keydown', function(e) {
            if (e.key === '/' || e.key === 'f' && e.ctrlKey) {
                e.preventDefault();
                document.getElementById('searchInput').focus();
            }
        });
    </script>
</body>
</html>
"""
    
    # 保存HTML文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✓ HTML页面已生成: {output_file}")
    print(f"✓ 包含 {len(filtered_transcript)} 段字幕")
    print(f"\n在浏览器中打开: file://{output_file}")
    
    return output_file


def main():
    """主函数"""
    # 视频URL
    video_url = "https://www.youtube.com/watch?v=7ARBJQn6QkM"
    
    # 生成HTML页面（前5分钟）
    output_file = generate_html_page(
        video_url=video_url,
        duration_minutes=5,
        output_file="video_first_5min.html"
    )
    
    if output_file:
        print("\n" + "=" * 60)
        print("✅ 成功生成网页！")
        print("=" * 60)
        print(f"\n功能特性：")
        print("  ✓ YouTube视频嵌入播放")
        print("  ✓ 前5分钟字幕展示")
        print("  ✓ 时间戳点击跳转")
        print("  ✓ 字幕内容搜索")
        print("  ✓ 响应式设计")
        print(f"\n打开方式：")
        print(f"  1. 在文件管理器中双击 {output_file}")
        print(f"  2. 或在浏览器中打开该文件")


if __name__ == "__main__":
    main()

