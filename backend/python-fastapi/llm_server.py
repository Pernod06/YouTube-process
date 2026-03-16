"""
LangChain Server - OpenRouter Integration
"""
import os

from typing import Optional, Dict, Any, List, AsyncIterator
from enum import Enum
import json
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from collections import deque
from supabase_utils import get_supabase_client, get_supabase_config

# 导入 MCP Tools
try:
    from mcp_tools import get_mcp_tools
    MCP_TOOLS_AVAILABLE = True
except ImportError:
    MCP_TOOLS_AVAILABLE = False

# LLM API 配置（支持通过环境变量覆盖默认 OpenRouter 地址）
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
IS_NEWAI_GATEWAY = "newapi.deepwisdom.ai" in OPENROUTER_BASE_URL


def _env_flag(name: str, default: bool = False) -> bool:
    """Parse common truthy/falsey env values."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

# 模型配置：new-api 通常使用不带 provider 前缀的模型名
DEFAULT_MAIN_MODEL = "gemini-3-flash-preview"
DEFAULT_LITE_MODEL = "gemini-2.5-flash"
DEFAULT_IMAGE_MODEL = "gemini-3-pro-image-preview"
MAIN_MODEL = os.getenv("OPENROUTER_MODEL_MAIN", DEFAULT_MAIN_MODEL)
LITE_MODEL = os.getenv("OPENROUTER_MODEL_LITE", DEFAULT_LITE_MODEL)
IMAGE_MODEL = os.getenv("OPENROUTER_MODEL_IMAGE", DEFAULT_IMAGE_MODEL)
KEY_TAKEAWAYS_IMAGE_ENABLED = _env_flag("ENABLE_KEY_TAKEAWAYS_IMAGE", default=True)

# == Pydantic 输出模型 ==

class ContentItem(BaseModel):
    content: str = Field(description="关键点内容（1-2句话）")
    timestampStart: str = Field(description="时间戳，格式： HH:MM:SS")

class Theme(BaseModel):
    """视频主题 - 跨章节聚合的内容主题"""
    id: str = Field(description="主题 ID，如 theme1")
    title: str = Field(description="主题标题")
    description: str = Field(description="主题简要描述")
    content: List[ContentItem] = Field(description="该主题相关的内容列表，从各章节聚合")

class ThemeResult(BaseModel):
    """主题生成结果"""
    themes: List[Theme] = Field(description="2-5个主题列表")


# == 段落切分与标签 Pydantic 模型 ==

class SegmentTag(str, Enum):
    """可用的语义标签"""
    INTRODUCTION = "Introduction"
    BACKGROUND = "Background"
    METHODOLOGY = "Methodology"
    IMPLEMENTATION = "Implementation"
    EXAMPLE = "Example"
    EXPERIMENT = "Experiment"
    RESULTS = "Results"
    DISCUSSION = "Discussion"
    COMPARISON = "Comparison"
    PROBLEM = "Problem"
    SOLUTION = "Solution"
    TIPS = "Tips"
    CONCLUSION = "Conclusion"
    QA = "QA"
    OTHER = "Other"

class TranscriptSegment(BaseModel):
    """转录文本的一个语义段落"""
    tag: SegmentTag = Field(description="该段落的语义标签")
    timestamp_start: str = Field(description="段落开始时间戳，格式 HH:MM:SS")
    timestamp_end: str = Field(description="段落结束时间戳，格式 HH:MM:SS")
    summary: str = Field(description="该段落的简要概括（1-2句话）")
    lines: List[str] = Field(description="该段落包含的原始转录行（保留时间戳）")

class SegmentedTranscript(BaseModel):
    """切分后的转录文本"""
    segments: List[TranscriptSegment] = Field(description="按语义切分的段落列表，按时间顺序排列")


# == V2.0 结构化文章 Pydantic 模型 ==

class ArticleMeta(BaseModel):
    """文章元信息"""
    title: str = Field(description="引人注目的标题（5-10个词）")
    tags: List[str] = Field(description="3-5个标签")
    reading_time: str = Field(description="预计阅读时间，如 '5 min'")
    difficulty: str = Field(description="难度: Beginner/Intermediate/Advanced")
    last_updated: str = Field(description="更新日期 YYYY-MM-DD")

class HeaderHook(BaseModel):
    """头部引言"""
    quote: str = Field(description="一句引人注目的金句或核心观点")
    author: str = Field(default="", description="说话者姓名（如有）")

class SummaryBox(BaseModel):
    """摘要框"""
    key_insight: str = Field(description="一句话总结核心价值（'Aha!' 时刻）")
    bullet_points: List[str] = Field(description="3个关键要点（可操作或事实性）")

class BackgroundCard(BaseModel):
    """背景知识卡片"""
    type: str = Field(description="类型: Concept / Person / Tool")
    name: str = Field(description="实体名称")
    description: str = Field(description="一句话定义或上下文")
    icon_hint: str = Field(description="建议的 emoji 图标")

class VisualBreak(BaseModel):
    """视觉分隔元素"""
    type: str = Field(description="类型: Quote / Stat")
    content: str = Field(description="显示内容")

class MainBodySection(BaseModel):
    """主体内容章节"""
    section_title: str = Field(description="章节标题（用于目录）")
    content_markdown: str = Field(description="Markdown 格式的章节内容摘要")
    timestamp_ref: str = Field(description="该章节起始时间戳 MM:SS 或 HH:MM:SS")
    visual_break: Optional[VisualBreak] = Field(default=None, description="可选的视觉分隔元素")

class DeepPoint(BaseModel):
    """深度论点"""
    title: str = Field(description="核心论点或复杂概念")
    detailed_explanation: str = Field(description="详细解释 Why 和 How")
    evidence_quote: str = Field(description="支持该论点的原文引用")

class DeepAnalysis(BaseModel):
    """深度分析"""
    mermaid_graph: str = Field(description="Mermaid.js 代码（flowchart 或 mindmap）")
    deep_points: List[DeepPoint] = Field(description="2-3个深度论点")

class QAInteraction(BaseModel):
    """问答交互"""
    question: str = Field(description="读者可能提出的问题")
    answer: str = Field(description="基于文本的回答")
    type: str = Field(description="类型: Core Concept / Counter-Intuitive")

class Resource(BaseModel):
    """资源链接"""
    name: str = Field(description="资源名称")
    type: str = Field(description="类型: Book / Paper / Link / Tool")

class ArticleFooter(BaseModel):
    """文章尾部"""
    resources: List[Resource] = Field(default_factory=list, description="提到的书籍、论文或工具")
    actionable_next_steps: List[str] = Field(description="读者的下一步行动建议")

class StructuredArticleV2(BaseModel):
    """V2.0 结构化文章完整格式"""
    meta: ArticleMeta
    header_hook: HeaderHook
    summary_box: SummaryBox
    background_cards: List[BackgroundCard] = Field(description="3-5个背景知识卡片")
    main_body: List[MainBodySection] = Field(description="3-6个主体章节")
    deep_analysis: DeepAnalysis
    qa_interactions: List[QAInteraction] = Field(description="3对问答")
    footer: ArticleFooter


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
            model=MAIN_MODEL,  # 或 "anthropic/claude-3.5-sonnet"
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
            model=LITE_MODEL,  # 或 "openai/gpt-4o-mini"
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

    async def analyze_video_transcript_stream(
        self,
        transcript: List[dict],
        details: dict,
        video_id: str,
    ) -> AsyncIterator[str]:
        """
        V2.0: 流式分析视频字幕，生成高密度知识网页结构 JSON
        
        Yields:
            str: 流式输出的 JSON 片段
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
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """# Role
You are a Senior Content Architect and Data Structuring Agent. Transform this video transcript into a rich, structured JSON for a high-density knowledge webpage.

# Task
Reconstruct whole information, eliminate noise, and output valid JSON.
**CRITICAL FOR LONG CONTENT:** Do not summarize the whole video broadly. You must process the transcript chronologically and ensure equal depth of analysis for the beginning, middle, and end of the video.

# Output Schema
{{
  "meta": {{
    "title": "Compelling title (5-10 words)",
    "tags": ["Tag1", "Tag2", "Tag3"],
    "reading_time": "e.g., '5 min'",
    "difficulty": "Beginner/Intermediate/Advanced",
    "last_updated": "2025-12-26"
  }},
  "header_hook": {{
    "quote": "A powerful, attention-grabbing quote from the content",
    "author": "Speaker name (if available)"
  }},
  "summary_box": {{
    "key_insight": "ONE profound sentence - the 'Aha!' moment",
    "bullet_points": ["Key takeaway 1", "Key takeaway 2", "Key takeaway 3", ...]
  }},
  "background_cards": [
    {{"type": "Concept/Person/Tool", "name": "Entity name", "description": "1-sentence definition", "icon_hint": "🔥"}}
  ],
  "main_body": [
    {{
      "section_title": "Section heading for TOC",
      "content_markdown": "### Sub-concept Title\n\n**Core Concept**[02:15] is defined as... explanation text.\n\n> \"Direct quote or profound insight from the speaker.\"[02:45]\n\nDetailed breakdown:\n- **Factor A**[03:10]: Explanation...\n- **Factor B**[03:30]: Explanation...\n\n### Practical Application\n\nFinal synthesis sentence[04:00].",
      "timestamp_ref": "MM:SS (section start)",
      "visual_break": {{"type": "Quote/Stat", "content": "Highlight content"}},
      "image_prompt": "Optional: If a diagram/illustration would help explain this section, provide a detailed prompt here"
    }}
  ],

  "visual_summary_chart": {{
    "title": "Logic Map / Structure Tree",
    "ascii_art": "ASCII tree string..."
  }},

  "deep_analysis": {{
    "mermaid_graph": "flowchart LR\\n    A[Start] --> B[Process]\\n    B --> C[End]",
    "deep_points": [
      {{"title": "Complex idea", "detailed_explanation": "Why and How explanation", "evidence_quote": "Supporting quote"}}
    ]
  }},
  "qa_interactions": [
    {{"question": "Smart reader question", "answer": "Answer from text", "type": "Core Concept/Counter-Intuitive"}}
  ],
  "footer": {{
    "resources": [{{"name": "Resource", "type": "Book/Paper/Link"}}],
    "actionable_next_steps": ["Step 1", "Step 2"]
  }}
}}

# Guidelines
1. **Adaptive Sectioning (CRITICAL):**
   - For short videos (<15 min): Use 3-5 sections.
   - For medium videos (15-45 min): Use 5-8 sections.
   - **For long videos (>45 min): Use 8-15 sections.** Do NOT compress 2 hours of content into 3 sections. Break it down by thematic shifts.

2. **Strict Sentence-Level Timestamping:** - **EVERY single sentence** in the `content_markdown` MUST end with a timestamp reference [MM:SS]. 
   - **No Exceptions:** Do not group multiple sentences under one timestamp. 
   - **Format:** Sentence text ends here [MM:SS]. Next sentence starts here [MM:SS].

3. **Rich Markdown Formatting (CRITICAL):**
   - **Structure:** Treat `content_markdown` as a micro-blog post. Use `###` headers to break up text within the section.
   - **Emphasis:** Use **bold** for key terms/concepts, not just random words.
   - **Quotes:** Use Markdown blockquotes (`> Quote text`) for impactful sentences or the speaker's core philosophy.
   - **Lists:** Mix paragraphs with bullet points (`- `) to avoid "walls of text".
   - **Spacing:** Use `\n\n` frequently to create breathing room between paragraphs.
   - **Timestamps:** Every logical block (paragraph or list item) MUST have a [MM:SS] timestamp reference.
4. **Mermaid Graph:** Use flowchart LR format. Escape newlines as \\n in JSON.
5. **Tone:** Professional, objective, educational.
6. **background_cards:** 3-5 key concepts/people/tools.
7. **main_body:** 3-6 logical sections.
8. **Visual Summary (High-Fidelity ASCII Art):**
   - **Goal:** Create a stunning, high-density ASCII visualization. **ABSOLUTELY NO plain text lists or simple descriptions.**
   - **Visual Style:** "Cyberpunk Terminal" or "System Dashboard".
   - **Constraint:** Single-line JSON string with `\n`. Max width 50 chars.
   - **Toolbox:** - Use Box Drawing: `+`, `-`, `|`, `/`, `\`.
     - Use Texture: `░`, `▒`, `▓`, `█`, `*`, `=`, `:`.
     - Use Flow: `-->`, `==>`, `v`, `^`.
   - **Mandatory Layouts (Choose best fit):**
     
     *Option A: The "System Box" (For concepts/structures)*
     "+------------------+      +------------------+\n|   Input Layer    | ===> |   Hidden Layer   |\n+------------------+      +--------+---------+\n        ^                          |\n        |________(Backprop)________|"

     *Option B: The "Rich Timeline" (For history/evolution)*
     "1980s | ░░░░░░             (PC Era)\n2000s | ▒▒▒▒▒▒▒▒▒▒         (Web 2.0)\n2020s | ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓   (AI Era) <-- NOW\n      +------------------------------> Time"

     *Option C: The "Comparison Matrix" (For versus)*
     "      | Speed | Cost | Power\n------+-------+------+------\nGPT-3 |  ** |  $$ | Low\nGPT-4 |  *** |$$$  | High\n------+-------+------+------\nResult: GPT-4 wins on Logic"
     *Option D: **Visual Summary (ASCII Mind Map Mode):**
   - **Objective:** Create a structural overview of the content.
   - **Format:** Single-line JSON string with `\n`. Max width 50 chars.
   - **Visual Language:**
     - **Root Node:** `[ CAPITALIZED ]`
     - **Branches:** `+--`, `L--`, `|`
     - **Leaves:** `( )` or simple text
   - **Anti-Pattern:** Do NOT just make a bullet list. Connect them with lines!
   - **Example:**
     "      [ THE HERO'S JOURNEY ]\n                 |\n      +----------+----------+\n      |                     |\n [Departure]           [Return]\n      |                     |\n   (Call)               (Elixir)"*

   - **CRITICAL:** The output must look like a diagram, not a sentence. Use spacing to align columns perfectly.
9. **qa_interactions:** 3 pairs of Q&A.

CRITICAL: Output ONLY the raw JSON object. Do NOT wrap it in markdown code blocks. Start directly with {{ and end with }}.
Every sentence in main_body's content_markdown MUST end with a timestamp [MM:SS], other sentences should not end with a timestamp."""),
            ("human", """Video Title: {title}
Video ID: {video_id}
Thumbnail: {thumbnail}

# Transcript
{transcript}""")
        ])

        # 流式输出（使用带工具的 LLM 如果可用）
        print(f"[LLM] 开始 V2.0 流式调用...", flush=True)
        full_response = ""
        chunk_idx = 0
        async for chunk in (prompt | self.llm).astream({
            "title": details.get('title', 'Unknown'),
            "video_id": video_id,
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "transcript": transcript_preview,
        }):
            # 处理工具调用（如果存在）
            if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                # 如果有工具调用，这里可以处理，但为了保持流式输出，我们暂时跳过
                # 在实际应用中，可以异步处理工具调用并在后处理阶段注入结果
                print(f"[LLM] 🔧 检测到工具调用请求（在流式输出中暂不处理）", flush=True)
            
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
        
        # 注意：图像生成已移至 main.py 中异步处理，不阻塞主要内容流式输出

    async def analyze_video_transcript(
        self,
        transcript: List[dict],
        details: dict,
        video_id: str,
    ) -> StructuredArticleV2:
        """
        非流式分析入口：复用流式链路并返回完整 V2 schema
        """
        full_response = ""
        async for chunk in self.analyze_video_transcript_stream(transcript, details, video_id):
            if chunk != "\n[STREAM_END]":
                full_response += chunk
        return self.parse_analysis_result(full_response)

    def parse_analysis_result(self, raw_text: str) -> StructuredArticleV2:
        """
        解析流式输出的结果为 V2 结构化对象
        
        Args:
            raw_text: LLM 生成的原始 JSON 文本
            
        Returns:
            StructuredArticleV2: 解析后的结构化结果
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
        
        if "main_body" not in data:
            raise ValueError("LLM response is not a valid V2 article: missing main_body")

        return StructuredArticleV2(**data)


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

        # 尝试获取 MCP Tools 并绑定到 LLM
        llm_with_tools = self.llm_lite
        if MCP_TOOLS_AVAILABLE:
            try:
                mcp_tools = get_mcp_tools()
                if mcp_tools:
                    # 绑定工具到 LLM
                    llm_with_tools = self.llm_lite.bind_tools(mcp_tools)
            except Exception as e:
                print(f"[LLM] ⚠️ 绑定 MCP Tools 失败: {e}，使用普通 LLM")
                llm_with_tools = self.llm_lite

        # 创建 Chain
        chain = prompt | llm_with_tools | StrOutputParser()

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
        翻译视频数据到目标语言 - 分段翻译以避免 token 限制
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
            ("system", """You are a JSON translator. Your task is to translate text values in a JSON object to {target_language}.

