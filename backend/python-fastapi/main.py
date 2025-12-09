"""
Python + FastAPI 后端示例
安装依赖: pip install fastapi uvicorn python-multipart
"""

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, Response
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import os
from datetime import datetime
from pathlib import Path
import sys

# Supabase 配置
from supabase import create_client, Client

SUPABASE_URL = "https://xxurqudxplxhignlshhy.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh4dXJxdWR4cGx4aGlnbmxzaGh5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUyNDAxMjEsImV4cCI6MjA4MDgxNjEyMX0.afuHUdv5pDwKrMbEon5Tcy2W2EHTR9ZMlka8jiECGDY"

def get_supabase_client() -> Client:
    """获取 Supabase 客户端"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_cached_video_from_supabase(video_id: str) -> dict | None:
    """从 Supabase 获取缓存的视频数据"""
    try:
        client = get_supabase_client()
        result = client.table("youtube_videos").select("*").eq("video_id", video_id).single().execute()
        if result.data:
            return result.data
        return None
    except Exception as e:
        print(f"[WARN] 从 Supabase 获取缓存失败: {e}")
        return None

def save_video_to_supabase(video_id: str, video_data: dict, transcript: str = None, chapters: list = None):
    """保存视频数据到 Supabase"""
    try:
        client = get_supabase_client()
        record = {
            "video_id": video_id,
            "video_data": video_data,
            "transcript": transcript,
            "chapters": chapters
        }
        client.table("youtube_videos").upsert(record, on_conflict="video_id").execute()
        print(f"[SUCCESS] 视频数据已保存到 Supabase: {video_id}")
    except Exception as e:
        print(f"[WARN] 保存到 Supabase 失败: {e}")

# 添加以下代码来加载 .env 文件
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    print(f"[App] .env 文件已加载")
except ImportError:
    print("[App] python-dotenv 未安装")

# 导入辅助模块
from pdf_generator import generate_video_pdf
from video_frame_extractor import extract_frame_at_timestamp, extract_youtube_chapters, extract_multiple_frames

app = FastAPI(
    title="视频内容平台 API",
    description="动态视频内容管理系统",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置路径
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
STATIC_DIR = BASE_DIR

# 内存存储
comments_db = {}
progress_db = {}


# Pydantic 模型
class Comment(BaseModel):
    comment: str
    author: Optional[str] = "Anonymous"


class CommentResponse(BaseModel):
    id: str
    author: str
    text: str
    timestamp: str


class Progress(BaseModel):
    timestamp: float


class ProgressResponse(BaseModel):
    timestamp: float
    updatedAt: str


class SearchResult(BaseModel):
    videoId: str
    title: str
    thumbnail: str
    url: str


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int


class ChatRequest(BaseModel):
    message: str
    video_context: Optional[Dict[str, Any]] = None


class VideoFramesRequest(BaseModel):
    timestamps: List[int]


class ProcessVideoRequest(BaseModel):
    url: str
    language: str = "en"  # 默认英语，支持: zh, en, ja, ko, es, fr, de, pt, ru, ar


def load_video_data():
    """加载视频数据"""
    data_path = DATA_DIR / 'video-data.json'
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@app.get("/api/videos/{video_id}")
async def get_video(video_id: str, language: str = None):
    """获取视频数据，支持翻译为目标语言"""
    try:
        # 从 Supabase 获取视频数据
        cached_record = get_cached_video_from_supabase(video_id)
        
        if not cached_record or not cached_record.get('video_data'):
            raise HTTPException(status_code=404, detail=f"视频数据不存在: {video_id}")
        
        video_data = cached_record['video_data']
        
        # 如果指定了非英文语言，翻译数据
        if language and language != 'en':
            print(f"[INFO] 翻译视频数据为 {language}...")
            video_data = translate_cached_data(video_data, language)
        
        return video_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/transcript/{video_id}")
async def get_transcript(video_id: str):
    """获取视频字幕"""
    try:
        # 从 Supabase 获取字幕
        cached_record = get_cached_video_from_supabase(video_id)
        
        if not cached_record or not cached_record.get('transcript'):
            raise HTTPException(status_code=404, detail=f"字幕不存在: {video_id}")
        
        content = cached_record['transcript']
        return Response(content=content, media_type="text/plain; charset=utf-8")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取字幕失败: {str(e)}")


@app.get("/api/videos")
async def get_videos():
    """获取视频列表（从 Supabase）"""
    try:
        client = get_supabase_client()
        result = client.table("youtube_videos").select("video_id, video_data, created_at").order("created_at", desc=True).execute()
        
        videos = []
        for record in result.data:
            video_data = record.get('video_data', {})
            video_info = video_data.get('videoInfo', {})
            videos.append({
                "videoId": record['video_id'],
                "title": video_info.get('title', f"Video {record['video_id']}"),
                "description": video_info.get('description', ''),
                "thumbnail": video_info.get('thumbnail', f"https://img.youtube.com/vi/{record['video_id']}/maxresdefault.jpg"),
                "summary": video_info.get('summary', ''),
                "createdAt": record.get('created_at', '')
            })
        return videos
    except Exception as e:
        print(f"[ERROR] 获取视频列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/videos/{video_id}/comments")
async def get_comments(video_id: str, maxResults: Optional[int] = Query(20)):
    """获取YouTube评论"""
    try:
        # 尝试导入 youtube_client
        import traceback
        sys.path.append(str(BASE_DIR))
        
        print(f"[INFO] 正在获取视频 {video_id} 的评论...")
        
        from youtube_client import YouTubeClient
        
        # 创建 YouTube 客户端
        print("[INFO] 正在初始化 YouTube 客户端...")
        client = YouTubeClient()
        
        # 获取评论数量参数（默认20条）
        max_results = min(maxResults, 30)  # 限制最大100条
        
        print(f"[INFO] 正在调用 YouTube API 获取 {max_results} 条评论...")
        # 调用 YouTube API 获取评论
        print(f"[INFO] 视频ID: {video_id}")
        comments = client.get_video_comments(video_id, max_results=max_results)
        
        if comments:
            print(f"[SUCCESS] 成功获取 {len(comments)} 条评论")
            print(comments)
            return {
                'success': True,
                'videoId': video_id,
                'comments': comments,
                'total': len(comments)
            }
            
        else:
            # 如果获取失败，返回空列表
            print("[WARNING] 未获取到评论")
            return {
                'success': True,
                'videoId': video_id,
                'comments': [],
                'total': 0,
                'message': '该视频没有评论或评论已关闭'
            }
    except ImportError as e:
        # 如果无法导入 youtube_client，返回模拟数据
        print(f"[ERROR] 导入错误: {str(e)}")
        traceback.print_exc()
        return {
            'success': False,
            'videoId': video_id,
            'comments': [],
            'total': 0,
            'error': str(e),
            'message': 'YouTube API 客户端导入失败'
        }
    except ValueError as e:
        # YouTube API 密钥未配置
        print(f"[ERROR] 配置错误: {str(e)}")
        return {
            'success': False,
            'videoId': video_id,
            'comments': [],
            'total': 0,
            'error': str(e),
            'message': 'YouTube API 密钥未配置或无效，请检查 config.py'
        }
    except Exception as e:
        print(f"[ERROR] 未知错误: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                'success': False,
                'videoId': video_id,
                'error': str(e),
                'error_type': type(e).__name__,
                'message': '获取评论失败，请查看后端日志'
            }
        )


@app.post("/api/videos/{video_id}/comments", response_model=CommentResponse, status_code=201)
async def post_comment(video_id: str, comment_data: Comment):
    """发布评论"""
    if video_id not in comments_db:
        comments_db[video_id] = []
    
    new_comment = {
        "id": str(int(datetime.now().timestamp() * 1000)),
        "author": comment_data.author,
        "text": comment_data.comment,
        "timestamp": datetime.now().isoformat()
    }
    
    comments_db[video_id].append(new_comment)
    return new_comment


@app.get("/api/videos/{video_id}/progress")
async def get_progress(video_id: str):
    """获取播放进度"""
    user_progress = progress_db.get(video_id, {'timestamp': 0})
    return user_progress


@app.put("/api/videos/{video_id}/progress")
async def update_progress(video_id: str, progress_data: Progress):
    """更新播放进度"""
    progress_db[video_id] = {
        "timestamp": progress_data.timestamp,
        "updatedAt": datetime.now().isoformat()
    }
    
    return {
        "success": True,
        "progress": progress_db[video_id]
    }


@app.get("/api/search", response_model=SearchResponse)
async def search(
    query: str = Query(..., description="搜索关键词"), 
    limit: int = Query(10, description="返回结果数量限制"),
    order: str = Query("viewCount", description="排序方式: relevance, date, viewCount, rating, title"),
    duration: str = Query("long", description="视频时长: any, short(<4min), medium(4-20min), long(>20min)"),
    time_filter: Optional[str] = Query(None, description="时间过滤: hour, today, week, month, year")
):
    """通过 YouTube API 搜索视频"""
    try:
        print(f"[INFO] 搜索 YouTube: {query}, limit={limit}, order={order}, duration={duration}, time_filter={time_filter}")
        
        # 导入 YouTubeClient
        sys.path.append(str(BASE_DIR))
        from youtube_client import YouTubeClient
        
        # 创建客户端并搜索
        client = YouTubeClient()
        youtube_results = client.search_videos(query, max_results=limit, order=order, 
                                               published_after=time_filter, duration=duration)
        
        # 转换为前端期望的格式
        results = []
        for video in youtube_results:
            video_id = video.get('video_id', '')
            thumbnails = video.get('thumbnails', {})
            thumbnail = thumbnails.get('high') or thumbnails.get('medium') or thumbnails.get('default') or f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg'
            
            results.append({
                "videoId": video_id,
                "title": video.get('title', ''),
                "thumbnail": thumbnail,
                "url": f"https://www.youtube.com/watch?v={video_id}"
            })
        
        print(f"[SUCCESS] 找到 {len(results)} 个视频")
        
        return {
            "results": results,
            "total": len(results)
        }
    except ValueError as e:
        # YouTube API 密钥未配置
        print(f"[ERROR] YouTube API 配置错误: {e}")
        raise HTTPException(status_code=500, detail=f"YouTube API 配置错误: {str(e)}")
    except Exception as e:
        print(f"[ERROR] 搜索失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


@app.post("/api/chat")
async def chat(chat_request: ChatRequest):
    """
    LLM 聊天接口
    """
    user_message = chat_request.message
    video_context = chat_request.video_context

    print(f"Video context: {video_context}", flush=True)

    try:
        # 调用 OpenAI API 进行聊天
        response = chat_with_openai(user_message, video_context)

        return {
            'success': True,
            'response': response,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                'error': str(e),
                'response': 'sorry, please try again later.'
            }
        )


@app.get("/api/generate-pdf/{video_id}")
async def generate_pdf(video_id: str):
    """
    生成视频数据的 PDF 文档
    
    Args:
        video_id: YouTube 视频 ID
    """
    try:
        print(f'[INFO] 开始生成 PDF for video {video_id}...')
        
        # 加载视频数据
        data_path = DATA_DIR / f'video-data-{video_id}.json'
        
        if not data_path.exists():
            raise HTTPException(
                status_code=404,
                detail={
                    'success': False,
                    'error': 'Video data not found',
                    'message': f'视频数据文件不存在: video-data-{video_id}.json'
                }
            )
        
        with open(data_path, 'r', encoding='utf-8') as f:
            video_data = json.load(f)
        
        # 生成 PDF（在内存中）
        pdf_buffer = generate_video_pdf(video_data, output_path=None)
        
        # 生成文件名
        video_title = video_data.get('videoInfo', {}).get('title', 'video')
        # 清理文件名中的特殊字符（只保留 ASCII 字符）
        safe_title = "".join(c for c in video_title if c.isascii() and (c.isalnum() or c in (' ', '-', '_'))).strip()
        safe_title = safe_title[:50] if safe_title else video_id  # 如果为空则使用 video_id
        filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # 对文件名进行 URL 编码以支持特殊字符
        from urllib.parse import quote
        encoded_filename = quote(filename)
        
        print(f'[SUCCESS] PDF 生成成功: {filename}')
        
        # 读取 buffer 内容
        pdf_content = pdf_buffer.getvalue()
        
        # 使用 Response 而不是 StreamingResponse，确保完整传输
        # 使用 RFC 5987 格式支持 UTF-8 文件名
        return Response(
            content=pdf_content,
            media_type='application/pdf',
            headers={
                'Content-Disposition': f"attachment; filename=\"{video_id}.pdf\"; filename*=UTF-8''{encoded_filename}",
                'Content-Length': str(len(pdf_content))
            }
        )
        
    except Exception as e:
        print(f'[ERROR] PDF 生成失败: {str(e)}')
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                'success': False,
                'error': str(e),
                'message': 'PDF 生成失败'
            }
        )


@app.get("/api/video-frame/{video_id}")
async def get_video_frame(video_id: str, timestamp: int = Query(0)):
    """
    获取视频指定时间戳的帧图片
    
    Query Parameters:
        - timestamp: 时间戳（秒），默认为 0
    
    Example:
        GET /api/video-frame/EF8C4v7JIbA?timestamp=1794
    """
    try:
        print(f"[INFO] 收到帧提取请求 - 视频ID: {video_id}, 时间戳: {timestamp}")
        
        # 提取帧
        frame_path = extract_frame_at_timestamp(video_id, timestamp)
        
        # 返回图片文件
        return FileResponse(
            frame_path,
            media_type='image/jpeg',
            filename=f"frame_{video_id}_{timestamp}.jpg"
        )
        
    except Exception as e:
        print(f"[ERROR] 帧提取失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail={
                'success': False,
                'error': str(e),
                'message': '无法提取视频帧'
            }
        )


@app.get("/api/video-info/{video_id}")
async def get_video_info(video_id: str):
    """获取 YouTube 视频信息（标题、描述等）"""
    try:
        print(f"[INFO] 获取视频信息 - 视频ID: {video_id}")
        
        sys.path.append(str(BASE_DIR))
        from youtube_get_video_information import get_video_information
        
        # 获取视频信息
        video_info = get_video_information(video_id)
        
        if not video_info:
            raise HTTPException(status_code=404, detail={'success': False, 'message': '无法获取视频信息'})
        
        print(f"[SUCCESS] 视频信息获取成功")
        
        return {
            'success': True,
            'videoId': video_id,
            'title': video_info.get('title', ''),
            'description': video_info.get('description', ''),
            'channelTitle': video_info.get('channel_title', ''),
            'publishedAt': video_info.get('published_at', ''),
            'duration': video_info.get('duration', ''),
            'viewCount': video_info.get('view_count', 0),
            'likeCount': video_info.get('like_count', 0),
            'thumbnail': video_info.get('thumbnails', {}).get('maxres', '')
        }
        
    except Exception as e:
        print(f"[ERROR] 获取视频信息失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail={'success': False, 'error': str(e)})


@app.get("/api/video-chapters/{video_id}")
async def get_video_chapters(video_id: str):
    """获取视频章节列表（直接调用现有函数）"""
    try:
        video_title, chapters = extract_youtube_chapters(video_id)
        
        if not chapters:
            raise HTTPException(status_code=404, detail={'success': False, 'message': '未找到章节'})
        
        return {'success': True, 'chapters': chapters, 'total': len(chapters)}
    except Exception as e:
        raise HTTPException(status_code=500, detail={'success': False, 'error': str(e)})


@app.post("/api/video-frames/{video_id}")
async def get_video_frames_batch(video_id: str, request: VideoFramesRequest):
    """
    批量获取视频多个时间戳的帧图片
    
    Request Body:
        {
            "timestamps": [10, 30, 60, 120, 180]  // 时间戳数组（秒）
        }
    
    Response:
        {
            "success": true,
            "videoId": "xxx",
            "frames": [
                {
                    "timestamp": 10,
                    "success": true,
                    "url": "/api/video-frame/xxx?timestamp=10"
                },
                ...
            ]
        }
    
    Example:
        POST /api/video-frames/EF8C4v7JIbA
        Body: {"timestamps": [10, 30, 60]}
    """
    timestamps = request.timestamps
    
    try:
        print(f"[INFO] 收到批量帧提取请求 - 视频ID: {video_id}, 时间戳数量: {len(timestamps)}")
        
        # 提取多个帧
        results = extract_multiple_frames(video_id, timestamps)
        
        # 转换结果格式，添加 URL
        frames = []
        for result in results:
            if result['success']:
                frames.append({
                    'timestamp': result['timestamp'],
                    'success': True,
                    'url': f"/api/video-frame/{video_id}?timestamp={result['timestamp']}"
                })
            else:
                frames.append({
                    'timestamp': result['timestamp'],
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                })
        
        success_count = sum(1 for f in frames if f['success'])
        print(f"[SUCCESS] 批量帧提取完成 - 成功: {success_count}/{len(timestamps)}")
        
        return {
            'success': True,
            'videoId': video_id,
            'frames': frames,
            'total': len(frames),
            'successCount': success_count
        }
        
    except Exception as e:
        print(f"[ERROR] 批量帧提取失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail={
                'success': False,
                'error': str(e),
                'message': '批量提取视频帧失败'
            }
        )



def chat_with_openai(user_message, video_context):
    """
    使用 Gemini API 进行聊天（不需要代理，可直连）
    """
    from google import genai
    
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY 未配置，请在 .env 文件中设置")
    
    client = genai.Client(api_key=gemini_api_key)
    
    system_prompt = """You are a video assistant PageOn-Video assistant, helping users understand and find video content.
