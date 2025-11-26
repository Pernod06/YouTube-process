# FastAPI 后端服务

这是从 Flask 迁移到 FastAPI 的视频处理后端服务。

## 功能特性

### 已迁移的所有功能

✅ **基础功能**
- 视频数据获取 (`GET /api/videos/{video_id}`)
- 视频列表 (`GET /api/videos`)
- 健康检查 (`GET /api/health`)

✅ **评论系统**
- 获取 YouTube 评论 (`GET /api/videos/{video_id}/comments`)
- 发布评论 (`POST /api/videos/{video_id}/comments`)

✅ **播放进度**
- 获取播放进度 (`GET /api/videos/{video_id}/progress`)
- 更新播放进度 (`PUT /api/videos/{video_id}/progress`)

✅ **搜索功能**
- 内容搜索 (`GET /api/search?q=关键词`)

✅ **AI 功能**
- LLM 聊天接口 (`POST /api/chat`)
- 生成思维导图 (`GET /api/generate-mindmap`)

✅ **视频处理**
- 获取视频帧 (`GET /api/video-frame/{video_id}?timestamp=秒`)
- 批量获取视频帧 (`POST /api/video-frames/{video_id}`)
- 获取视频章节 (`GET /api/video-chapters/{video_id}`)
- 获取视频信息 (`GET /api/video-info/{video_id}`)

✅ **文档生成**
- 生成 PDF 文档 (`GET /api/generate-pdf`)

## 安装依赖

```bash
cd /root/pernod/youtube-process/backend/python-fastapi
pip install -r requirements.txt
```

## 环境配置

确保在项目根目录有 `.env` 文件，包含以下配置：

```bash
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# YouTube API Key (可选)
YOUTUBE_API_KEY=your_youtube_api_key_here
```

## 启动服务

```bash
# 开发模式
python main.py

# 或使用 uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 访问服务

- **主页**: http://localhost:8000
- **API 端点**: http://localhost:8000/api
- **API 文档 (Swagger)**: http://localhost:8000/docs
- **API 文档 (ReDoc)**: http://localhost:8000/redoc

## 与 Flask 版本的差异

### 优势
1. **自动 API 文档**: FastAPI 自动生成交互式 API 文档 (`/docs`)
2. **类型安全**: 使用 Pydantic 模型进行请求/响应验证
3. **更高性能**: 基于 ASGI，支持异步处理
4. **现代化**: 使用 Python 类型提示，代码更清晰

### 兼容性
- 所有 API 端点完全兼容 Flask 版本
- 相同的响应格式
- 相同的错误处理

## 文件结构

```
python-fastapi/
├── main.py                    # FastAPI 主应用
├── video_frame_extractor.py   # 视频帧提取模块
├── pdf_generator.py           # PDF 生成模块
├── requirements.txt           # 依赖包列表
└── README.md                  # 本文档
```

## 开发说明

### 添加新的 API 端点

```python
@app.get("/api/new-endpoint")
async def new_endpoint():
    """端点描述"""
    return {"message": "Hello World"}
```

### 使用 Pydantic 模型

```python
class MyRequest(BaseModel):
    field1: str
    field2: int

@app.post("/api/endpoint")
async def endpoint(request: MyRequest):
    return {"received": request.field1}
```

## 迁移说明

从 Flask (`backend/python/app.py`) 迁移的所有功能：

1. ✅ 路由定义 (Flask → FastAPI decorator)
2. ✅ CORS 配置 (flask-cors → CORSMiddleware)
3. ✅ 静态文件服务 (send_from_directory → StaticFiles)
4. ✅ JSON 响应 (jsonify → FastAPI 自动处理)
5. ✅ 错误处理 (Flask errorhandler → HTTPException)
6. ✅ 文件下载 (send_file → StreamingResponse/FileResponse)
7. ✅ 环境变量加载 (python-dotenv)
8. ✅ OpenAI 集成
9. ✅ YouTube API 集成
10. ✅ PDF 生成
11. ✅ 视频帧提取

## 性能对比

FastAPI vs Flask:
- 🚀 更快的请求处理 (异步支持)
- 📊 更低的内存占用
- 🔒 自动数据验证
- 📚 内置 API 文档

## 故障排查

### 常见问题

1. **ModuleNotFoundError: No module named 'xxx'**
   - 解决: `pip install -r requirements.txt`

2. **OPENAI_API_KEY 未配置**
   - 解决: 在 `.env` 文件中设置 `OPENAI_API_KEY`

3. **静态文件 404 错误**
   - 解决: 确保 `css/`, `js/`, `data/` 目录存在于项目根目录

4. **YouTube API 错误**
   - 解决: 检查 `youtube_client.py` 是否存在于项目根目录

## 许可

与项目主体保持一致

