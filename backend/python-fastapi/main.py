"""
Python + FastAPI 后端示例
安装依赖: pip install fastapi uvicorn python-multipart
"""

import logging
from logging.handlers import RotatingFileHandler
import os as _os
from pathlib import Path as _Path

# ========== 日志配置 ==========
# 自动检测运行环境：Docker 使用 /app/logs，本地使用项目目录下的 logs
if _os.path.exists("/app"):
    LOG_DIR = "/app/logs"
else:
    LOG_DIR = str(_Path(__file__).parent.parent.parent / "logs")
_os.makedirs(LOG_DIR, exist_ok=True)

# 文件日志处理器
_file_handler = RotatingFileHandler(
    f"{LOG_DIR}/app.log",
    maxBytes=50*1024*1024,  # 50MB
    backupCount=5,
    encoding='utf-8'
)
_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

# 控制台日志处理器
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))

# 配置根日志
logging.basicConfig(
    level=logging.INFO,
    handlers=[_file_handler, _console_handler]
)

logger = logging.getLogger(__name__)
logger.info("=== 应用启动，日志系统初始化完成 ===")
# ==============================

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

def record_user_usage(user_id: str, video_id: str, video_title: str = None, action_type: str = "analysis"):
    """记录用户使用分析功能"""
    if not user_id:
        print(f"[Usage] 匿名用户，跳过使用记录")
        return False
    
    try:
        client = get_supabase_client()
        record = {
            "user_id": user_id,
            "video_id": video_id,
            "video_title": video_title,
            "action_type": action_type
        }
        client.table("user_usage").insert(record).execute()
        print(f"[Usage] ✅ 已记录用户 {user_id[:8]}... 分析视频: {video_id}")
        return True
    except Exception as e:
        print(f"[Usage] ⚠️ 记录使用失败: {e}")
        return False

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

# 导入 LangChain LLM 服务
from llm_server import get_llm_service

# 导入 YouTube 搜索服务 (SerpAPI)
from youtube_search_service import (
    get_youtube_search_service,
    SearchYouTubeParams,
    YouTubeSearchError
)

# 导入 Chat 路由
from chat import router as chat_router

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

# 注册 Chat 路由
app.include_router(chat_router)

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
    duration: Optional[str] = None  # 格式化时长 (如 "1:02:03")
    channel: Optional[str] = None  # 频道名称
    views: Optional[int] = None  # 观看次数
    publishedDate: Optional[str] = None  # 发布日期


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int


class GenerateThemesRequest(BaseModel):
    video_id: str
    stream: bool = False  # 是否使用流式输出


class VideoFramesRequest(BaseModel):
    timestamps: List[int]