Your key abilities are:
1. **deep Analysis**: Provide accurate and detailed response based on the complete video transcript and chapter information.
2. **Timestamp**: Mark precise timestamps for relevant content within your answers to facilitate user navigation.
3. **Contextual Understanding**: Comprehend the overall structure of the video to provide valuable insights.

Response Format Requirements:
1. Use the [Timestamp] format to cite key information points. For example:
-[05:30] mention a key concept
-[12:45] demonstrated a specific case
-[1:08:20] summarized the core viewpoints

2. If the user's inquiry involves multiple relevant sections, list all corresponding timestamps:
Example:
"This topic is mentioned multiple times in the video:
-[05:30] Introduced the concept for the first time
-[15:20] Explained the principle in depth
-[28:40] Showed practical application"

3. Provide concise yet informative responses, highlighting key takeaways.

4. If the video does not contain relevant content, explicitly inform the user.

5. Adopt a friendly and professional tone, acting as a knowledgeable guide who understands the full scope of the video"""
    
    # 构建完整提示
    full_prompt = system_prompt
    
    if video_context:
        full_prompt += f"\n\nVideo information: {json.dumps(video_context, ensure_ascii=False)}"
    
    full_prompt += f"\n\nUser question: {user_message}"
    
    # 调用 Gemini API
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[full_prompt]
    )
    
    return response.text


@app.post('/api/process-video')
async def process_video(request_data: ProcessVideoRequest):
    """
    处理前端传来的 YouTube 视频 URL：
    - 提取视频 ID
    - 首先检查 data 目录是否有缓存数据，有则直接返回
    - 无缓存则通过 get_full_transcript 获取完整字幕和视频信息
    - 将字幕写入 data/transcript_{video_id}.txt
    - 返回基本处理状态给前端
    """
    url = request_data.url
    language = request_data.language

    if not url:
        raise HTTPException(status_code=400, detail='URL is required')

    try:
        print(f"[INFO] 开始处理视频: {url}")

        import sys
        import json
        sys.path.append(str(BASE_DIR))

        from get_full_transcript_ytdlp import get_full_transcript, display_full_transcript
        from youtube_client import YouTubeClient

        # 提取视频 ID
        video_id = YouTubeClient.extract_video_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail='无法从URL提取视频ID')

        # 从 Supabase 检查是否有缓存数据
        cached_record = get_cached_video_from_supabase(video_id)
        if cached_record and cached_record.get('video_data'):
            print(f"[INFO] 从 Supabase 发现缓存数据: {video_id}")
            try:
                cached_data = cached_record['video_data']
                
                # 翻译缓存数据为目标语言
                if language and language != 'en':
                    print(f"[INFO] 正在将缓存数据翻译为 {language}...")
                    cached_data = translate_cached_data(cached_data, language)
                
                # 获取缓存中的视频标题
                video_title = cached_data.get('videoInfo', {}).get('title', '')
                
                print(f"[SUCCESS] 使用 Supabase 缓存数据返回，视频标题: {video_title}")
                return {
                    'success': True,
                    'videoId': video_id,
                    'title': video_title,
                    'transcriptLength': len(cached_record.get('transcript', '') or ''),
                    'dataFile': f"video-data-{video_id}.json",
                    'chapters': cached_data.get('chapters', []),
                    'sections': cached_data.get('sections', []),
                    'videoInfo': cached_data.get('videoInfo', {}),
                    'message': '视频处理成功（使用 Supabase 缓存数据）',
                    'cached': True
                }
            except Exception as cache_error:
                print(f"[WARN] 读取 Supabase 缓存数据失败: {cache_error}，将重新生成")

        # print(f"[INFO] 提取到视频 ID: {video_id}")

        # 获取完整字幕与视频详情（注意传入的是完整 URL）
        result = get_full_transcript(url, language='en')
        if not result or result == (None, None):
            raise HTTPException(status_code=500, detail='无法获取视频字幕')

        transcript, details = result
        
        # 再次检查解包后的值
        if not transcript or not details:
            raise HTTPException(status_code=500, detail='无法获取视频字幕或详情')

        # 使用 LLM 处理和结构化字幕
        try:
            print(f"[INFO] 开始使用 LLM 处理字幕...")
            video_data_json = chat_with_gemini(transcript, details, video_id, language)
            print(f"[INFO] 生成的 JSON language: {language}")
            
            # 获取章节缩略图和视频标题
            video_title = ''
            try:
                print(f"[INFO] 正在获取章节缩略图...")
                video_title, chapters = extract_youtube_chapters(video_id)
                
                # 使用正确的视频标题更新 JSON
                if video_title:
                    video_data_json['videoInfo']['title'] = video_title
                    print(f"[SUCCESS] 更新视频标题: {video_title}")
                
                if chapters:
                    # 将章节缩略图添加到 JSON 数据中
                    video_data_json['chapters'] = chapters
                    print(f"[SUCCESS] 获取到 {len(chapters)} 个章节缩略图")
                else:
                    video_data_json['chapters'] = []
                    print(f"[INFO] 该视频没有章节信息")
            except Exception as chapter_error:
                print(f"[WARN] 获取章节缩略图失败: {chapter_error}")
                video_data_json['chapters'] = []
                video_title = details.get('title', '') if details else ''
            
            # 使用 display_full_transcript 获取格式化的字幕
            from get_full_transcript_ytdlp import display_full_transcript
            
            output_lines = display_full_transcript(transcript, details=details)
            
            # 组装完整文本（标题 + 分隔线 + 内容）
            video_title = video_data_json.get('videoInfo', {}).get('title', f'Video {video_id}')
            transcript_text = f"{video_title}\n{'=' * 70}\n\n" + '\n'.join(output_lines)
            
            # 保存到 Supabase
            save_video_to_supabase(
                video_id=video_id,
                video_data=video_data_json,
                transcript=transcript_text,
                chapters=video_data_json.get('chapters', [])
            )
            
            
            # 如果目标语言不是英文，翻译数据后返回
            response_data = video_data_json
            if language and language != 'en':
                print(f"[INFO] 正在将生成的数据翻译为 {language}...")
                response_data = translate_cached_data(video_data_json, language)
            
            return {
                'success': True,
                'videoId': video_id,
                'title': response_data.get('videoInfo', {}).get('title', video_title),
                'transcriptLength': len(transcript),
                'dataFile': f"video-data-{video_id}.json",
                'chapters': response_data.get('chapters', []),
                'sections': response_data.get('sections', []),
                'videoInfo': response_data.get('videoInfo', {}),
                'message': '视频处理成功',
                'cached': False
            }
        except Exception as llm_error:
            print(f"[WARN] LLM 处理失败: {llm_error}, 返回基本信息")
            # LLM 失败时仍返回成功，但不包含结构化数据
            return {
                'success': True,
                'videoId': video_id,
                'title': details.get('title', '') if details else '',
                'transcriptLength': len(transcript) if transcript else 0,
                'message': '视频处理成功（未使用 LLM 结构化）',
                'warning': str(llm_error)
            }

    except Exception as e:
        import traceback
        print(f"[ERROR] /api/process-video 处理失败: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f'视频处理失败: {str(e)}')




def translate_cached_data(cached_data: dict, target_language_code: str) -> dict:
    """
    使用 Gemini API 将缓存的视频数据翻译为目标语言
    """
    import json
    import re
    from google import genai

    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY 未配置，请在 .env 文件中设置")

    client = genai.Client(api_key=gemini_api_key)

    # 语言映射
    language_names = {
        "zh": "Chinese (简体中文)",
        "en": "English",
        "ja": "Japanese (日本語)",
        "ko": "Korean (한국어)",
        "es": "Spanish (Español)",
        "fr": "French (Français)",
        "de": "German (Deutsch)",
        "pt": "Portuguese (Português)",
        "ru": "Russian (Русский)",
        "ar": "Arabic (العربية)",
    }
    target_language = language_names.get(target_language_code, "English")

    # 提取需要翻译的文本内容
    video_info = cached_data.get('videoInfo', {})
    sections = cached_data.get('sections', [])
    
    # 构建翻译提示
    translation_prompt = f"""
