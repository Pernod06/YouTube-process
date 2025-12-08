"""
视频帧提取器 - 从 YouTube 获取章节缩略图（快速版本）
"""

import requests
import re
import json
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs


def extract_youtube_chapters(video_id):
    """
    从 YouTube 页面提取章节信息和缩略图 URL
    
    Args:
        video_id: YouTube 视频 ID
    
    Returns:
        tuple: (video_title, chapters)
            - video_title: 视频标题
            - chapters: 章节列表，每个章节包含 timestamp、title、thumbnail_url
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    print(f"[INFO] 正在获取视频页面: {video_id}")
    try:
        # 设置 User-Agent 避免被识别为爬虫
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html = response.text
        
        # 提取 ytInitialData
        print("[INFO] 正在解析视频数据...")
        data_match = re.search(r'var ytInitialData = ({.*?});', html, re.DOTALL)
        
        if not data_match:
            print("[WARNING] 未找到 ytInitialData，尝试备用方法...")
            return extract_chapters_fallback(video_id)
        
        data = json.loads(data_match.group(1))

        # 寻找title
        video_title = ''
        try:
            contents = data['contents']['twoColumnWatchNextResults']['results']['results']['contents']
            for content in contents:
                if 'videoPrimaryInfoRenderer' in content:
                    title_runs = content['videoPrimaryInfoRenderer']['title']['runs']
                    video_title = ''.join(run['text'] for run in title_runs)
                    break
        except (KeyError, TypeError):
            # 备用方法：从 HTML title 标签提取
            title_match = re.search(r'<title>(.+?) - YouTube</title>', html)
            if title_match:
                video_title = title_match.group(1)
        
        # 寻找章节数据
        chapters = []
        
        # 路径1: 尝试从 playerOverlays 获取
        try:
            player_overlays = data['playerOverlays']['playerOverlayRenderer']
            decorated_bar = player_overlays['decoratedPlayerBarRenderer']['decoratedPlayerBarRenderer']
            player_bar = decorated_bar['playerBar']['multiMarkersPlayerBarRenderer']
            
            markers_map = player_bar.get('markersMap', [])
            
            for marker_group in markers_map:
                if 'value' in marker_group and 'chapters' in marker_group['value']:
                    chapter_list = marker_group['value']['chapters']
                    
                    for chapter in chapter_list:
                        chapter_renderer = chapter.get('chapterRenderer', {})
                        
                        # 获取时间戳
                        time_ms = chapter_renderer.get('timeRangeStartMillis', 0)
                        timestamp = int(time_ms) // 1000
                        
                        # 获取标题
                        title_runs = chapter_renderer.get('title', {}).get('simpleText', '')
                        
                        # 获取缩略图
                        thumbnails = chapter_renderer.get('thumbnail', {}).get('thumbnails', [])
                        thumbnail_url = thumbnails[-1]['url'] if thumbnails else None
                        
                        chapters.append({
                            'timestamp': timestamp,
                            'title': title_runs,
                            'thumbnail_url': thumbnail_url
                        })
                    
                    print(f"[SUCCESS] 找到 {len(chapters)} 个章节, 标题: {video_title}")
                    return (video_title, chapters)
        except (KeyError, TypeError) as e:
            print(f"[WARNING] 主路径解析失败: {e}")
        
        # 路径2: 尝试从 engagementPanels 获取（某些视频）
        try:
            panels = data.get('engagementPanels', [])
            for panel in panels:
                panel_renderer = panel.get('engagementPanelSectionListRenderer', {})
                content = panel_renderer.get('content', {})
                
                macro_markers = content.get('macroMarkersListRenderer', {})
                if macro_markers:
                    contents = macro_markers.get('contents', [])
                    
                    for item in contents:
                        marker = item.get('macroMarkersListItemRenderer', {})
                        time_description = marker.get('timeDescription', {}).get('simpleText', '0:00')
                        
                        # 解析时间
                        timestamp = parse_timestamp(time_description)
                        
                        title = marker.get('title', {}).get('simpleText', '')
                        thumbnails = marker.get('thumbnail', {}).get('thumbnails', [])
                        thumbnail_url = thumbnails[-1]['url'] if thumbnails else None
                        
                        chapters.append({
                            'timestamp': timestamp,
                            'title': title,
                            'thumbnail_url': thumbnail_url
                        })
                    
                    if chapters:
                        print(f"[SUCCESS] 找到 {len(chapters)} 个章节（备用路径）, 标题: {video_title}")
                        return (video_title, chapters)
        except (KeyError, TypeError) as e:
            print(f"[WARNING] 备用路径解析失败: {e}")
        
        # 如果没找到章节，返回空列表
        print(f"[WARNING] 未找到章节信息, 标题: {video_title}")
        return (video_title, [])
        
    except requests.RequestException as e:
        print(f"[ERROR] 请求失败: {e}")
        return ('', [])
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析失败: {e}")
        return ('', [])
    except Exception as e:
        print(f"[ERROR] 未知错误: {e}")
        return ('', [])


def parse_timestamp(time_str):
    """
    解析时间字符串为秒数
    例如: "1:30" -> 90, "1:23:45" -> 5025
    """
    parts = time_str.split(':')
    parts = [int(p) for p in parts]
    
    if len(parts) == 2:  # MM:SS
        return parts[0] * 60 + parts[1]
    elif len(parts) == 3:  # HH:MM:SS
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    else:
        return 0


def extract_chapters_fallback(video_id):
    """
    备用方法：使用 yt-dlp 提取章节信息和视频标题
    
    Returns:
        tuple: (video_title, chapters)
    """
    import subprocess
    
    print("[INFO] 使用 yt-dlp 备用方法...")
    
    try:
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--skip-download',
            f"https://www.youtube.com/watch?v={video_id}"
        ]
        
        result = subprocess.check_output(cmd, stderr=subprocess.PIPE, timeout=15)
        data = json.loads(result.decode('utf-8'))
        
        # 获取视频标题
        video_title = data.get('title', '')
        
        chapters = []
        if 'chapters' in data and data['chapters']:
            for chapter in data['chapters']:
                chapters.append({
                    'timestamp': int(chapter.get('start_time', 0)),
                    'title': chapter.get('title', ''),
                    'thumbnail_url': None  # yt-dlp 不提供章节缩略图
                })
        
        print(f"[SUCCESS] yt-dlp 获取标题: {video_title}, 章节数: {len(chapters)}")
        return (video_title, chapters)
        
    except Exception as e:
        print(f"[ERROR] yt-dlp 备用方法失败: {e}")
        return ('', [])


def download_thumbnail(thumbnail_url, output_path):
    """
    下载缩略图到本地
    
    Args:
        thumbnail_url: 缩略图 URL
        output_path: 输出路径
    
    Returns:
        str: 保存的文件路径
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(thumbnail_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        return output_path
        
    except Exception as e:
        raise Exception(f"缩略图下载失败: {e}")


def extract_frame_at_timestamp(video_id, timestamp_seconds, output_path=None):
    """
    快速提取指定时间戳的帧（使用 YouTube 章节缩略图）
    
    Args:
        video_id: YouTube 视频 ID
        timestamp_seconds: 时间戳（秒）
        output_path: 输出路径
    
    Returns:
        str: 图片文件路径
    """
    if output_path is None:
        output_path = f"/tmp/frame_{video_id}_{timestamp_seconds}.jpg"
    
    print(f"[INFO] 正在提取视频帧（快速模式）...")
    print(f"[INFO] 视频 ID: {video_id}, 时间戳: {timestamp_seconds} 秒")
    
    # 获取所有章节
    chapters = extract_youtube_chapters(video_id)
    
    if not chapters:
        print("[WARNING] 未找到章节，回退到传统方法...")
        return extract_frame_traditional(video_id, timestamp_seconds, output_path)
    
    # 找到最接近的章节
    closest_chapter = None
    min_diff = float('inf')
    
    for chapter in chapters:
        diff = abs(chapter['timestamp'] - timestamp_seconds)
        if diff < min_diff:
            min_diff = diff
            closest_chapter = chapter
    
    if closest_chapter and closest_chapter['thumbnail_url']:
        print(f"[INFO] 找到匹配章节: {closest_chapter['title']} (误差 {min_diff} 秒)")
        
        try:
            # 下载缩略图
            download_thumbnail(closest_chapter['thumbnail_url'], output_path)
            print(f"[SUCCESS] 缩略图下载成功")
            return output_path
        except Exception as e:
            print(f"[ERROR] {e}")
            return extract_frame_traditional(video_id, timestamp_seconds, output_path)
    else:
        print("[WARNING] 未找到匹配章节，回退到传统方法...")
        return extract_frame_traditional(video_id, timestamp_seconds, output_path)


def extract_frame_traditional(video_id, timestamp_seconds, output_path):
    """
    传统方法：使用 yt-dlp + ffmpeg 提取帧（原有方法）
    """
    import subprocess
    
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    print("[INFO] 使用传统方法（yt-dlp + ffmpeg）...")
    
    cmd = [
        'yt-dlp',
        '--quiet',
        '--no-warnings',
        '--get-url',
        '-f', 'best',
        url
    ]
    
    try:
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=30)
        video_url = result.decode('utf-8').strip().split('\n')[0]
        
        ffmpeg_cmd = [
            'ffmpeg',
            '-ss', str(timestamp_seconds),
            '-i', video_url,
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            output_path
        ]
        
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, timeout=30)
        
        if not os.path.exists(output_path):
            raise Exception("帧提取失败")
        
        print(f"[SUCCESS] 传统方法提取成功")
        return output_path
        
    except Exception as e:
        raise Exception(f"传统方法失败: {e}")