class ProcessVideoRequest(BaseModel):
    url: str
    language: str = "en"  # 默认英语，支持: zh, en, ja, ko, es, fr, de, pt, ru, ar
    user_id: Optional[str] = None  # 用户ID（可选，用于记录使用次数）


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
            
            # 格式化发布日期
            published_at = video.get('published_at', '')
            published_date = None
            if published_at:
                try:
                    from datetime import datetime
                    pub_dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    now = datetime.now(pub_dt.tzinfo)
                    diff = now - pub_dt
                    if diff.days == 0:
                        published_date = "Today"
                    elif diff.days == 1:
                        published_date = "Yesterday"
                    elif diff.days < 7:
                        published_date = f"{diff.days} days ago"
                    elif diff.days < 30:
                        weeks = diff.days // 7
                        published_date = f"{weeks} week{'s' if weeks > 1 else ''} ago"
                    elif diff.days < 365:
                        months = diff.days // 30
                        published_date = f"{months} month{'s' if months > 1 else ''} ago"
                    else:
                        years = diff.days // 365
                        published_date = f"{years} year{'s' if years > 1 else ''} ago"
                except:
                    published_date = published_at[:10] if published_at else None
            
            results.append({
                "videoId": video_id,
                "title": video.get('title', ''),
                "thumbnail": thumbnail,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "duration": video.get('duration_formatted', ''),  # 格式化时长
                "channel": video.get('channel_title', ''),  # 频道名称
                "views": video.get('view_count', 0),  # 观看次数
                "publishedDate": published_date  # 格式化发布日期
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


# ==================== SerpAPI YouTube 搜索 ====================

class SerpAPISearchRequest(BaseModel):
    """SerpAPI YouTube 搜索请求模型"""
    search_query: str
    gl: Optional[str] = None  # 国家/地区代码 (如 "us", "cn")
    hl: Optional[str] = None  # 语言代码 (如 "en", "zh-CN")
    duration: Optional[str] = None  # 视频时长: any, short(<20min), medium(20min-1hour), long(>1hour)
    limit: Optional[int] = None  # 返回结果数量限制


class SerpAPIVideoResult(BaseModel):
    """SerpAPI 视频结果模型"""
    position: Optional[int] = None
    title: str
    videoId: str
    link: str
    thumbnail: Optional[str] = None
    channel: Optional[str] = None
    channelLink: Optional[str] = None
    publishedDate: Optional[str] = None
    views: Optional[int] = None
    length: Optional[str] = None
    description: Optional[str] = None


class SerpAPISearchResponse(BaseModel):
    """SerpAPI 搜索响应模型"""
    success: bool
    results: List[SerpAPIVideoResult]
    total: int
    cached: bool = False


@app.post("/api/search-youtube", response_model=SerpAPISearchResponse)
async def search_youtube_serpapi(request: SerpAPISearchRequest):
    """
    使用 SerpAPI 搜索 YouTube 视频
    
    与 NestJS 版本 SearchYouTubeService 功能一致:
    - 支持 search_query 搜索关键词
    - 10分钟缓存机制
    - 返回 video_results 列表
    
    Request Body:
        {
            "search_query": "搜索关键词",
            "gl": "us",  // 可选，国家/地区代码
            "hl": "en"   // 可选，语言代码
        }
    
    Response:
        {
            "success": true,
            "results": [...],
            "total": 10,
            "cached": false
        }
    """
    try:
        print(f"[INFO] SerpAPI YouTube 搜索: {request.search_query}, duration={request.duration}, limit={request.limit}")
        
        # 获取搜索服务
        service = get_youtube_search_service()
        
        # 构建搜索参数
        params = SearchYouTubeParams(
            search_query=request.search_query,
            engine="youtube",
            gl=request.gl,
            hl=request.hl,
            duration=request.duration,
            limit=request.limit
        )
        
        # 执行搜索
        response = await service.search_youtube(params)
        
        # 转换为前端友好的格式
        results = []
        for video in response.video_results:
            # 提取视频 ID（从链接中）
            video_id = ""
            link = video.get('link', '')
            if 'watch?v=' in link:
                video_id = link.split('watch?v=')[1].split('&')[0]
            
            # 提取缩略图
            thumbnail = ""
            thumb_data = video.get('thumbnail', {})
            if isinstance(thumb_data, dict):
                thumbnail = thumb_data.get('static', '') or thumb_data.get('rich', '')
            elif isinstance(thumb_data, str):
                thumbnail = thumb_data
            
            # 提取频道信息
            channel_data = video.get('channel', {})
            channel_name = ""
            channel_link = ""
            if isinstance(channel_data, dict):
                channel_name = channel_data.get('name', '')
                channel_link = channel_data.get('link', '')
            elif isinstance(channel_data, str):
                channel_name = channel_data
            
            results.append(SerpAPIVideoResult(
                position=video.get('position'),
                title=video.get('title', ''),
                videoId=video_id,
                link=link,
                thumbnail=thumbnail,
                channel=channel_name,
                channelLink=channel_link,
                publishedDate=video.get('published_date'),
                views=video.get('views'),
                length=video.get('length'),
                description=video.get('description')
            ))
        
        print(f"[SUCCESS] SerpAPI 搜索成功，找到 {len(results)} 个视频")
        
        return SerpAPISearchResponse(
            success=True,
            results=results,
            total=len(results),
            cached=False  # 缓存状态由服务内部处理
        )
        
    except YouTubeSearchError as e:
        print(f"[ERROR] SerpAPI 搜索失败: {e.message}")
        raise HTTPException(
            status_code=500,
            detail={
                'success': False,
                'error': e.message,
                'message': 'YouTube 搜索失败'
            }
        )
    except Exception as e:
        print(f"[ERROR] SerpAPI 搜索异常: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={
                'success': False,
                'error': str(e),
                'message': 'YouTube 搜索失败'
            }
        )


@app.get("/api/search-youtube/cache-stats")
async def get_youtube_search_cache_stats():
    """获取 YouTube 搜索缓存统计信息"""
    service = get_youtube_search_service()
    return {
        'success': True,
        'stats': service.get_cache_stats()
    }


@app.delete("/api/search-youtube/cache")
async def clear_youtube_search_cache():
    """清空 YouTube 搜索缓存"""
    service = get_youtube_search_service()
    service.clear_cache()
    return {
        'success': True,
        'message': '缓存已清空'
    }


# Chat 路由已迁移到 chat.py


@app.post("/api/generate-themes/{video_id}")
async def generate_themes(
    video_id: str, 
    stream: bool = Query(False, description="是否使用流式输出"),
    language: str = Query("en", description="输出语言: en, zh, ja, ko, es, fr, de")
):
    """
    根据视频分析数据生成 2-5 个主题
    
    Args:
        video_id: YouTube 视频 ID
        stream: 是否使用流式输出（默认 False）
        language: 输出语言代码（默认英语）
    
    Returns:
        - 非流式：直接返回完整的主题 JSON
        - 流式：返回 SSE 流
    """
    try:
        print(f"[INFO] 生成主题 - 视频ID: {video_id}, stream: {stream}, language: {language}")
        
        # 从 Supabase 获取视频数据
        cached_record = get_cached_video_from_supabase(video_id)
        
        if not cached_record or not cached_record.get('video_data'):
            raise HTTPException(
                status_code=404,
                detail={'success': False, 'error': 'Video data not found', 'message': f'视频数据不存在: {video_id}'}
            )
        
        video_data = cached_record['video_data']
        
        if not video_data.get('sections'):
            raise HTTPException(
                status_code=400,
                detail={'success': False, 'error': 'No sections found', 'message': '视频数据中没有章节信息'}
            )
        
        llm_service = get_llm_service()
        
        if stream:
            # 流式输出
            async def generate_stream():
                try:
                    full_response = ""
                    async for chunk in llm_service.generate_themes_stream(video_data, language):
                        if chunk == "\n[STREAM_END]":
                            continue
                        full_response += chunk
                        yield f"data: {chunk}\n\n"
                    
                    # 解析最终结果
                    try:
                        theme_result = llm_service.parse_themes_result(full_response)
                        yield f'data: [DONE] {json.dumps(theme_result.model_dump(), ensure_ascii=False)}\n\n'
                    except Exception as parse_error:
                        print(f"[WARN] 主题解析失败: {parse_error}")
                        yield f'data: [DONE] {full_response}\n\n'
                        
                except Exception as e:
                    print(f"[ERROR] 流式生成主题失败: {e}")
                    yield f'data: [ERROR] {str(e)}\n\n'
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        else:
            # 非流式输出
            theme_result = llm_service.generate_themes(video_data, language)
            
            print(f"[SUCCESS] 生成了 {len(theme_result.themes)} 个主题")
            
            return {
                'success': True,
                'videoId': video_id,
                'themes': theme_result.model_dump()['themes'],
                'total': len(theme_result.themes)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 生成主题失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail={'success': False, 'error': str(e), 'message': '生成主题失败'}
        )


@app.post("/api/generate-themes")
async def generate_themes_from_json(request: Request):
    """
    根据传入的视频 JSON 数据直接生成主题（无需视频ID）
    
    Request Body:
        {
            "video_data": { ... 视频分析 JSON ... },
            "stream": false
        }
    """
    try:
        body = await request.json()
        video_data = body.get('video_data')
        stream = body.get('stream', False)
        
        if not video_data:
            raise HTTPException(status_code=400, detail={'success': False, 'message': '缺少 video_data'})
        
        if not video_data.get('sections'):
            raise HTTPException(status_code=400, detail={'success': False, 'message': '视频数据中没有 sections'})
        
        print(f"[INFO] 从 JSON 生成主题, sections 数量: {len(video_data.get('sections', []))}")
        
        llm_service = get_llm_service()
        
        if stream:
            async def generate_stream():
                try:
                    full_response = ""
                    async for chunk in llm_service.generate_themes_stream(video_data):
                        if chunk == "\n[STREAM_END]":
                            continue
                        full_response += chunk
                        yield f"data: {chunk}\n\n"
                    
                    try:
                        theme_result = llm_service.parse_themes_result(full_response)
                        yield f'data: [DONE] {json.dumps(theme_result.model_dump(), ensure_ascii=False)}\n\n'
                    except:
                        yield f'data: [DONE] {full_response}\n\n'
                except Exception as e:
                    yield f'data: [ERROR] {str(e)}\n\n'
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
            )
        else:
            theme_result = llm_service.generate_themes(video_data)
            return {
                'success': True,
                'themes': theme_result.model_dump()['themes'],
                'total': len(theme_result.themes)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] 生成主题失败: {e}")
        raise HTTPException(status_code=500, detail={'success': False, 'error': str(e)})