RULES:
1. PRESERVE JSON STRUCTURE EXACTLY - same keys, same nesting, same order
2. ONLY translate string VALUES that contain human-readable text
3. DO NOT translate:
   - JSON keys (field names)
   - URLs, IDs, timestamps (e.g., "00:01:45", "LNHBMFCzznE")
   - Technical code (mermaid_graph content)
   - File paths, thumbnail URLs
   - Numbers, booleans, null values
   - English tags in arrays (keep as-is for SEO)

OUTPUT FORMAT:
- Return ONLY valid JSON
- Start with {{ end with }}
- No markdown, no explanation, no extra text"""),
            ("human", "{json_data}")
        ])
        
        # 使用输出能力更强的模型进行翻译
        translate_llm = ChatOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=OPENROUTER_BASE_URL,
            model=LITE_MODEL,
            temperature=0.3,
            max_tokens=16384,
            default_headers={
                "HTTP-Referer": "https://your-app.com",
                "X-Title": "YouTube Process API",
            }
        )
        
        chain = prompt | translate_llm | StrOutputParser()
        
        print(f"[Translate] 🔄 开始分段翻译到 {target_lang}...")
        
        # 分段翻译策略：将大 JSON 拆分为多个部分分别翻译
        result = cached_data.copy()
        
        # 需要翻译的字段列表（按优先级）
        translate_sections = [
            'meta',           # 标题、标签等元数据
            'header_hook',    # 开头引言
            'summary_box',    # 摘要框
            'main_body',      # 主要内容（最大的部分）
            'deep_analysis',  # 深度分析
            'qa_interactions', # 问答
            'footer',         # 页脚资源
        ]
        
        for section_key in translate_sections:
            if section_key not in cached_data or not cached_data[section_key]:
                continue
                
            section_data = cached_data[section_key]
            
            # 跳过不需要翻译的内容
            if section_key == 'deep_analysis' and isinstance(section_data, dict):
                # 保留 mermaid_graph 不翻译
                mermaid = section_data.get('mermaid_graph', '')
                section_to_translate = {k: v for k, v in section_data.items() if k != 'mermaid_graph'}
                if not section_to_translate:
                    continue
            else:
                section_to_translate = section_data
                mermaid = None
            
            try:
                print(f"[Translate] 📝 翻译 {section_key}...")
                response = chain.invoke({
                    "target_language": target_lang,
                    "json_data": json.dumps(section_to_translate, ensure_ascii=False)
                })
                
                if response and response.strip():
                    translated = self._extract_json(response)
                    if translated:
                        # 恢复 mermaid_graph
                        if mermaid and section_key == 'deep_analysis':
                            translated['mermaid_graph'] = mermaid
                        result[section_key] = translated
                        print(f"[Translate] ✅ {section_key} 翻译成功")
                    else:
                        print(f"[Translate] ⚠️ {section_key} JSON 解析失败，保留原文")
                else:
                    print(f"[Translate] ⚠️ {section_key} 响应为空，保留原文")
                    
            except Exception as e:
                print(f"[Translate] ❌ {section_key} 翻译出错: {e}，保留原文")
                continue
        
        print(f"[Translate] ✅ 全部翻译完成")
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
            video_data: 视频分析结果 JSON，使用 V2 main_body schema
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
        
        # V2.0 格式：从 main_body 转换为 LLM 可理解的格式
        if video_data.get('main_body'):
            converted_sections = []
            for i, section in enumerate(video_data.get('main_body', [])):
                converted_sections.append({
                    "id": f"section{i+1}",
                    "title": section.get('section_title', f'Section {i+1}'),
                    "content": [{"content": section.get('content_markdown', ''), "timestampStart": section.get('timestamp_ref', '00:00')}]
                })
            sections_json = json.dumps(converted_sections, ensure_ascii=False, indent=2)
            title = video_data.get('meta', {}).get('title', 'Unknown')
        else:
            sections_json = "[]"
            title = "Unknown"
        
        result = chain.invoke({
            "title": title,
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
        
        # V2.0 格式：从 main_body 转换为 LLM 可理解的格式
        if video_data.get('main_body'):
            converted_sections = []
            for i, section in enumerate(video_data.get('main_body', [])):
                converted_sections.append({
                    "id": f"section{i+1}",
                    "title": section.get('section_title', f'Section {i+1}'),
                    "content": [{"content": section.get('content_markdown', ''), "timestampStart": section.get('timestamp_ref', '00:00')}]
                })
            sections_json = json.dumps(converted_sections, ensure_ascii=False, indent=2)
            title = video_data.get('meta', {}).get('title', 'Unknown')
        else:
            sections_json = "[]"
            title = "Unknown"
        
        print(f"[LLM] 开始流式生成主题，语言: {target_lang}...", flush=True)
        full_response = ""
        chunk_idx = 0
        
        async for chunk in (prompt | self.llm).astream({
            "title": title,
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

    def _sample_transcript(self, text: str, max_chars: int = 20000) -> str:
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

    def _segment_transcript_with_tags(self, transcript_text: str) -> SegmentedTranscript:
        """
        使用 AI + Pydantic 强制输出结构化的段落切分结果
        
        Extraction Agent 模式：使用 PydanticOutputParser 确保 LLM 输出符合 JSON Schema
        
        Args:
            transcript_text: 采样后的转录文本
            
        Returns:
            SegmentedTranscript: 结构化的段落切分结果
        """
        parser = PydanticOutputParser(pydantic_object=SegmentedTranscript)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert content structurer (Extraction Agent). 
Analyze the transcript and segment it into logical paragraphs with semantic tags.

**Available Tags** (SegmentTag enum values):
- Introduction: Opening, greetings, topic introduction
- Background: Context, prior knowledge, prerequisites  
- Methodology: Methods, approaches, techniques explained
- Implementation: Code, setup, step-by-step instructions
- Example: Demonstrations, case studies, examples
- Experiment: Tests, trials, experiments
- Results: Findings, outcomes, data presentation
- Discussion: Analysis, interpretation, implications
- Comparison: Contrasting options, pros/cons
- Problem: Challenges, issues, pain points
- Solution: Fixes, answers, resolutions
- Tips: Best practices, recommendations
- Conclusion: Summary, wrap-up, final thoughts
- QA: Questions and answers section
- Other: Content that doesn't fit other categories

{format_instructions}

**Rules**:
1. Group related consecutive lines into one segment (typically 3-15 lines)
2. Choose the SINGLE most appropriate tag per segment
3. Preserve chronological order
4. Extract timestamp_start from first line, timestamp_end from last line of each segment
5. Write a brief summary (1-2 sentences) for each segment
6. Keep original transcript lines intact in the "lines" array"""),
            ("human", """Segment and tag this transcript:

{transcript}""")
        ])
        
        chain = prompt | self.llm | parser
        
        print(f"[LLM] 开始段落切分与标签 (Extraction Agent)...", flush=True)
        
        result = chain.invoke({
            "transcript": transcript_text,
            "format_instructions": parser.get_format_instructions()
        })
        
        print(f"[LLM] 段落切分完成，共 {len(result.segments)} 个段落", flush=True)
        
        return result

    async def _segment_transcript_with_tags_async(self, transcript_text: str) -> SegmentedTranscript:
        """
        异步版本：使用 AI + Pydantic 强制输出结构化的段落切分结果
        """
        parser = PydanticOutputParser(pydantic_object=SegmentedTranscript)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert content structurer (Extraction Agent). 
