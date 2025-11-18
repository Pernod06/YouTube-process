#!/bin/bash

# 开发环境启动脚本

echo "🚀 启动 YouTube 视频处理应用"
echo "================================"
echo ""

# 检查是否有端口参数
PORT=${1:-8000}

# 检查Python是否安装
if command -v python3 &> /dev/null; then
    echo "✅ 使用 Python 3 启动 HTTP 服务器"
    echo "📡 服务器地址: http://localhost:$PORT"
    echo "📄 访问页面: http://localhost:$PORT/video_page_dynamic.html"
    echo ""
    echo "按 Ctrl+C 停止服务器"
    echo ""
    python3 -m http.server $PORT
elif command -v python &> /dev/null; then
    echo "✅ 使用 Python 2 启动 HTTP 服务器"
    echo "📡 服务器地址: http://localhost:$PORT"
    echo "📄 访问页面: http://localhost:$PORT/video_page_dynamic.html"
    echo ""
    echo "按 Ctrl+C 停止服务器"
    echo ""
    python -m SimpleHTTPServer $PORT
else
    echo "❌ 未找到 Python，请安装 Python 或使用其他方式启动服务器"
    echo ""
    echo "其他选择："
    echo "1. 安装 Node.js 后运行: npx http-server -p $PORT"
    echo "2. 直接在浏览器中打开 video_page_dynamic.html（可能有CORS限制）"
fi

