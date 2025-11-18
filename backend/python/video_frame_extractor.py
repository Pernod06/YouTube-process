"""
视频帧提取器 - 从 YouTube 视频中提取指定时间戳的帧
"""

import subprocess
import os
from pathlib import Path
from io import BytesIO


def extract_frame_at_timestamp(video_id, timestamp_seconds, output_path=None):
    """
    从 YouTube 视频中提取指定时间戳的帧
    
    Args:
        video_id: YouTube 视频 ID
        timestamp_seconds: 时间戳（秒）
        output_path: 输出路径，如果为 None 则使用临时路径
    
    Returns:
        图片文件路径
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    if output_path is None:
        # 使用临时目录
        output_path = f"/tmp/frame_{video_id}_{timestamp_seconds}.jpg"
    
    print(f"[INFO] 正在提取视频帧...")
    print(f"[INFO] 视频 ID: {video_id}")
    print(f"[INFO] 时间戳: {timestamp_seconds} 秒")
    
    # 使用 yt-dlp 获取视频流 URL
    cmd = [
        'yt-dlp',
        '--quiet',
        '--no-warnings',
        '--get-url',
        '-f', 'best',  # 获取最佳质量
        url
    ]
    
    try:
        # 获取视频 URL
        print("[INFO] 正在获取视频流 URL...")
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        video_url = result.decode('utf-8').strip().split('\n')[0]
        print(f"[INFO] 视频流 URL 获取成功")
        
        # 使用 ffmpeg 提取帧
        print(f"[INFO] 正在提取第 {timestamp_seconds} 秒的帧...")
        ffmpeg_cmd = [
            'ffmpeg',
            '-ss', str(timestamp_seconds),  # 跳转到指定时间
            '-i', video_url,
            '-vframes', '1',  # 只提取一帧
            '-q:v', '2',  # 高质量 (1-31, 越小越好)
            '-y',  # 覆盖已存在的文件
            output_path
        ]
        
        subprocess.run(
            ffmpeg_cmd,
            check=True,
            capture_output=True,
            timeout=30  # 30秒超时
        )
        
        # 验证文件是否创建
        if not os.path.exists(output_path):
            raise Exception("帧提取失败：输出文件未创建")
        
        file_size = os.path.getsize(output_path)
        print(f"[SUCCESS] 帧提取成功！文件大小: {file_size / 1024:.2f} KB")
        
        return output_path
        
    except subprocess.TimeoutExpired:
        raise Exception("帧提取超时（30秒）")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8') if e.stderr else str(e)
        raise Exception(f"FFmpeg 执行失败: {error_msg}")
    except Exception as e:
        raise Exception(f"帧提取失败: {str(e)}")


def extract_multiple_frames(video_id, timestamps):
    """
    从视频中提取多个时间戳的帧
    
    Args:
        video_id: YouTube 视频 ID
        timestamps: 时间戳列表（秒）
    
    Returns:
        文件路径列表
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


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("测试视频帧提取功能")
    print("=" * 60)
    
    video_id = "EF8C4v7JIbA"
    timestamp = 1794
    
    try:
        output_path = extract_frame_at_timestamp(video_id, timestamp)
        print(f"\n✓ 测试成功！")
        print(f"图片保存到: {output_path}")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()

