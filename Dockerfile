FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY backend/python-fastapi/requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir supabase youtube-transcript-api google-api-python-client google-genai

# 复制整个项目
COPY . .

# 创建数据目录
RUN mkdir -p /app/data

# 设置工作目录
WORKDIR /app/backend/python-fastapi

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]