Analyze the transcript and segment it into logical paragraphs with semantic tags.

**Available Tags** (SegmentTag enum values):
- Introduction: Opening, greetings, topic introduction
- Background: Context, prior knowledge, prerequisites  
- Methodology: Methods, approaches, techniques explained
- Implementation: Code, setup, step-by-step instructions
- Example: Demonstrations, case studies, examples
- Experiment: Tests, trials, experiments
- Results: Findings, outcomes, data presentation
- Discussion: Analysis, interpretation, implications
- Comparison: Contrasting options, pros/cons
- Problem: Challenges, issues, pain points
- Solution: Fixes, answers, resolutions
- Tips: Best practices, recommendations
- Conclusion: Summary, wrap-up, final thoughts
- QA: Questions and answers section
- Other: Content that doesn't fit other categories

{format_instructions}

**Rules**:
1. Group related consecutive lines into one segment (typically 3-15 lines)
2. Choose the SINGLE most appropriate tag per segment
3. Preserve chronological order
4. Extract timestamp_start from first line, timestamp_end from last line of each segment
5. Write a brief summary (1-2 sentences) for each segment
6. Keep original transcript lines intact in the "lines" array"""),
            ("human", """Segment and tag this transcript:

{transcript}""")
        ])
        
        chain = prompt | self.llm | parser
        
        print(f"[LLM] 开始异步段落切分与标签 (Extraction Agent)...", flush=True)
        
        result = await chain.ainvoke({
            "transcript": transcript_text,
            "format_instructions": parser.get_format_instructions()
        })
        
        print(f"[LLM] 异步段落切分完成，共 {len(result.segments)} 个段落", flush=True)
        
        return result
    
    def _format_segmented_transcript(self, segmented: SegmentedTranscript) -> str:
        """
        将结构化的段落切分结果格式化为文本，供后续分析使用
        
        Args:
            segmented: 结构化的段落切分结果
            
        Returns:
            str: 格式化后的带标签文本
        """
        formatted_parts = []
        for seg in segmented.segments:
            lines_text = "\n".join(seg.lines)
            part = f"""#{seg.tag.value}
