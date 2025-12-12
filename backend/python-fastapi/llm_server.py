"""
LangChain Server
"""
import os

from typing import Optional, Dict, Any, List, AsyncIterator
import json
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain.memory import ConversationBufferWindowMemory

# == Pydantic 输出模型 ==

class ContentItem(BaseModel):
    content: str = Field(description="关键点内容（1-2句话）")
    timestampStart: str = Field(description="时间戳，格式： HH:MM:SS")

class Section(BaseModel):
    """视频章节"""
    id: str = Field(description="章节 ID，如 section1")
    title: str = Field(description="章节标题")
    content: List[ContentItem] = Field(description="章节内容列表")

class VideoInfo(BaseModel):
    """视频基本信息"""
    title: str = Field(description="视频标题")
    videoId: str = Field(description="视频 ID")
    description: str = Field(description="简短描述")
    thumbnail: str = Field(description="缩略图 URL")
    summary: str = Field(description="2-3句话总结")

class VideoAnalysisResult(BaseModel):
    """视频分析结果"""
    videoInfo: VideoInfo
    sections: List[Section] = Field(description="视频章节列表")

# ========= LLM Server =========

class LLMService:
    """统一 LLM 服务"""
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        
        # 主模型 (用与复杂任务，transcript解析)
        self.llm = ChatGoogleGenerativeAI(
            api_key=api_key,
            model="gemini-3-pro-preview",
            temperature=0.3,
            streaming=True,  # 启用流式输出
        )

        # 轻量模型 用于chat和翻译
        self.llm_lite = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=api_key,
            temperature=0.7,
        )

        # 聊天记录（保留最近对话）
        self._chat_memories: Dict[str, ConversationBufferWindowMemory] = {}

    def _get_memory(self, video_id: str, user_id: str = "anonymous") -> ConversationBufferWindowMemory:
        """获取或创建用户+视频的聊天记录（用户隔离）"""
        memory_key = f"{user_id}:{video_id}"
        if memory_key not in self._chat_memories:
            self._chat_memories[memory_key] = ConversationBufferWindowMemory(
                k=5,
                return_messages=True,
            )
        return self._chat_memories[memory_key]
    
    def clear_user_memory(self, video_id: str, user_id: str = "anonymous"):
        """清除指定用户的视频聊天记录"""
        memory_key = f"{user_id}:{video_id}"
        if memory_key in self._chat_memories:
            del self._chat_memories[memory_key]


    # ==== transcript 分析 Chain ====
    def analyze_video_transcript(
        self,
        transcript: List[str],
        details: dict,
        video_id: str,
    ) -> VideoAnalysisResult:
        """
        分析视频字幕并生成结构化结果
        使用 LangChain 的 pydanticOutputParser 确保输出格式正确
        """
        def seconds_to_timestamp(seconds):
            total = int(float(seconds))
            h, m, s = total // 3600, (total % 3600) // 60, total % 60
            return f"{h:02d}:{m:02d}:{s:02d}"

        transcript_text = "\n".join([
            f"[{seconds_to_timestamp(item['start'])}] {item['text']}"
            for item in transcript
        ])

        transcript_preview = self._sample_transcript(transcript_text)

        parser = PydanticOutputParser(pydantic_object=VideoAnalysisResult)

        # 创建 Prompt 模板
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert video content analyst. Analyze this YouTube video transcript and extract valuable insights.

**SUMMARIZE, DON'T TRANSCRIBE**: Extract insights, arguments, and conclusions - NOT word-for-word transcript.

{format_instructions}

REQUIREMENTS:
- Cover the ENTIRE video from beginning to end
- Create sections based on natural topic changes
- Each content item: 1-2 concise sentences
- timestampStart format: "HH:MM:SS"
- COPY timestamps EXACTLY from the transcript"""),
            ("human", """Video Title: {title}
Video ID: {video_id}
Thumbnail: {thumbnail}