class PDFExportRequest(BaseModel):
    notes: list = []
    videoTitle: str = ""

@app.post("/api/generate-pdf/{video_id}")
async def generate_pdf_post(video_id: str, request: PDFExportRequest = None):
    """
    生成视频数据的 PDF 文档（支持包含笔记）
    
    Args:
        video_id: YouTube 视频 ID
        request: 可选的请求体，包含 notes 和 videoTitle
    """
    return await _generate_pdf_internal(video_id, request)

@app.get("/api/generate-pdf/{video_id}")
async def generate_pdf(video_id: str):
    """
    生成视频数据的 PDF 文档（GET 方式，向后兼容）
    
    Args:
        video_id: YouTube 视频 ID
    """
    return await _generate_pdf_internal(video_id, None)

async def _generate_pdf_internal(video_id: str, request: PDFExportRequest = None):
    """
    内部 PDF 生成函数
    """
    try:
        print(f'[INFO] 开始生成 PDF for video {video_id}...')
        
        # 从 Supabase 获取视频数据
        cached_record = get_cached_video_from_supabase(video_id)
        
        if not cached_record or not cached_record.get('video_data'):
            raise HTTPException(
                status_code=404,
                detail={
                    'success': False,
                    'error': 'Video data not found',
                    'message': f'视频数据不存在: {video_id}'
                }
            )
        
        video_data = cached_record['video_data']
        
        # 提取笔记数据
        notes = request.notes if request else []
        
        # 生成 PDF（在内存中），传入笔记
        pdf_buffer = generate_video_pdf(video_data, output_path=None, notes=notes)
        
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

        # 使用 LangChain LLM 服务处理和结构化字幕
        try:
            print(f"[INFO] 开始使用 LangChain 处理字幕...")
            llm_service = get_llm_service()
            video_analysis = llm_service.analyze_video_transcript(transcript, details, video_id)
            video_data_json = video_analysis.model_dump()
            print(f"[INFO] LangChain 生成结构化数据，language: {language}")
            
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