[{seg.timestamp_start} - {seg.timestamp_end}]
Summary: {seg.summary}

{lines_text}
"""
            formatted_parts.append(part)
        
        return "\n---\n".join(formatted_parts)

    def _denoise_transcript(self, formatted_text: str) -> str:
        """
        降噪层：清理格式化后的转录文本
        
        功能:
        1. 删除陈词滥调 (clichés)，如 "In this video...", "It is important to note..."
        2. 将被动语态改为主动语态
        3. 删除冗余填充词
        
        Args:
            formatted_text: 格式化后的带标签转录文本
            
        Returns:
            str: 降噪后的文本
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a text editor specializing in concise, clear writing. 
Clean up the transcript while preserving ALL timestamps and structure.

**REMOVE these clichés and filler phrases**:
- "In this video..."
- "As you can see..."
- "It is important to note that..."
- "Let me explain..."
- "What I want to talk about is..."
- "Basically...", "Actually...", "You know..."
- "So...", "Well...", "Okay so..."
- "I think that...", "I believe that..."
- "As I mentioned earlier..."
- "Without further ado..."
- "Before we get started..."
- "Don't forget to like and subscribe..."
- "Thanks for watching..."
- Generic greetings and outros

**CONVERT passive voice to active voice**:
- "The model was trained by researchers" → "Researchers trained the model"
- "It was discovered that..." → "They discovered..."
- "The data is processed" → "The system processes the data"

