# backend/python/video_frame_extractor.py
import subprocess
import os
from pathlib import Path

def extract_frame_at_timestamp(video_id, timestamp_seconds, output_path=None):
    """
    从 YouTube 视频中提取指定时间戳的帧
    
    Args:
        video_id: YouTube 视频 ID
        timestamp_seconds: 时间戳（秒）
        output_path: 输出路径，如果为 None 则返回 BytesIO
    
    Returns:
        图片文件路径或 BytesIO 对象
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    if output_path is None:
        output_path = f"/tmp/frame_{video_id}_{timestamp_seconds}.jpg"
    
    # 使用 yt-dlp 获取视频流 URL
    # 然后用 ffmpeg 提取指定时间的帧
    cmd = [
        'yt-dlp',
        '--quiet',
        '--no-warnings',
        '--get-url',
        url
    ]
    
    try:
        # 获取视频 URL
        video_url = subprocess.check_output(cmd).decode('utf-8').strip().split('\n')[0]
        
        # 使用 ffmpeg 提取帧
        ffmpeg_cmd = [
            'ffmpeg',
            '-ss', str(timestamp_seconds),  # 跳转到指定时间
            '-i', video_url,
            '-vframes', '1',  # 只提取一帧
            '-q:v', '2',  # 高质量
            '-y',  # 覆盖已存在的文件
            output_path
        ]
        
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True)
        return output_path
        
    except Exception as e:
        raise Exception(f"Failed to extract frame: {str(e)}")

if __name__ == "__main__":
    print("=" * 60)
    print("测试视频帧提取功能")
    print("=" * 60)
    print(f"\n视频 ID: EF8C4v7JIbA")
    print(f"时间戳: 1794 秒 (29分54秒)")
    print(f"\n正在提取视频帧...")
    
    try:
        output_path = extract_frame_at_timestamp("EF8C4v7JIbA", 1794)
        print(f"\n✓ 成功！")
        print(f"图片已保存到: {output_path}")
        
        # 检查文件是否存在
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"文件大小: {file_size / 1024:.2f} KB")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n✗ 失败: {e}")
        import traceback
        traceback.print_exc()