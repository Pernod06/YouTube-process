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

# 创建 SSL 目录
RUN mkdir -p /app/ssl

# 暴露端口
EXPOSE 5500

# 启动命令 - 使用 Python 启动以支持动态 HTTPS 检测
CMD ["python", "main.py"]