**RULES**:
1. KEEP all timestamps [HH:MM:SS] exactly as they are
2. KEEP all #Tags and structure (---, Summary:, etc.)
3. KEEP technical content and key information
4. Only clean up the transcript lines, not the metadata
5. If a line becomes empty after cleaning, remove it entirely
6. Output the cleaned transcript only, no explanations"""),
            ("human", """{text}""")
        ])
        
        chain = prompt | self.llm_lite | StrOutputParser()
        
        print(f"[LLM] 开始降噪处理...", flush=True)
        
        result = chain.invoke({
            "text": formatted_text
        })
        
        print(f"[LLM] 降噪完成，原长度: {len(formatted_text)}, 新长度: {len(result)}", flush=True)
        
        return result

    
    async def _generate_key_takeaways_image(self, full_response: str, video_id: str = None, save_to_db: bool = True) -> Optional[str]:
        """
        从分析结果中提取 Key Takeaways 并使用 OpenRouter (Nano Banana Pro) 生成手绘风格简报图像
        
        Args:
            full_response: LLM 生成的完整 JSON 响应文本
            video_id: 视频 ID（可选，用于保存到数据库）
            save_to_db: 是否保存到数据库（默认 True，失败时不会保存）
            
        Returns:
            str: 生成的图像 URL，如果失败则返回 None
        """
        if not KEY_TAKEAWAYS_IMAGE_ENABLED:
            print(
                "[Key Takeaways Image] ⏸️ 功能已禁用 (ENABLE_KEY_TAKEAWAYS_IMAGE=false)，跳过图像生成",
                flush=True,
            )
            return None
        
        def _save_image_status(status: str, image_url: str = '', error_message: str = ''):
            """保存图像生成状态到数据库（仅保存成功状态，失败时不保存）"""
            # 如果 save_to_db=False，不保存
            if not save_to_db:
                print(f"[Key Takeaways Image] ⚠️ save_to_db=False，跳过保存到数据库", flush=True)
                return
            
            # 只在成功时保存，失败时不保存到数据库
            if status != 'completed':
                print(f"[Key Takeaways Image] ⚠️ 状态为 {status}，跳过保存到数据库", flush=True)
                return
                
            if not video_id:
                print(f"[Key Takeaways Image] ⚠️ 未提供 video_id，跳过保存", flush=True)
                return
            try:
                supabase_url, supabase_key = get_supabase_config(prefer_service_role=True)
                # 检查是否使用了 SERVICE_ROLE_KEY（仅日志用途）
                is_service_role = 'SUPABASE_SERVICE_ROLE_KEY' in os.environ or 'service_role' in supabase_key.lower() or supabase_key.startswith("sb_secret_")
                if not is_service_role:
                    print(f"[Key Takeaways Image] ⚠️ 使用 anon key，可能因 RLS 策略无法写入", flush=True)
                
                print(f"[Key Takeaways Image] 💾 开始保存状态到数据库: video_id={video_id}, status={status}, image_url={'已设置' if image_url else '未设置'}, key_type={'SERVICE_ROLE' if is_service_role else 'ANON'}", flush=True)
                client = get_supabase_client(prefer_service_role=True)
                result = client.table('key_takeaways_images').upsert({
                    'video_id': video_id,
                    'image_url': image_url,
                    'status': status,
                    'error_message': error_message[:500] if error_message else ''
                }).execute()
                
                if result.data:
                    print(f"[Key Takeaways Image] ✅ 状态已保存到 key_takeaways_images 表: {status}, image_url={image_url[:50] if image_url else 'N/A'}...", flush=True)
                else:
                    print(f"[Key Takeaways Image] ⚠️ 保存返回空数据", flush=True)
            except Exception as e:
                import traceback
                print(f"[Key Takeaways Image] ❌ 保存状态失败: {e}", flush=True)
                print(f"[Key Takeaways Image] 错误详情: {traceback.format_exc()}", flush=True)
        
        try:
            # 提取 Key Takeaways
            json_data = self._extract_json(full_response)
            if not json_data or not isinstance(json_data, dict):
                print(f"[Key Takeaways Image] ⚠️ 无法解析 JSON 或格式错误", flush=True)
                _save_image_status('failed', error_message='无法解析 JSON 或格式错误')
                return None
                
            summary_box = json_data.get('summary_box', {})
            bullet_points = summary_box.get('bullet_points', [])
            
            if not bullet_points or not isinstance(bullet_points, list):
                print(f"[Key Takeaways Image] ⚠️ 未找到有效的 Key Takeaways", flush=True)
                _save_image_status('failed', error_message='未找到有效的 Key Takeaways')
                return None
            
            # 将 Key Takeaways 组合成文本
            key_takeaways_text = "\n".join([f"• {point}" for point in bullet_points])
            
            print(f"[Key Takeaways Image] 📝 提取到 {len(bullet_points)} 个 Key Takeaways", flush=True)
            
            # 使用 LLM 生成图像提示词
            system_prompt = """# ROLE: Advanced Technical Information Designer & Scientific Illustrator

