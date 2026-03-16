# YouTube Process

`YouTube-process` 是 PageOn 视频分析体系的后端和脚本仓库。它负责拉取字幕与视频信息、调用 LLM 生成结构化文章、提供搜索与聊天接口、输出 PDF/图片，并把结果缓存到 Supabase。

前端仓库是同级目录下的 `../PageOn_video_web`。这两个仓库通常一起使用。

## 仓库包含什么

- FastAPI 服务：对外提供 `/api/*` 接口
- YouTube 处理脚本：字幕提取、HTML 生成、数据导入
- LLM 分析链路：结构化文章、聊天、翻译、图片摘要
- Supabase 缓存与用户数据读写
- 静态页面与样式资源，便于独立调试

## 主要能力

- 根据 YouTube URL 提取视频 ID、字幕和视频元数据
- 用 LLM 生成 V2 结构化文章数据
- 支持流式分析输出，供前端结果页实时消费
- 基于 SerpAPI 搜索 YouTube，并带缓存与时长过滤
- 提供聊天、翻译、PDF 导出、章节缩略图、视频帧提取
- 将分析结果缓存到 Supabase，减少重复处理

## 目录概览

```text
YouTube-process/
├── backend/python-fastapi/     # 主后端服务
├── backend/nodejs/             # 旧 Node 示例
├── backend/python/             # 旧 Flask 示例
├── data/                       # 已生成的数据
├── tmp_data/                   # 临时处理数据
├── logs/                       # 后端日志
├── css/ js/ index.html         # 静态调试页面
├── get_full_transcript_ytdlp.py
├── generate_video_page.py
├── import_to_supabase.py
└── docker-compose.yml
```

## 环境变量

建议在仓库根目录放 `.env`。常用变量如下：

```bash
# LLM
OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL_MAIN=gemini-3-flash-preview
OPENROUTER_MODEL_LITE=gemini-2.5-flash
OPENROUTER_MODEL_IMAGE=gemini-3-pro-image-preview

# YouTube / 搜索
YOUTUBE_API_KEY=
SERP_API_KEY=
TranscriptAPI_KEY=

# Supabase
SUPABASE_URL=
SUPABASE_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# 运行开关
USE_HTTPS=false
ENABLE_KEY_TAKEAWAYS_IMAGE=true
```

说明：

- `OPENROUTER_API_KEY`：分析、聊天、翻译等 LLM 能力必需
- `SERP_API_KEY`：首页搜索视频必需
- `YOUTUBE_API_KEY`：补充视频详情、章节等能力建议配置
- `SUPABASE_*`：缓存、用户行为记录、前后端联动建议配置
- `TranscriptAPI_KEY`：字幕抓取辅助能力可选

## 本地启动

### 1. 安装依赖

本仓库有历史依赖文件并存，按当前 Docker 和主服务代码，最稳妥的本地安装方式是：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/python-fastapi/requirements.txt
pip install supabase youtube-transcript-api google-api-python-client google-genai
```

### 2. 启动主服务

```bash
python backend/python-fastapi/main.py
```

默认地址：

- API: `http://localhost:5000/api`
- Docs: `http://localhost:5000/docs`

如果检测到证书且 `USE_HTTPS=true`，服务会改为：

- API: `https://localhost:5000/api`
- Docs: `https://localhost:5000/docs`

### 3. 联调前端

前端仓库 `../PageOn_video_web` 默认把 `/api` 代理到 `https://localhost:5000`。  
如果你这里跑的是 HTTP，请同步修改前端的 `VITE_BACKEND_TARGET`。

## Docker

```bash
docker compose up --build
```

默认端口：

- `5000:5000`

`docker-compose.yml` 会把 `data/` 和 `logs/` 挂进去，并读取根目录环境变量。

## 关键接口

最常用的一组接口：

- `POST /api/process-video`
- `POST /api/process-video/stream`
- `POST /api/search-youtube`
- `POST /api/chat`
- `POST /api/translate-themes`
- `GET /api/generate-pdf/{video_id}`
- `POST /api/generate-pdf/{video_id}`
- `GET /api/video-info/{video_id}`
- `GET /api/video-chapters/{video_id}`
- `GET /api/health`

## 常用脚本

根目录还保留了一些离线处理脚本：

- `get_full_transcript_ytdlp.py`：抓取完整字幕
- `generate_video_page.py`：生成带播放器和字幕的 HTML 页面
- `generate_video_page_thumbnail.py`：生成缩略图相关页面或数据
- `import_to_supabase.py`：把本地 `data/` 导入 Supabase

这些脚本多数属于历史工具链，主业务入口仍然是 `backend/python-fastapi/main.py`。

## 与前端的配合

典型开发顺序：

1. 在本仓库启动 FastAPI
2. 在 `../PageOn_video_web` 启动 Vite
3. 访问前端首页，用关键词搜索或直接分析 YouTube 链接

前端侧的搜索、分析、聊天、翻译、PDF、图片摘要都依赖这里的接口。

## 当前状态说明

- 仓库内同时保留了多套历史实现，当前主线是 `backend/python-fastapi/`
- 根目录脚本、旧 Node/Flask 示例和静态页面仍有参考价值，但不是主运行路径
- `README` 已按当前主服务和真实目录结构重写