Transcript:
{transcript}""")
        ])

        # 创建 Chain
        chain = prompt | self.llm | parser

        # run
        result = chain.invoke({
            "title": details.get('title', 'Unknown'),
            "video_id": video_id,
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "transcript": transcript_preview,
            "format_instructions": parser.get_format_instructions(),
        })

        return result

    async def analyze_video_transcript_stream(
        self,
        transcript: List[dict],
        details: dict,
        video_id: str,
    ) -> AsyncIterator[str]:
        """
        流式分析视频字幕，逐步输出生成的 JSON
        
        Yields:
            str: 流式输出的文本块（JSON 片段）
        """
        def seconds_to_timestamp(seconds):
            total = int(float(seconds))
            h, m, s = total // 3600, (total % 3600) // 60, total % 60
            return f"{h:02d}:{m:02d}:{s:02d}"

        transcript_text = "\n".join([
            f"[{seconds_to_timestamp(item['start'])}] {item['text']}"
            for item in transcript
        ])

        transcript_preview = self._sample_transcript(transcript_text)

        # 不使用 PydanticOutputParser，直接流式输出
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert video content analyst. Analyze this YouTube video transcript and extract valuable insights.

**SUMMARIZE, DON'T TRANSCRIBE**: Extract insights, arguments, and conclusions - NOT word-for-word transcript.

Generate JSON with this EXACT structure:
{{
  "videoInfo": {{
    "title": "Video Title",
    "videoId": "{video_id}",
    "description": "Brief topic description",
    "thumbnail": "https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
    "summary": "2-3 sentence summary"
  }},
  "sections": [
    {{
      "id": "section1",
      "title": "Section Title",
      "content": [
        {{"content": "Key point (1-2 sentences)", "timestampStart": "00:00:00"}}
      ]
    }}
  ]
}}

REQUIREMENTS:
- Cover the ENTIRE video from beginning to end
- Create sections based on natural topic changes
- Each content item: 1-2 concise sentences
- timestampStart format: "HH:MM:SS"
- COPY timestamps EXACTLY from the transcript
- Output valid JSON only, no markdown code blocks"""),
            ("human", """Video Title: {title}
Video ID: {video_id}
Thumbnail: {thumbnail}

Transcript:
{transcript}""")
        ])

        # 流式输出
        print(f"[LLM] 开始流式调用...", flush=True)
        full_response = ""
        chunk_idx = 0
        async for chunk in (prompt | self.llm).astream({
            "title": details.get('title', 'Unknown'),
            "video_id": video_id,
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "transcript": transcript_preview,
        }):
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            if content:
                chunk_idx += 1
                full_response += content
                # 调试前几个 chunks
                if chunk_idx <= 5:
                    print(f"[LLM] chunk#{chunk_idx} 长度:{len(content)} 内容前50字符:{repr(content[:50])}", flush=True)
                yield content
        
        print(f"[LLM] 流式完成，总chunks:{chunk_idx}, 总长度:{len(full_response)}", flush=True)
        # 流式结束标记（用于前端判断）
        yield "\n[STREAM_END]"

    def parse_analysis_result(self, raw_text: str) -> VideoAnalysisResult:
        """
        解析流式输出的结果为结构化对象
        
        Args:
            raw_text: LLM 生成的原始 JSON 文本
            
        Returns:
            VideoAnalysisResult: 解析后的结构化结果
        """
        # 清理文本
        import re
        text = re.sub(r'^```json?\s*', '', raw_text.strip())
        text = re.sub(r'\s*```$', '', text)
        text = text.replace('[STREAM_END]', '').strip()
        
        # 提取 JSON
        start = text.find('{')
        if start == -1:
            raise ValueError("No JSON found in response")
        
        brace_count = 0
        end = start
        for i, c in enumerate(text[start:], start):
            if c == '{': brace_count += 1
            elif c == '}': 
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
        
        json_str = text[start:end]
        data = json.loads(json_str)
        
        # 转换为 Pydantic 模型
        return VideoAnalysisResult(**data)


    # === chat ===

    def chat_with_video(
        self, 
        user_message: str, 
        video_context: Optional[Dict[str, Any]] = None,
        video_id: str = "default",
        user_id: str = "anonymous"
    ) -> str:
        """
        基于视频内容的聊天，支持对话记忆（用户隔离）
        
        Args:
            user_message: 用户消息
            video_context: 视频上下文信息
            video_id: 视频 ID
            user_id: 用户标识（用于隔离不同用户的聊天记录）
        """
        system_prompt = """You are PageOn-Video assistant, helping users understand video content.

Your abilities:
1. **Deep Analysis**: Provide accurate responses based on video transcript and chapters
2. **Timestamps**: Mark precise timestamps in format [MM:SS] or [HH:MM:SS]
3. **Contextual Understanding**: Comprehend overall video structure

Response Format:
- Use [05:30] format to cite timestamps
- List all relevant timestamps if topic appears multiple times
- Be concise yet informative
- Friendly and professional tone"""

        # 构建 prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "Video Context: {video_context}\n\nUser Question: {question}"),
        ])

        # 获取用户+视频的独立记忆
        memory = self._get_memory(video_id, user_id)
        chat_history = memory.chat_memory.messages

        # 创建 Chain
        chain = prompt | self.llm_lite | StrOutputParser()

        # run
        result = chain.invoke({
            "video_context": str(video_context) if video_context else "No context",
            "question": user_message,
            "chat_history": chat_history,
        })

        # 保存到记忆
        memory.chat_memory.add_user_message(user_message)
        memory.chat_memory.add_ai_message(result)

        return result


    # ==== translate ====

    def translate_video_data(
        self, 
        cached_data: dict, 
        target_language_code: str
    ) -> dict:
        """
        翻译视频数据到目标语言
        """
        import json
        
        language_names = {
            "zh": "Chinese (简体中文)",
            "en": "English",
            "ja": "Japanese (日本語)",
            "ko": "Korean (한국어)",
            "es": "Spanish (Español)",
            "fr": "French (Français)",
            "de": "German (Deutsch)",
        }
        target_lang = language_names.get(target_language_code, "English")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a professional translator. 
