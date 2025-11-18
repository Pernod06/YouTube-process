#!/bin/bash
# YouTube API 客户端安装脚本

echo "=================================="
echo "YouTube API 客户端安装脚本"
echo "=================================="
echo ""

# 检查Python
echo "检查Python安装..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✓ 找到Python: $PYTHON_VERSION"
else
    echo "✗ 未找到Python3，请先安装Python3"
    exit 1
fi

# 安装pip（如果需要）
echo ""
echo "检查pip安装..."
if python3 -m pip --version &> /dev/null; then
    echo "✓ pip已安装"
else
    echo "正在安装pip..."
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python3 get-pip.py --user
    rm get-pip.py
    echo "✓ pip安装完成"
fi

# 安装依赖
echo ""
echo "安装Python依赖包..."
python3 -m pip install --user -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "=================================="
    echo "✓ 安装完成！"
    echo "=================================="
    echo ""
    echo "下一步："
    echo "1. 运行测试: python3 test_connection.py"
    echo "2. 查看示例: python3 youtube_client.py"
    echo ""
else
    echo "✗ 安装失败，请检查错误信息"
    exit 1
fi

