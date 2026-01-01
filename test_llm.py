#!/usr/bin/env python3
"""
测试 LLM analyze_video_transcript 函数
使用真实的 transcript 文件作为输入
"""
import asyncio
import json
import os
import sys
import re

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 添加路径
sys.path.insert(0, '/home/ubuntu/YouTube-process/backend/python-fastapi')

from llm_server import get_llm_service, StructuredArticleV2


def parse_transcript_file(filepath: str) -> tuple[list, dict, str]:
    """
    解析 transcript txt 文件
    
    Returns:
        transcript: List[dict] - [{"start": seconds, "text": "..."}, ...]
        details: dict - {"title": "...", "description": "..."}
        video_id: str
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.strip().split('\n')
    
    # 第一行是标题
    title = lines[0].strip() if lines else "Unknown Title"
    
    # 从文件名提取 video_id
    filename = os.path.basename(filepath)
    video_id_match = re.search(r'transcript_([A-Za-z0-9_-]+)\.txt', filename)
    video_id = video_id_match.group(1) if video_id_match else "unknown"
    
    # 解析带时间戳的行
    # 格式: [MM:SS] text 或 [HH:MM:SS] text
    timestamp_pattern = re.compile(r'\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]\s*[-–]?\s*(.*)')
    
    transcript = []
    for line in lines[2:]:  # 跳过标题和分隔线
        match = timestamp_pattern.match(line.strip())
        if match:
            if match.group(3):  # HH:MM:SS 格式
                hours = int(match.group(1))
                minutes = int(match.group(2))
                seconds = int(match.group(3))
            else:  # MM:SS 格式
                hours = 0
                minutes = int(match.group(1))
                seconds = int(match.group(2))
            
            total_seconds = hours * 3600 + minutes * 60 + seconds
            text = match.group(4).strip()
            
            if text:  # 只添加有文本的行
                transcript.append({
                    "start": total_seconds,
                    "text": text
                })
    
    details = {
        "title": title,
        "description": f"Transcript from video {video_id}",
    }
    
    return transcript, details, video_id


# 使用真实的 transcript 文件
TRANSCRIPT_FILE = "/home/ubuntu/PageOn_video_web/src/data/transcript/transcript_DxL2HoqLbyA.txt"

# 解析文件
REAL_TRANSCRIPT, REAL_DETAILS, VIDEO_ID = parse_transcript_file(TRANSCRIPT_FILE)


async def test_stream():
    """测试流式版本"""
    print("=" * 60)
    print("测试 analyze_video_transcript_stream")
    print("=" * 60)
    print(f"📁 Transcript 文件: {TRANSCRIPT_FILE}")
    print(f"📹 Video ID: {VIDEO_ID}")
    print(f"📝 标题: {REAL_DETAILS['title']}")
    print(f"📊 总行数: {len(REAL_TRANSCRIPT)}")
    print("=" * 60)
    
    llm_service = get_llm_service()
    
    full_response = ""
    async for chunk in llm_service.analyze_video_transcript_stream(
        transcript=REAL_TRANSCRIPT,
        details=REAL_DETAILS,
        video_id=VIDEO_ID,
    ):
        print(f"[CHUNK] {chunk[:100]}..." if len(chunk) > 100 else f"[CHUNK] {chunk}")
        full_response += chunk
    
    # 清理响应 - 移除 markdown 代码块和流结束标记
    clean_response = full_response.replace("[STREAM_END]", "").strip()
    # 移除 markdown 代码块
    if clean_response.startswith("```"):
        clean_response = re.sub(r'^```json?\s*', '', clean_response)
        clean_response = re.sub(r'\s*```$', '', clean_response)
        clean_response = clean_response.strip()
    
    print("\n" + "=" * 60)
    print("完整响应 (JSON):")
    print("=" * 60)
    
    try:
        parsed = json.loads(clean_response)
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
        
        print("\n" + "=" * 60)
        print("V2.0 响应结构分析:")
        print("=" * 60)
        print(f"顶层字段: {list(parsed.keys())}")
        
        # V2.0 结构分析
        if "meta" in parsed:
            meta = parsed['meta']
            print(f"\n📋 Meta:")
            print(f"  标题: {meta.get('title')}")
            print(f"  标签: {meta.get('tags')}")
            print(f"  阅读时间: {meta.get('reading_time')}")
            print(f"  难度: {meta.get('difficulty')}")
        
        if "header_hook" in parsed:
            hook = parsed['header_hook']
            print(f"\n💡 Header Hook:")
            print(f"  引言: {hook.get('quote', '')[:80]}...")
        
        if "summary_box" in parsed:
            summary = parsed['summary_box']
            print(f"\n📦 Summary Box:")
            print(f"  核心洞察: {summary.get('key_insight', '')[:80]}...")
            print(f"  要点数量: {len(summary.get('bullet_points', []))}")
        
        if "background_cards" in parsed:
            cards = parsed['background_cards']
            print(f"\n🎴 Background Cards: {len(cards)} 张")
            for card in cards[:3]:
                print(f"  - {card.get('icon_hint', '')} {card.get('name')} ({card.get('type')})")
        
        if "main_body" in parsed:
            sections = parsed['main_body']
            print(f"\n📖 Main Body: {len(sections)} 个章节")
            for i, sec in enumerate(sections):
                print(f"  {i+1}. [{sec.get('timestamp_ref')}] {sec.get('section_title')}")
        
        if "deep_analysis" in parsed:
            deep = parsed['deep_analysis']
            print(f"\n🔬 Deep Analysis:")
            print(f"  Mermaid 图表: {len(deep.get('mermaid_graph', ''))} 字符")
            print(f"  深度论点: {len(deep.get('deep_points', []))} 个")
        
        if "qa_interactions" in parsed:
            qa = parsed['qa_interactions']
            print(f"\n❓ Q&A: {len(qa)} 对")
            for q in qa[:2]:
                print(f"  Q: {q.get('question', '')[:50]}...")
        
        if "footer" in parsed:
            footer = parsed['footer']
            print(f"\n📎 Footer:")
            print(f"  资源: {len(footer.get('resources', []))} 个")
            print(f"  下一步: {len(footer.get('actionable_next_steps', []))} 条")
            
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
        print("原始响应前2000字符:")
        print(clean_response[:2000])


def test_sync():
    """测试同步版本"""
    print("=" * 60)
    print("测试 analyze_video_transcript (同步)")
    print("=" * 60)
    
    llm_service = get_llm_service()
    
    result = llm_service.analyze_video_transcript(
        transcript=REAL_TRANSCRIPT,
        details=REAL_DETAILS,
        video_id=VIDEO_ID,
    )
    
    print("\n" + "=" * 60)
    print("返回结果类型:", type(result))
    print("=" * 60)
    
    # 转换为 dict
    result_dict = result.model_dump()
    print(json.dumps(result_dict, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    print("\n🧪 LLM 函数测试开始\n")
    
    # 测试流式版本
    asyncio.run(test_stream())
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

