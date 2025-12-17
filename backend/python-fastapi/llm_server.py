"""
LangChain Server - OpenRouter Integration
"""
import os

from typing import Optional, Dict, Any, List, AsyncIterator
import json
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from collections import deque

# OpenRouter 配置
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

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

class Theme(BaseModel):
    """视频主题 - 跨章节聚合的内容主题"""
    id: str = Field(description="主题 ID，如 theme1")
    title: str = Field(description="主题标题")
    description: str = Field(description="主题简要描述")
    content: List[ContentItem] = Field(description="该主题相关的内容列表，从各章节聚合")

class ThemeResult(BaseModel):
    """主题生成结果"""
    themes: List[Theme] = Field(description="2-5个主题列表")

# ========= LLM Server =========

class LLMService:
    """统一 LLM 服务 - OpenRouter"""
    def __init__(self):
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        
        # 主模型 (用于复杂任务，transcript解析)
        # OpenRouter 模型格式: provider/model-name
        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            model="google/gemini-2.5-flash-lite",  # 或 "anthropic/claude-3.5-sonnet"
            temperature=0.3,
            streaming=True,
            default_headers={
                "HTTP-Referer": "https://your-app.com",  # 可选：你的应用 URL
                "X-Title": "YouTube Process API",        # 可选：应用名称
            }
        )

        # 轻量模型 用于chat和翻译
        self.llm_lite = ChatOpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            model="google/gemini-2.5-flash-lite",  # 或 "openai/gpt-4o-mini"
            temperature=0.7,
            default_headers={
                "HTTP-Referer": "https://your-app.com",
                "X-Title": "YouTube Process API",
            }
        )

        # 聊天记录（保留最近对话）- 使用简单的 deque 实现
        self._chat_memories: Dict[str, deque] = {}
        self._memory_window_size = 5  # 保留最近5轮对话

    def _get_memory(self, video_id: str, user_id: str = "anonymous") -> deque:
        """获取或创建用户+视频的聊天记录（用户隔离）"""
        memory_key = f"{user_id}:{video_id}"
        if memory_key not in self._chat_memories:
            self._chat_memories[memory_key] = deque(maxlen=self._memory_window_size * 2)
        return self._chat_memories[memory_key]
    
    def _add_to_memory(self, video_id: str, user_id: str, human_msg: str, ai_msg: str):
        """添加对话到记忆"""
        memory = self._get_memory(video_id, user_id)
        memory.append(HumanMessage(content=human_msg))
        memory.append(AIMessage(content=ai_msg))
    
    def _get_memory_messages(self, video_id: str, user_id: str = "anonymous") -> List:
        """获取记忆中的消息列表"""
        memory = self._get_memory(video_id, user_id)
        return list(memory)
    
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
2. **Time Clips**: Identify precise video segments with start and end timestamps
3. **Contextual Understanding**: Comprehend overall video structure

Response Format:
- When referencing video moments, use TIME CLIPS format:
[START - END] Description
  Example: [02:30 - 04:15] Explanation of the main concept
  
- For single moments: [05:30] Brief description
- List all relevant clips if topic appears multiple times
- Be concise yet informative
- Friendly and professional tone

Example Response:
"The video discusses AI in these segments:
[01:20 - 03:45] Introduction to machine learning basics
[08:10 - 12:30] Deep learning applications
[15:00 - 15:45] Future predictions"
"""

        # 构建 prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "Video Context: {video_context}\n\nUser Question: {question}"),
        ])

        # 获取用户+视频的独立记忆
        chat_history = self._get_memory_messages(video_id, user_id)

        # 创建 Chain
        chain = prompt | self.llm_lite | StrOutputParser()

        # run
        result = chain.invoke({
            "video_context": str(video_context) if video_context else "No context",
            "question": user_message,
            "chat_history": chat_history,
        })

        # 保存到记忆
        self._add_to_memory(video_id, user_id, user_message, result)

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
Translate ALL text content in the JSON to {target_language}.

CRITICAL - YOU MUST TRANSLATE:
- videoInfo.title (视频标题 - MUST be translated!)
- videoInfo.description
- videoInfo.summary
- All sections[].title
- All sections[].content
- All chapters[].title (if exists)

DO NOT TRANSLATE (keep original):
- videoId, id, thumbnail, thumbnail_url
- timestampStart, timestamp, any numbers/URLs

OUTPUT:
- Return the complete JSON with translated text
- Keep exact same structure
- Output valid JSON only, no explanation"""),
            ("human", "{json_data}")
        ])
        
        chain = prompt | self.llm_lite | StrOutputParser()
        
        print(f"[Translate] 🔄 开始翻译到 {target_lang}...")
        print(f"[Translate] 📝 原始标题: {cached_data.get('videoInfo', {}).get('title', 'N/A')[:50]}...")
        
        response = chain.invoke({
            "target_language": target_lang,
            "json_data": json.dumps(cached_data, ensure_ascii=False)
        })
        
        print(f"[Translate] 📥 LLM 响应长度: {len(response)}")
        print(f"[Translate] 📥 LLM 响应前200字符: {response[:200]}...")
        
        # 解析 JSON
        result = self._extract_json(response)
        
        if not result:
            print(f"[Translate] ❌ JSON 解析失败，返回原始数据")
            return cached_data
        
        print(f"[Translate] ✅ 翻译完成，标题: {result.get('videoInfo', {}).get('title', 'N/A')[:50]}...")
        return result


    # ==== theme 生成 ====
    
    # 语言名称映射
    LANGUAGE_NAMES = {
        "zh": "Chinese (简体中文)",
        "en": "English",
        "ja": "Japanese (日本語)",
        "ko": "Korean (한국어)",
        "es": "Spanish (Español)",
        "fr": "French (Français)",
        "de": "German (Deutsch)",
    }

    def generate_themes(
        self,
        video_data: dict,
        language: str = "en",
    ) -> ThemeResult:
        """
        根据视频分析 JSON 生成 2-5 个主题
        
        Args:
            video_data: 视频分析结果 JSON，包含 videoInfo 和 sections
            language: 输出语言代码（默认英语）
            
        Returns:
            ThemeResult: 包含 2-5 个主题的结果
        """
        parser = PydanticOutputParser(pydantic_object=ThemeResult)
        target_lang = self.LANGUAGE_NAMES.get(language, "English")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert content analyst. Analyze the video content and identify 2-5 major THEMES.