Translate the video content JSON to {target_language}.

RULES:
1. Translate ONLY text fields (title, description, summary, content)
2. DO NOT translate: videoId, thumbnail, id, timestampStart, timestamp
3. Keep exact same JSON structure
4. Output valid JSON only"""),
            ("human", "{json_data}")
        ])
        
        chain = prompt | self.llm_lite | StrOutputParser()
        
        response = chain.invoke({
            "target_language": target_lang,
            "json_data": json.dumps(cached_data, ensure_ascii=False)
        })
        
        # 解析 JSON
        return self._extract_json(response)


    # ==== 工具方法 ====

    def _sample_transcript(self, text: str, max_chars: int = 15000) -> str:
        """均匀采样长字幕"""
        if len(text) <= max_chars:
            return text
        
        lines = text.strip().split('\n')
        num_segments = 10
        lines_per_seg = len(lines) // num_segments
        
        sampled = []
        for i in range(num_segments):
            start = i * lines_per_seg
            end = min(start + lines_per_seg, len(lines))
            sampled.append('\n'.join(lines[start:end]))
        
        return "\n\n[...]\n\n".join(sampled)
    
    def _extract_json(self, text: str) -> dict:
        """从文本中提取 JSON"""
        import json
        import re
        
        text = re.sub(r'^```json?\s*', '', text.strip())
        text = re.sub(r'\s*```$', '', text)
        
        start = text.find('{')
        if start == -1:
            return {}
        
        brace_count = 0
        end = start
        for i, c in enumerate(text[start:], start):
            if c == '{': brace_count += 1
            elif c == '}': 
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
        
        return json.loads(text[start:end])


# ========= 全局单例 =========

_llm_service: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    """获取 LLM 服务单例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service