# GOAL:
You are an expert in translating complex textual information, data, and processes into precise, high-fidelity technical diagrams and infographics. Your output must synthesize the aesthetic qualities found in scientific illustrations, engineering blueprints, and complex process flowcharts (as seen in reference images image_0.png, image_1.png, and image_2.png).

# CORE TASK:
When provided with a user's text description, your job is to analyze the information structure and visualize it accurately using the specific aesthetic guidelines below. Do not generate photorealistic scenes; generate analytical diagrams.

# AESTHETIC GUIDELINES & CONSTRAINTS:

1.  **Background Color (MANDATORY):**
    The background MUST be a solid, off-white color with the specific RGB value of (250, 249, 245).

2.  **Perspective & Structure:**
    * Prioritize **isometric** or **axonometric** projections to show depth and structure cleanly.
    * Use **exploded views** (like image_0.png) when showing layers, composition, or internal hierarchies.
    * Use **structured flowcharts** with clear directional pathways, pipes, or connector lines (like image_1.png and image_2.png) when showing processes, life cycles, or systems.

3.  **Visual Elements & Style:**
    * **Line Work:** Clean, precise vector-style lines.
    * **Materials:** Use representations of translucent membranes, wireframe meshes, glass-like spheres, and solid geometric blocks to represent components.
    * **Abstraction:** Translate real-world objects into technical icons (e.g., molecules as spheres, machinery as geometric blocks, flow as arrows).
    * **Clarity:** Ensure high visual hierarchy. The diagram should feel clinical, engineered, and analytical.

