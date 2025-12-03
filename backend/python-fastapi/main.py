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
    sectionId: str
    title: str
    snippet: str
    timestamp: str


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


def load_video_data():
    """加载视频数据"""
    data_path = DATA_DIR / 'video-data.json'
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@app.get("/api/videos/{video_id}")
async def get_video(video_id: str):
    """获取视频数据"""
    try:
        data_path = DATA_DIR / f'video-data-{video_id}.json'
        if not data_path.exists():
            raise HTTPException(status_code=404, detail=f"视频数据文件不存在: video-data-{video_id}.json")
        
        with open(data_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/transcript/{video_id}")
async def get_transcript(video_id: str):
    """获取视频字幕"""
    transcript_file = DATA_DIR / f"transcript_{video_id}.txt"
    
    if not transcript_file.exists():
        raise HTTPException(status_code=404, detail=f"字幕文件不存在: transcript_{video_id}.txt")
    
    try:
        with open(transcript_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return Response(content=content, media_type="text/plain; charset=utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取字幕失败: {str(e)}")


@app.get("/api/videos")
async def get_videos():
    """获取视频列表"""
    videos = [
        {
            "videoId": "lQHK61IDFH4",
            "title": "NVIDIA GTC Washington D.C. Keynote",
            "description": "CEO Jensen Huang keynote",
            "thumbnail": "https://img.youtube.com/vi/lQHK61IDFH4/maxresdefault.jpg",
            "duration": "01:42:25",
            "uploadDate": "2024-03-18"
        }
    ]
    return videos


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
async def search(q: str = Query(..., description="搜索关键词")):
    """搜索内容"""
    query = q.lower()
    
    try:
        video_data = load_video_data()
        results = []
        
        for section in video_data.get('sections', []):
            title = section['title'].lower()
            content = section['content'].lower()
            
            if query in title or query in content:
                # 提取匹配片段
                index = content.find(query)
                if index != -1:
                    snippet_start = max(0, index - 50)
                    snippet_end = min(len(section['content']), index + len(query) + 50)
                    snippet = '...' + section['content'][snippet_start:snippet_end] + '...'
                else:
                    snippet = section['content'][:100] + '...'
                
                results.append({
                    "videoId": video_data['videoInfo']['videoId'],
                    "sectionId": section['id'],
                    "title": section['title'],
                    "snippet": snippet,
                    "timestamp": section['timestampStart']
                })
        
        return {
            "results": results,
            "total": len(results)
        }
    except Exception as e:
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
        # 清理文件名中的特殊字符
        safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title[:50]  # 限制长度
        filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        print(f'[SUCCESS] PDF 生成成功: {filename}')
        
        # 读取 buffer 内容
        pdf_content = pdf_buffer.getvalue()
        
        # 使用 Response 而不是 StreamingResponse，确保完整传输
        return Response(
            content=pdf_content,
            media_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
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
        chapters = extract_youtube_chapters(video_id)
        
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
        model="gemini-2.5-flash",
        contents=[full_prompt]
    )
    
    return response.text


@app.post('/api/process-video')
async def process_video(request_data: ProcessVideoRequest):
    """
    处理前端传来的 YouTube 视频 URL：
    - 提取视频 ID
    - 通过 get_full_transcript 获取完整字幕和视频信息
    - 将字幕写入 data/transcript_{video_id}.txt
    - 返回基本处理状态给前端
    """
    url = request_data.url

    if not url:
        raise HTTPException(status_code=400, detail='URL is required')

    try:
        print(f"[INFO] 开始处理视频: {url}")

        import sys
        sys.path.append(str(BASE_DIR))

        from get_full_transcript_ytdlp import get_full_transcript, display_full_transcript
        from youtube_client import YouTubeClient

        # 提取视频 ID
        video_id = YouTubeClient.extract_video_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail='无法从URL提取视频ID')

        # print(f"[INFO] 提取到视频 ID: {video_id}")

        # 获取完整字幕与视频详情（注意传入的是完整 URL）
        result = get_full_transcript(url, language='en')
        if not result or result == (None, None):
            raise HTTPException(status_code=500, detail='无法获取视频字幕')

        transcript, details = result
        
        # 再次检查解包后的值
        if not transcript or not details:
            raise HTTPException(status_code=500, detail='无法获取视频字幕或详情')

        # 保存字幕到文件，供后续 /api/videos/<video_id> 使用
        output_file = DATA_DIR / f"transcript_{video_id}.txt"
        try:
            display_full_transcript(transcript, output_file=str(output_file), details=details)
            print(f"[SUCCESS] 字幕已写入文件: {output_file}")
        except Exception as save_error:
            print(f"[WARN] 保存字幕文件失败: {save_error}")

        # 使用 LLM 处理和结构化字幕
        try:
            print(f"[INFO] 开始使用 LLM 处理字幕...")
            video_data_json = chat_with_gemini(transcript, details, video_id)
            
            # 保存生成的 JSON 到 data 目录
            json_output_file = DATA_DIR / f"video-data-{video_id}.json"
            with open(json_output_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(video_data_json, f, ensure_ascii=False, indent=2)
            
            print(f"[SUCCESS] 视频数据已保存到: {json_output_file}")
            
            return {
                'success': True,
                'videoId': video_id,
                'title': details.get('title', ''),
                'transcriptLength': len(transcript),
                'dataFile': f"video-data-{video_id}.json",
                'message': '视频处理成功'
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




def chat_with_gemini(transcript, details, video_id):
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


    # 准备字幕文本
    transcript_text = "\n".join([f"[{item['start']}] {item['text']}" for item in transcript])
    
    # 构建 prompt，避免 f-string 嵌套问题
    title = details.get('title', 'Unknown')
    def sample_transcript(transcript_text, max_chars=15000, num_segments=10):
      """
      均匀采样文本：将文本分为N个片段，均匀分布在整个时间轴
      """
      total_len = len(transcript_text)
      if total_len <= max_chars:
        return transcript_text

      segment_len = max_chars // num_segments
      if segment_len == 0:
        segment_len = 1
      
      if num_segments > 1:
        step = (total_len - segment_len) // (num_segments - 1)
      else:
        step = 0

      sampled_parts = []
      for i in range(num_segments):
        start_index = i * step
        end_index = start_index + segment_len
        chunk = transcript_text[start_index:end_index]
        sampled_parts.append(chunk)

      separator = "\n\n[...]\n\n"
      return separator.join(sampled_parts)
      
      
      
    transcript_preview = sample_transcript(transcript_text, max_chars=15000, num_segments=10)
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    
    system_prompt = """
You are a video content analyzer. Analyze this YouTube video transcript and generate a structured JSON.

Video Title: """ + title + """
Video ID: """ + video_id + """

Transcript:
""" + transcript_preview + """

Generate JSON with this structure:
{
  "videoInfo": {
    "title": "Video Title",
    "videoId": "xxx",
    "description": "Brief topic description",
    "thumbnail": "https://img.youtube.com/vi/xxx/maxresdefault.jpg",
    "summary": "2-3 sentence summary"
  },
  "sections": [
    {
      "id": "section1",
      "title": "Section Title",
      "content": [
        {"content": "Key point (1-2 sentences)", "timestampStart": "00:00"}
      ]
    }
  ]
}

REQUIREMENTS:
- **MUST cover the ENTIRE video from beginning to end**
- Create sections based on natural topic changes in the video
- Each content item: 1-2 concise sentences (focus on key insights)
- Include timestamps spanning the full video duration
- Thumbnail: """ + thumbnail_url + """
- Output ONLY valid JSON
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
