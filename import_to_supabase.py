#!/usr/bin/env python3
"""
将本地YouTube视频数据导入到Supabase数据库
"""

import os
import json
import re
from pathlib import Path
from supabase import create_client, Client

# Supabase配置
SUPABASE_URL = "https://xxurqudxplxhignlshhy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh4dXJxdWR4cGx4aGlnbmxzaGh5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyNDAxMjEsImV4cCI6MjA4MDgxNjEyMX0.afuHUdv5pDwKrMbEon5Tcy2W2EHTR9ZMlka8jiECGDY"

# 数据目录
DATA_DIR = Path(__file__).parent / "data"


def get_supabase_client() -> Client:
    """创建Supabase客户端"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def extract_video_id_from_filename(filename: str) -> str | None:
    """从文件名中提取video_id"""
    # video-data-{video_id}.json
    if filename.startswith("video-data-") and filename.endswith(".json"):
        return filename[11:-5]
    # transcript_{video_id}.txt
    if filename.startswith("transcript_") and filename.endswith(".txt"):
        return filename[11:-4]
    # chapters_{video_id}.json
    if filename.startswith("chapters_") and filename.endswith(".json"):
        return filename[9:-5]
    return None


def load_json_file(filepath: Path) -> dict | None:
    """加载JSON文件"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️  加载JSON失败 {filepath}: {e}")
        return None


def load_text_file(filepath: Path) -> str | None:
    """加载文本文件"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"  ⚠️  加载文本失败 {filepath}: {e}")
        return None


def collect_video_data(data_dir: Path) -> dict:
    """
    收集所有视频数据
    返回: {video_id: {"video_data": ..., "transcript": ..., "chapters": ...}}
    """
    videos = {}
    
    for filepath in data_dir.iterdir():
        if not filepath.is_file():
            continue
            
        filename = filepath.name
        video_id = extract_video_id_from_filename(filename)
        
        if not video_id:
            continue
        
        # 跳过模板文件
        if video_id == "template":
            continue
            
        if video_id not in videos:
            videos[video_id] = {
                "video_data": None,
                "transcript": None,
                "chapters": None
            }
        
        if filename.startswith("video-data-"):
            videos[video_id]["video_data"] = load_json_file(filepath)
        elif filename.startswith("transcript_"):
            videos[video_id]["transcript"] = load_text_file(filepath)
        elif filename.startswith("chapters_"):
            videos[video_id]["chapters"] = load_json_file(filepath)
    
    return videos


def import_to_supabase(videos: dict, client: Client) -> tuple[int, int]:
    """
    导入数据到Supabase
    返回: (成功数, 失败数)
    """
    success_count = 0
    fail_count = 0
    
    for video_id, data in videos.items():
        try:
            record = {
                "video_id": video_id,
                "video_data": data["video_data"],
                "transcript": data["transcript"],
                "chapters": data["chapters"]
            }
            
            # 使用upsert，如果已存在则更新
            result = client.table("youtube_videos").upsert(
                record, 
                on_conflict="video_id"
            ).execute()
            
            print(f"  ✅ {video_id}")
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ {video_id}: {e}")
            fail_count += 1
    
    return success_count, fail_count


def main():
    print("=" * 60)
    print("YouTube视频数据导入工具")
    print("=" * 60)
    print(f"\n📁 数据目录: {DATA_DIR}")
    print(f"🌐 Supabase: {SUPABASE_URL}")
    
    # 收集数据
    print("\n📦 收集本地数据...")
    videos = collect_video_data(DATA_DIR)
    print(f"   找到 {len(videos)} 个视频")
    
    if not videos:
        print("\n⚠️  没有找到任何视频数据！")
        return
    
    # 显示数据概览
    print("\n📊 数据概览:")
    for video_id, data in videos.items():
        has_data = "✓" if data["video_data"] else "✗"
        has_transcript = "✓" if data["transcript"] else "✗"
        has_chapters = "✓" if data["chapters"] else "✗"
        print(f"   {video_id}: video_data={has_data} transcript={has_transcript} chapters={has_chapters}")
    
    # 确认导入
    print(f"\n确认导入 {len(videos)} 个视频到Supabase？")
    response = input("输入 'yes' 继续: ")
    
    if response.lower() != "yes":
        print("已取消")
        return
    
    # 连接并导入
    print("\n🔗 连接Supabase...")
    client = get_supabase_client()
    
    print("\n📤 开始导入...")
    success, fail = import_to_supabase(videos, client)
    
    print("\n" + "=" * 60)
    print(f"导入完成！成功: {success}, 失败: {fail}")
    print("=" * 60)


if __name__ == "__main__":
    main()