4.  **Annotations & Text Integration:**
    * The image must include clear labels, annotations, and call-outs pointing to relevant parts of the diagram with thin lead lines.
    * If the input text includes data or percentages, integrate them visually (e.g., next to icons or within flow lines, similar to image_2.png).
    * Include a main title if appropriate to the text.

# EXECUTION PROCESS:

1.  **Analyze Input:** Deconstruct the user's text into key components, steps, relationships, and data points.
2.  **Determine Structure:** Decide the best visualization method (e.g., "Is this a layered structure diagram?" or "Is this a linear process flowchart?").
3.  **Visual Synthesis:** Render the components using the specified aesthetic guidelines, ensuring all connections and flows are logical based on the text.
4.  **Annotate:** Add precise labels derived from the text to explain the visual elements."""

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "Key Takeaways:\n{key_takeaways}")
            ])
            
            chain = prompt | self.llm_lite | StrOutputParser()
            image_prompt = await chain.ainvoke({
                "key_takeaways": key_takeaways_text
            })
            
            # 使用 OpenRouter 生成图像
            try:
                from openai import OpenAI
                
                openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
                if not openrouter_api_key:
                    print(f"[Key Takeaways Image] ⚠️ OPENROUTER_API_KEY 未设置", flush=True)
                    return None
                
                client = OpenAI(
                    base_url=OPENROUTER_BASE_URL,
                    api_key=openrouter_api_key,
                )
                
                # 在后台线程中运行以避免阻塞
                import asyncio
                loop = asyncio.get_event_loop()
                
                def run_openrouter_image():
                    return client.chat.completions.create(
                        model=IMAGE_MODEL,
                        messages=[
                            {"role": "user", "content": image_prompt}
                        ],
                        extra_body={
                            "modalities": ["image", "text"]
                        }
                    )
                
                response = await loop.run_in_executor(None, run_openrouter_image)
                
                if response and response.choices:
                    message = response.choices[0].message
                    content = message.content or ""
                    
                    image_url = None
                    
                    # 1. 尝试从内容中提取 URL
                    import re
                    url_match = re.search(r'(?:!\[.*?\]\((https?://[^\s)]+)\))|(https?://[^\s)]+)', content)
                    if url_match:
                        image_url = url_match.group(1) or url_match.group(2)
                        
                    # 2. 尝试从 'images' 字段提取
                    if not image_url:
                        try:
                            message_dict = message.model_dump() if hasattr(message, 'model_dump') else message.dict()
                            if 'images' in message_dict and message_dict['images']:
                                first_image = message_dict['images'][0]
                                if isinstance(first_image, dict):
                                    if 'image_url' in first_image and isinstance(first_image['image_url'], dict):
                                        image_url = first_image['image_url'].get('url')
                                    elif 'url' in first_image:
                                        image_url = first_image.get('url')
                        except Exception:
                            pass

                    if image_url:
                        _save_image_status('completed', image_url=image_url)
                        return image_url
                    else:
                        print(f"[Key Takeaways Image] ⚠️ 未找到图像 URL", flush=True)
                        _save_image_status('failed', error_message='未找到图像 URL')
                        return None
                else:
                    print(f"[Key Takeaways Image] ⚠️ 图像生成返回为空", flush=True)
                    _save_image_status('failed', error_message='图像生成返回为空')
                    return None
                    
            except ImportError:
                print(f"[Key Takeaways Image] ⚠️ openai 库未安装", flush=True)
                _save_image_status('failed', error_message='openai 库未安装')
                return None
            except Exception as e:
                print(f"[Key Takeaways Image] ❌ 图像生成失败: {e}", flush=True)
                _save_image_status('failed', error_message=str(e))
                return None
            
        except Exception as e:
            print(f"[Key Takeaways Image] ❌ 生成图像时出错: {e}", flush=True)
            _save_image_status('failed', error_message=str(e))
            return None
    
    def _extract_json(self, text: str):
        """从文本中提取 JSON（支持对象和数组）"""
        import json
        import re
        
        if not text or not text.strip():
            print(f"[_extract_json] ⚠️ 输入文本为空")
            return None
        
        # 清理 markdown 代码块
        text = text.strip()
        text = re.sub(r'^```json?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
        text = text.strip()
        
        # 检测是对象还是数组
        obj_start = text.find('{')
        arr_start = text.find('[')
        
        # 判断哪个先出现
        if arr_start != -1 and (obj_start == -1 or arr_start < obj_start):
            # 数组格式
            start = arr_start
            end = text.rfind(']')
            if end == -1 or end < start:
                print(f"[_extract_json] ⚠️ 数组格式：未找到有效的结束符 ']'")
                return None
        elif obj_start != -1:
            # 对象格式
            start = obj_start
            end = text.rfind('}')
            if end == -1 or end < start:
                print(f"[_extract_json] ⚠️ 对象格式：未找到有效的结束符 '}}'")
                return None
        else:
            print(f"[_extract_json] ⚠️ 未找到 JSON 起始符, 文本前200字符: {text[:200]}")
            return None
        
        json_str = text[start:end+1]
        if not json_str or len(json_str) < 2:
            print(f"[_extract_json] ⚠️ 提取的 JSON 字符串过短: '{json_str}'")
            return None
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[_extract_json] ❌ JSON 解析失败: {e}")
            print(f"[_extract_json] 📝 JSON 字符串长度: {len(json_str)}, 前200字符: {json_str[:200]}")
            print(f"[_extract_json] 📝 JSON 字符串后100字符: ...{json_str[-100:]}")
            return None
    
    def save_key_takeaways_image_status(self, video_id: str, status: str, image_url: str = '', error_message: str = ''):
        """
        保存 Key Takeaways 图像生成状态到数据库（仅保存成功状态）
        
        Args:
            video_id: 视频 ID
            status: 状态 ('completed' 或 'failed')
            image_url: 图像 URL（仅 status='completed' 时需要）
            error_message: 错误信息（仅 status='failed' 时需要）
        """
        # 只在成功时保存，失败时不保存到数据库
        if status != 'completed':
            print(f"[Key Takeaways Image] ⚠️ 状态为 {status}，跳过保存到数据库", flush=True)
            return
        
        if not video_id:
            print(f"[Key Takeaways Image] ⚠️ 未提供 video_id，跳过保存", flush=True)
            return
        
        if not image_url:
            print(f"[Key Takeaways Image] ⚠️ 未提供 image_url，跳过保存", flush=True)
            return
        
        try:
            supabase_url, supabase_key = get_supabase_config(prefer_service_role=True)
            # 检查是否使用了 SERVICE_ROLE_KEY（仅日志用途）
            is_service_role = 'SUPABASE_SERVICE_ROLE_KEY' in os.environ or 'service_role' in supabase_key.lower() or supabase_key.startswith("sb_secret_")
            if not is_service_role:
                print(f"[Key Takeaways Image] ⚠️ 使用 anon key，可能因 RLS 策略无法写入", flush=True)
            
            print(f"[Key Takeaways Image] 💾 开始保存状态到数据库: video_id={video_id}, status={status}, image_url={'已设置' if image_url else '未设置'}, key_type={'SERVICE_ROLE' if is_service_role else 'ANON'}", flush=True)
            client = get_supabase_client(prefer_service_role=True)
            result = client.table('key_takeaways_images').upsert({
                'video_id': video_id,
                'image_url': image_url,
                'status': status,
                'error_message': error_message[:500] if error_message else ''
            }).execute()
            
            if result.data:
                print(f"[Key Takeaways Image] ✅ 状态已保存到 key_takeaways_images 表: {status}, image_url={image_url[:50] if image_url else 'N/A'}...", flush=True)
            else:
                print(f"[Key Takeaways Image] ⚠️ 保存返回空数据", flush=True)
        except Exception as e:
            import traceback
            print(f"[Key Takeaways Image] ❌ 保存状态失败: {e}", flush=True)
            print(f"[Key Takeaways Image] 错误详情: {traceback.format_exc()}", flush=True)


# ========= 全局单例 =========

_llm_service: Optional[LLMService] = None

def get_llm_service() -> LLMService:
    """获取 LLM 服务单例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