You are a professional translator. Translate the following video content JSON to {target_language}.

IMPORTANT RULES:
1. Translate ONLY the text content fields (title, description, summary, content)
2. DO NOT translate or modify: videoId, thumbnail, id, timestampStart, timestamp, thumbnail_url
3. Keep the exact same JSON structure
4. Output valid JSON only, no markdown code blocks

Original JSON:
{json.dumps(cached_data, ensure_ascii=False, indent=2)}

OUTPUT: Return the translated JSON with the same structure, all text in {target_language}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[translation_prompt],
        )
        
        response_text = response.text.strip()
        
        # 移除可能的 markdown 代码块标记
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'^```\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        
        # 提取纯 JSON
        start_idx = response_text.find('{')
        if start_idx != -1:
            brace_count = 0
            end_idx = start_idx
            for i, char in enumerate(response_text[start_idx:], start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            response_text = response_text[start_idx:end_idx]
        
        translated_data = json.loads(response_text)
        print(f"[SUCCESS] 缓存数据已翻译为 {target_language}")
        return translated_data
        
    except Exception as e:
        print(f"[WARN] 翻译缓存数据失败: {e}，返回原始数据")
        return cached_data


def chat_with_gemini(transcript, details, video_id, language):
    """
    使用Gemini API 将视频字幕转换为结构化 JSON
    """
    import os
    import json
    import re
    from google import genai

    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY 未配置，请在 .env 文件中设置")

    client = genai.Client(api_key=gemini_api_key)


    # 时间戳转换函数
    def seconds_to_timestamp(seconds):
        """将秒数转换为时间戳格式 HH:MM:SS"""
        try:
            total_seconds = int(float(seconds))
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            secs = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        except:
            return "00:00:00"
    
    # 准备字幕文本（时间戳转换为 MM:SS 或 HH:MM:SS 格式）
    transcript_text = "\n".join([f"[{seconds_to_timestamp(item['start'])}] {item['text']}" for item in transcript])
    
    # 构建 prompt，避免 f-string 嵌套问题
    title = details.get('title', 'Unknown')
    
    def sample_transcript(transcript_text, max_chars=15000, num_segments=10):
      """
      按行均匀采样文本：保持完整的 [时间戳] 文字 格式
      """
      lines = transcript_text.strip().split('\n')
      total_lines = len(lines)
      
      # 如果总字符数不超过限制，返回完整文本
      if len(transcript_text) <= max_chars:
        return transcript_text
      
      # 计算每个片段应该包含的行数
      lines_per_segment = max(1, total_lines // num_segments)
      chars_per_segment = max_chars // num_segments
      
      sampled_parts = []
      for i in range(num_segments):
        # 计算每个片段的起始行（均匀分布）
        if num_segments > 1:
          start_line = i * (total_lines - lines_per_segment) // (num_segments - 1)
        else:
          start_line = 0
        
        # 收集该片段的完整行，直到达到字符限制
        segment_lines = []
        segment_chars = 0
        for j in range(start_line, min(start_line + lines_per_segment * 2, total_lines)):
          line = lines[j]
          if segment_chars + len(line) > chars_per_segment and segment_lines:
            break
          segment_lines.append(line)
          segment_chars += len(line) + 1  # +1 for newline
        
        if segment_lines:
          sampled_parts.append('\n'.join(segment_lines))

      separator = "\n\n[...]\n\n"
      return separator.join(sampled_parts)
      
      
      
    transcript_preview = sample_transcript(transcript_text, max_chars=15000, num_segments=10)
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    
    # 语言映射
    language_names = {
        "zh": "Chinese (简体中文)",
        "en": "English",
        "ja": "Japanese (日本語)",
        "ko": "Korean (한국어)",
        "es": "Spanish (Español)",
        "fr": "French (Français)",
        "de": "German (Deutsch)",
        "pt": "Portuguese (Português)",
        "ru": "Russian (Русский)",
        "ar": "Arabic (العربية)",
    }
    target_language = language_names.get(language, "English")
    
    system_prompt = """
You are an expert video content analyst. Your task is to deeply analyze this YouTube video transcript and extract the most valuable insights, creating a well-structured summary.

**SUMMARIZE, DON'T TRANSCRIBE**: Extract insights, arguments, and conclusions - NOT word-for-word transcript**

Video Title: """ + title + """
Video ID: """ + video_id + """

Transcript (format: [HH:MM:SS] text):
""" + transcript_preview + """

Generate JSON with this structure:
{
  "videoInfo": {
    "title": "Video Title",
    "videoId": \"""" + video_id + """\",
    "description": "Brief topic description",
    "thumbnail": \"""" + thumbnail_url + """\",
    "summary": "2-3 sentence summary"
  },
  "sections": [
    {
      "id": "section1",
      "title": "Section Title",
      "content": [
        {"content": "Key point (1-2 sentences)", "timestampStart": "00:00:00"}
      ]
    }
  ]
}

REQUIREMENTS:
- **MUST cover the ENTIRE video from beginning to end**
- Create sections based on natural topic changes in the video
- Each content item: 1-2 concise sentences (focus on key insights)
- **timestampStart format: "HH:MM:SS" (e.g., "00:05:30", "01:23:45")**
- **COPY timestamps EXACTLY from the transcript [HH:MM:SS] - DO NOT invent timestamps**

OUTPUT: Valid JSON only, no markdown code blocks or extra text
"""

    try:
        # 生成内容
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[system_prompt],
        )
        
        # 提取响应文本
        response_text = response.text.strip()
        
        # 移除可能的 markdown 代码块标记
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'^```\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        
        # 提取纯 JSON（处理 LLM 在 JSON 后面添加额外文字的情况）
        # 找到第一个 { 和最后一个匹配的 }
        start_idx = response_text.find('{')
        if start_idx != -1:
            # 使用括号匹配找到完整的 JSON 对象
            brace_count = 0
            end_idx = start_idx
            for i, char in enumerate(response_text[start_idx:], start_idx):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            response_text = response_text[start_idx:end_idx]
        
        # 解析 JSON
        video_data_json = json.loads(response_text)
        
        print(f"[SUCCESS] LLM 成功生成结构化数据，包含 {len(video_data_json.get('sections', []))} 个章节")
        return video_data_json
        
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析失败: {e}")
        print(f"[DEBUG] 原始响应: {response_text[:500]}")
        raise ValueError(f"LLM 返回的不是有效的 JSON: {str(e)}")
    except Exception as e:
        print(f"[ERROR] Gemini API 调用失败: {e}")
        raise

# 提供静态文件
@app.get("/")
async def root():
    """返回首页"""
    index_path = STATIC_DIR / "index.html"
    return FileResponse(index_path)


# 挂载静态文件目录
app.mount("/css", StaticFiles(directory=str(STATIC_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(STATIC_DIR / "js")), name="js")
app.mount("/data", StaticFiles(directory=str(STATIC_DIR / "data")), name="data")


if __name__ == "__main__":
    import uvicorn
    print("🚀 Server is running on http://localhost:5000")
    print("📊 API endpoint: http://localhost:5000/api")
    print("📚 API docs: http://localhost:5000/docs")
    print("🌐 Frontend: http://localhost:5000")
    uvicorn.run(app, host="0.0.0.0", port=5000)