def extract_multiple_frames(video_id, timestamps):
    """
    批量提取多个时间戳的帧
    """
    results = []
    
    for timestamp in timestamps:
        try:
            path = extract_frame_at_timestamp(video_id, timestamp)
            results.append({
                'timestamp': timestamp,
                'path': path,
                'success': True
            })
        except Exception as e:
            results.append({
                'timestamp': timestamp,
                'error': str(e),
                'success': False
            })
    
    return results


# 保存章节列表到文件
def save_chapters(video_id, video_title, chapters, output_dir=None):
    """
    保存章节列表到 JSON 文件
    
    Args:
        video_id: YouTube 视频 ID
        video_title: 视频标题
        chapters: 章节列表 [{timestamp, title, thumbnail_url}, ...]
        output_dir: 输出目录，默认为 data 目录
    
    Returns:
        保存的文件路径
    """
    import json
    
    if output_dir is None:
        output_dir = Path(__file__).parent.parent.parent / 'data'
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"chapters_{video_id}.json"
    
    data = {
        'video_id': video_id,
        'video_title': video_title,
        'chapters': chapters
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"[SUCCESS] 章节列表已保存: {output_file}")
    return str(output_file)


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("测试快速视频帧提取功能")
    print("=" * 60)
    
    video_id = "DxL2HoqLbyA"
    
    # 测试章节提取
    video_title, chapters = extract_youtube_chapters(video_id)
    print(f"\n视频标题: {video_title}")
    print(f"找到 {len(chapters)} 个章节:")
    for ch in chapters:
        print(f"  - {ch['timestamp']}s: {ch['title']}")
    
    # 保存章节列表
    if chapters:
        save_chapters(video_id, video_title, chapters)
    
    # 测试单帧提取
    # if chapters:
    #     timestamp = chapters[0]['timestamp']
    #     output_path = extract_frame_at_timestamp(video_id, timestamp)
    #     print(f"\n✓ 测试成功！")
    #     print(f"图片保存到: {output_path}")