@app.post('/api/process-video/stream')
async def process_video_stream(request_data: ProcessVideoRequest):
    """
    流式处理 YouTube 视频 URL - 直接输出 LLM 生成的内容
    
    返回 Server-Sent Events (SSE) 格式：
    - 直接发送 LLM 生成的文本片段（无前缀）
    - data: [DONE] 完整JSON结果
    - data: [CACHED] 缓存的完整JSON结果  
    - data: [ERROR] 错误消息
    """
    import time
    url = request_data.url
    language = request_data.language
    user_id = request_data.user_id  # 可选：用于记录使用次数
    
    print(f"[STREAM] 📥 收到请求: url={url}, language={language}, user_id={user_id[:8] + '...' if user_id else 'anonymous'}", flush=True)

    async def generate():
        try:
            sys.path.append(str(BASE_DIR))
            from get_full_transcript_ytdlp import get_full_transcript, display_full_transcript
            from youtube_client import YouTubeClient

            # 提取视频 ID
            video_id = YouTubeClient.extract_video_id(url)
            print(f"[STREAM] 🎬 视频ID: {video_id}", flush=True)
            if not video_id:
                print(f"[STREAM] ❌ 无法提取视频ID", flush=True)
                yield 'data: [ERROR] 无法从URL提取视频ID\n\n'
                return

            # 检查缓存
            print(f"[STREAM] 🔍 检查缓存...", flush=True)
            cached_record = get_cached_video_from_supabase(video_id)
            if cached_record and cached_record.get('video_data'):
                print(f"[STREAM] ✅ 命中缓存，直接返回", flush=True)
                cached_data = cached_record['video_data']
                if language and language != 'en':
                    cached_data = translate_cached_data(cached_data, language)
                yield f'data: [CACHED] {json.dumps(cached_data, ensure_ascii=False)}\n\n'
                return

            # 获取字幕
            print(f"[STREAM] 📝 开始获取字幕...", flush=True)
            start_time = time.time()
            result = get_full_transcript(url, language='en')
            print(f"[STREAM] 📝 字幕获取完成，耗时: {time.time() - start_time:.2f}s", flush=True)
            
            if not result or result == (None, None):
                print(f"[STREAM] ❌ 无法获取字幕", flush=True)
                yield 'data: [ERROR] 无法获取视频字幕\n\n'
                return

            transcript, details = result
            if not transcript or not details:
                print(f"[STREAM] ❌ 字幕或详情为空", flush=True)
                yield 'data: [ERROR] 字幕或详情为空\n\n'
                return
            
            print(f"[STREAM] 📝 字幕条数: {len(transcript)}", flush=True)

            # 流式 LLM 分析 - 使用分段事件流
            print(f"[STREAM] 🤖 开始 LLM 流式分析...", flush=True)
            llm_start = time.time()
            llm_service = get_llm_service()
            full_response = ""
            chunk_count = 0
            
            # 增量解析状态
            video_info_sent = False
            sent_section_ids = set()
            
            def send_event(event_type: str, data: dict):
                """发送结构化事件"""
                event = {"type": event_type, "data": data}
                return f'data: {json.dumps(event, ensure_ascii=False)}\n\n'
            
            def try_parse_video_info(content: str):
                """尝试从累积内容中解析 videoInfo"""
                import re
                # 清理 markdown
                text = re.sub(r'^```json?\s*', '', content.strip())
                
                # 查找 videoInfo 对象
                match = re.search(r'"videoInfo"\s*:\s*(\{)', text)
                if not match:
                    return None
                
                start = match.end() - 1  # { 的位置
                depth = 0
                for i in range(start, len(text)):
                    if text[i] == '{':
                        depth += 1
                    elif text[i] == '}':
                        depth -= 1
                        if depth == 0:
                            try:
                                return json.loads(text[start:i+1])
                            except:
                                return None
                return None
            
            def try_parse_sections(content: str, seen_ids: set):
                """尝试从累积内容中解析新的 sections"""
                import re
                text = re.sub(r'^```json?\s*', '', content.strip())
                
                # 查找 sections 数组
                match = re.search(r'"sections"\s*:\s*\[', text)
                if not match:
                    return []
                
                start = match.end()
                new_sections = []
                
                # 查找每个 section 对象
                i = start
                while i < len(text):
                    # 跳过空白和逗号
                    while i < len(text) and text[i] in ' \t\n\r,':
                        i += 1
                    if i >= len(text) or text[i] == ']':
                        break
                    if text[i] != '{':
                        i += 1
                        continue
                    
                    # 找到对象开始，寻找闭合
                    obj_start = i
                    depth = 0
                    for j in range(i, len(text)):
                        if text[j] == '{':
                            depth += 1
                        elif text[j] == '}':
                            depth -= 1
                            if depth == 0:
                                try:
                                    section = json.loads(text[obj_start:j+1])
                                    if section.get('id') and section['id'] not in seen_ids:
                                        new_sections.append(section)
                                        seen_ids.add(section['id'])
                                except:
                                    pass
                                i = j + 1
                                break
                    else:
                        break  # 对象未闭合，等待更多数据
                
                return new_sections
            
            async for chunk in llm_service.analyze_video_transcript_stream(transcript, details, video_id):
                if chunk == "\n[STREAM_END]":
                    continue
                full_response += chunk
                chunk_count += 1
                
                # 尝试增量解析并发送事件
                if not video_info_sent:
                    video_info = try_parse_video_info(full_response)
                    if video_info:
                        print(f"[STREAM] 📤 发送 video_info 事件", flush=True)
                        yield send_event("video_info", video_info)
                        video_info_sent = True
                
                # 尝试解析新的 sections
                new_sections = try_parse_sections(full_response, sent_section_ids)
                for section in new_sections:
                    print(f"[STREAM] 📤 发送 section 事件: {section.get('id')}", flush=True)
                    yield send_event("section", section)
                
                if chunk_count % 20 == 0:
                    print(f"[STREAM] 🔄 chunk#{chunk_count}, 长度:{len(full_response)}", flush=True)
            
            print(f"[STREAM] 🤖 LLM 流式输出完成，耗时: {time.time() - llm_start:.2f}s, 总chunks: {chunk_count}", flush=True)

            # === 解析完整结果 ===
            print(f"[STREAM] 📊 解析完整 JSON...", flush=True)
            try:
                video_analysis = llm_service.parse_analysis_result(full_response)
                video_data_json = video_analysis.model_dump()
                print(f"[STREAM] ✅ JSON 解析成功，sections: {len(video_data_json.get('sections', []))}", flush=True)
            except Exception as parse_error:
                print(f"[STREAM] ⚠️ JSON 解析失败，使用原始响应: {parse_error}", flush=True)
                try:
                    import re
                    text = re.sub(r'^```json?\s*', '', full_response.strip())
                    text = re.sub(r'\s*```$', '', text)
                    video_data_json = json.loads(text)
                except:
                    video_data_json = {"videoInfo": {"title": details.get('title', ''), "videoId": video_id}, "sections": []}

            # 获取章节
            try:
                video_title, chapters = extract_youtube_chapters(video_id)
                if video_title:
                    video_data_json['videoInfo']['title'] = video_title
                video_data_json['chapters'] = chapters or []
            except:
                video_data_json['chapters'] = []

            # 发送完整的 JSON 给前端（与 [CACHED] 格式保持一致）
            yield f'data: [DONE] {json.dumps(video_data_json, ensure_ascii=False)}\n\n'
            print(f"[STREAM] 📤 已发送 [DONE] 完整 JSON", flush=True)

            # 保存到 Supabase（后台处理，不阻塞前端）
            print(f"[STREAM] 💾 保存到 Supabase...", flush=True)
            output_lines = display_full_transcript(transcript, details=details)
            video_title = video_data_json.get('videoInfo', {}).get('title', f'Video {video_id}')
            transcript_text = f"{video_title}\n{'=' * 70}\n\n" + '\n'.join(output_lines)
            
            save_video_to_supabase(
                video_id=video_id,
                video_data=video_data_json,
                transcript=transcript_text,
                chapters=video_data_json.get('chapters', [])
            )
            
            # 记录用户使用（如果有 user_id）
            if user_id:
                record_user_usage(
                    user_id=user_id,
                    video_id=video_id,
                    video_title=video_title,
                    action_type="analysis"
                )
            
            print(f"[STREAM] ✅ 处理完成", flush=True)

        except Exception as e:
            import traceback
            print(f"[STREAM] ❌ 异常: {e}", flush=True)
            traceback.print_exc()
            yield f'data: [ERROR] {str(e)}\n\n'

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/translate-themes")
async def translate_themes(request: Request):
    """翻译 themes 数据为目标语言"""
    try:
        data = await request.json()
        themes = data.get('themes', [])
        target_language = data.get('language', 'en')
        
        if target_language == 'en' or not themes:
            return {"success": True, "themes": themes}
        
        # 使用 LLM 翻译 themes
        llm_service = get_llm_service()
        
        # 构建翻译请求
        themes_text = json.dumps(themes, ensure_ascii=False)
        
        language_names = {
            'zh': 'Chinese',
            'ja': 'Japanese', 
            'ko': 'Korean',
            'es': 'Spanish',
            'fr': 'French',
        }
        target_lang_name = language_names.get(target_language, target_language)
        
        prompt = f"""Translate the following JSON themes data to {target_lang_name}. 
Keep the JSON structure exactly the same, only translate the text content (title, description, content fields).
Do NOT translate field names like "id", "title", "content", "timestampStart", "color".
Return ONLY the translated JSON array, no explanation.

{themes_text}"""
        
        translated_text = llm_service.llm.invoke(prompt).content.strip()
        
        # 清理可能的 markdown 代码块
        if translated_text.startswith('```'):
            translated_text = translated_text.split('\n', 1)[1] if '\n' in translated_text else translated_text[3:]
        if translated_text.endswith('```'):
            translated_text = translated_text[:-3]
        translated_text = translated_text.strip()
        
        translated_themes = json.loads(translated_text)
        print(f"[SUCCESS] 翻译了 {len(translated_themes)} 个 themes 到 {target_language}")
        
        return {"success": True, "themes": translated_themes}
    except Exception as e:
        print(f"[ERROR] 翻译 themes 失败: {e}")
        return {"success": False, "error": str(e), "themes": data.get('themes', [])}