**OUTPUT LANGUAGE**: Generate ALL text content (title, description, content) in {target_language}.

**THEME vs SECTION**: 
- Sections are chronological (time-based)
- Themes are conceptual (topic-based, cross-cutting)

**Your Task**:
1. Identify 2-5 distinct themes based on content richness
2. For each theme, aggregate relevant content from ALL sections
3. Keep original timestamps for each content item

{format_instructions}

**REQUIREMENTS**:
- Generate 2-5 themes based on content depth (more content = more themes)
- Each theme should have a clear, descriptive title IN {target_language}
- Include a brief description explaining the theme IN {target_language}
- Aggregate content items from different sections if they relate to the same theme
- ALL content text must be in {target_language}
- Preserve original timestampStart values (do NOT translate timestamps)
- Theme IDs: theme1, theme2, etc."""),
            ("human", """Video Title: {title}

Video Content (sections):
{sections_json}

Generate themes in {target_language}:""")
        ])
        
        chain = prompt | self.llm | parser
        
        # 准备 sections JSON
        sections_json = json.dumps(video_data.get('sections', []), ensure_ascii=False, indent=2)
        
        result = chain.invoke({
            "title": video_data.get('videoInfo', {}).get('title', 'Unknown'),
            "sections_json": sections_json,
            "format_instructions": parser.get_format_instructions(),
            "target_language": target_lang,
        })
        
        return result

    async def generate_themes_stream(
        self,
        video_data: dict,
        language: str = "en",
    ) -> AsyncIterator[str]:
        """
        流式生成主题
        
        Args:
            video_data: 视频分析结果 JSON
            language: 输出语言代码（默认英语）
            
        Yields:
            str: 流式输出的 JSON 片段
        """
        target_lang = self.LANGUAGE_NAMES.get(language, "English")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert content analyst. Analyze the video content and identify 2-5 major THEMES.

**OUTPUT LANGUAGE**: Generate ALL text content (title, description, content) in {target_language}.

**THEME vs SECTION**: 
- Sections are chronological (time-based)
- Themes are conceptual (topic-based, cross-cutting)

Generate JSON with this EXACT structure:
{{
  "themes": [
    {{
      "id": "theme1",
      "title": "Theme Title in {target_language}",
      "description": "Brief description in {target_language}",
      "content": [
        {{"content": "Key point in {target_language}", "timestampStart": "00:05:30"}}
      ]
    }}
  ]
}}

**REQUIREMENTS**:
- Generate 2-5 themes based on content depth
- Each theme: clear title + description + aggregated content
- ALL text must be in {target_language}
- Preserve original timestampStart values (do NOT translate timestamps)
- Output valid JSON only, no markdown code blocks"""),
            ("human", """Video Title: {title}

Video Content (sections):
{sections_json}

Generate themes in {target_language}:""")
        ])
        
        sections_json = json.dumps(video_data.get('sections', []), ensure_ascii=False, indent=2)
        
        print(f"[LLM] 开始流式生成主题，语言: {target_lang}...", flush=True)
        full_response = ""
        chunk_idx = 0
        
        async for chunk in (prompt | self.llm).astream({
            "title": video_data.get('videoInfo', {}).get('title', 'Unknown'),
            "sections_json": sections_json,
            "target_language": target_lang,
        }):
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            if content:
                chunk_idx += 1
                full_response += content
                if chunk_idx <= 3:
                    print(f"[LLM] theme chunk#{chunk_idx}: {repr(content[:50])}", flush=True)
                yield content
        
        print(f"[LLM] 主题生成完成，总chunks:{chunk_idx}", flush=True)
        yield "\n[STREAM_END]"

    def parse_themes_result(self, raw_text: str) -> ThemeResult:
        """
        解析流式输出的主题结果
        
        Args:
            raw_text: LLM 生成的原始 JSON 文本
            
        Returns:
            ThemeResult: 解析后的主题结果
        """
        data = self._extract_json(raw_text.replace('[STREAM_END]', '').strip())
        return ThemeResult(**data)


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

