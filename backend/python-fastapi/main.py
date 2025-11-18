"""
Python + FastAPI 后端示例
安装依赖: pip install fastapi uvicorn python-multipart
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import json
from datetime import datetime
from pathlib import Path

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


def load_video_data():
    """加载视频数据"""
    data_path = DATA_DIR / 'video-data.json'
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@app.get("/api/videos/{video_id}")
async def get_video(video_id: str):
    """获取视频数据"""
    try:
        video_data = load_video_data()
        return video_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@app.get("/api/videos/{video_id}/comments", response_model=List[CommentResponse])
async def get_comments(video_id: str):
    """获取评论"""
    return comments_db.get(video_id, [])


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


@app.get("/api/videos/{video_id}/progress", response_model=ProgressResponse)
async def get_progress(video_id: str):
    """获取播放进度"""
    return progress_db.get(video_id, {
        "timestamp": 0,
        "updatedAt": datetime.now().isoformat()
    })


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


# 提供静态文件
@app.get("/")
async def root():
    """返回首页"""
    index_path = BASE_DIR / "index.html"
    return FileResponse(index_path)


# 挂载静态文件目录
app.mount("/css", StaticFiles(directory=str(BASE_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(BASE_DIR / "js")), name="js")
app.mount("/data", StaticFiles(directory=str(BASE_DIR / "data")), name="data")


if __name__ == "__main__":
    import uvicorn
    print("🚀 Server is running on http://localhost:8000")
    print("📊 API endpoint: http://localhost:8000/api")
    print("📚 API docs: http://localhost:8000/docs")
    print("🌐 Frontend: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