def translate_cached_data(cached_data: dict, target_language_code: str) -> dict:
    """
    使用 LangChain 翻译缓存数据
    """
    if target_language_code == 'en':
        return cached_data
    
    try:
        llm_service = get_llm_service()
        return llm_service.translate_video_data(cached_data, target_language_code)
    except Exception as e:
        print(f"[WARN] 翻译失败: {e}，返回原始数据")
        return cached_data


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
    import os 

    # SSL 证书路径
    ssl_keyfile = "/home/ubuntu/PageOn_video_web/ssl/server.key"
    ssl_certfile = "/home/ubuntu/PageOn_video_web/ssl/server.crt"

    # 检查是否存在 SSL 证书
    use_https = os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile)


    if use_https:
        print("🔒 Server is running on https://localhost:5500 (HTTPS)")
        print("📊 API endpoint: https://localhost:5500/api")
        print("📚 API docs: https://localhost:5500/docs")
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=5500,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile
        )
    else:
        print("🚀 Server is running on http://localhost:5500 (HTTP)")
        print("📊 API endpoint: http://localhost:5500/api")
        print("📚 API docs: http://localhost:5500/docs")
        print("⚠️  No SSL certificates found. To enable HTTPS, create:")
        print(f"    - {ssl_keyfile}")
        print(f"    - {ssl_certfile}")
        uvicorn.run(app, host="0.0.0.0", port=5500)
