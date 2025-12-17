"""
Chat 模块 - LLM 聊天接口

功能：
- 与视频上下文进行对话
- 支持用户隔离的会话管理
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

# 导入 LLM 服务
from llm_server import get_llm_service

# 创建路由器
router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    video_context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """聊天响应模型"""
    success: bool
    response: str
    timestamp: str


@router.post("/chat", response_model=ChatResponse)
async def chat(chat_request: ChatRequest, request: Request):
    """
    LLM 聊天接口 - 使用 LangChain（支持用户隔离）
    
    Request Body:
        {
            "message": "用户消息",
            "video_context": {
                "videoId": "xxx",
                "title": "视频标题",
                ...
            }
        }
    
    Response:
        {
            "success": true,
            "response": "AI 回复内容",
            "timestamp": "2024-01-01T00:00:00"
        }
    """
    user_message = chat_request.message
    video_context = chat_request.video_context

    # 获取用户标识（优先使用 X-Session-ID header，否则用 IP）
    user_id = request.headers.get("X-Session-ID") or request.client.host or "anonymous"
    
    print(f"[INFO] Chat request - User: {user_id}, Video context: {video_context}", flush=True)

    try:
        # 使用 LangChain LLM 服务
        llm_service = get_llm_service()
        
        # 从视频上下文获取 video_id
        video_id = video_context.get('videoId', 'default') if video_context else 'default'
        
        response = llm_service.chat_with_video(
            user_message=user_message,
            video_context=video_context,
            video_id=video_id,
            user_id=user_id  # 传入用户标识实现隔离
        )

        return ChatResponse(
            success=True,
            response=response,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        print(f"[ERROR] Chat failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                'error': str(e),
                'response': 'sorry, please try again later.'
            }
        )

