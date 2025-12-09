import subprocess
import os

def extract_youtube_frame(video_id, timestamp_seconds, output_path):
    """
    从 YouTube 视频提取指定时间戳的帧
    
    Args:
        video_id: YouTube 视频 ID (如 'dQw4w9WgXcQ')
        timestamp_seconds: 时间戳（秒）
        output_path: 输出图片路径
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # 步骤1: 获取视频流 URL
    cmd_get_url = [
        'yt-dlp',
        '--js-runtimes', 'node',
        '-f', 'best',
        '--get-url',
        url
    ]
    
    try:
        result = subprocess.check_output(cmd_get_url, stderr=subprocess.DEVNULL)
        stream_url = result.decode('utf-8').strip().split('\n')[0]
        
        # 步骤2: 使用 FFmpeg 提取帧
        cmd_ffmpeg = [
            'ffmpeg',
            '-ss', str(timestamp_seconds),  # 快速定位
            '-i', stream_url,
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            output_path
        ]
        
        subprocess.run(cmd_ffmpeg, check=True, capture_output=True)
        
        if os.path.exists(output_path):
            print(f"✅ 帧提取成功: {output_path}")
            return output_path
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 提取失败: {e}")
        return None

# 使用示例
extract_youtube_frame("HTa1uc_kmHQ", 30, "/tmp/frame_30s.jpg")