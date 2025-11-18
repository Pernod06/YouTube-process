#!/bin/bash

# API 测试脚本
# 用法: ./test_api.sh [API_BASE_URL]

API_BASE="${1:-http://localhost:8000/api}"

echo "🧪 测试 API 端点: $API_BASE"
echo "================================"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 测试函数
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo ""
    echo "📍 测试: $description"
    echo "   $method $API_BASE$endpoint"
    
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X $method "$API_BASE$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X $method "$API_BASE$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "   ${GREEN}✓ 成功 (HTTP $http_code)${NC}"
        echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    else
        echo -e "   ${RED}✗ 失败 (HTTP $http_code)${NC}"
        echo "$body"
    fi
}

# 1. 健康检查
test_endpoint "GET" "/health" "" "健康检查"

# 2. 获取视频数据
test_endpoint "GET" "/videos/lQHK61IDFH4" "" "获取视频数据"

# 3. 获取视频列表
test_endpoint "GET" "/videos" "" "获取视频列表"

# 4. 搜索内容
test_endpoint "GET" "/search?q=NVIDIA" "" "搜索内容 (关键词: NVIDIA)"

# 5. 发布评论
test_endpoint "POST" "/videos/lQHK61IDFH4/comments" \
    '{"comment": "这是一个测试评论", "author": "测试用户"}' \
    "发布评论"

# 6. 获取评论
test_endpoint "GET" "/videos/lQHK61IDFH4/comments" "" "获取评论列表"

# 7. 更新播放进度
test_endpoint "PUT" "/videos/lQHK61IDFH4/progress" \
    '{"timestamp": 125.5}' \
    "更新播放进度"

# 8. 获取播放进度
test_endpoint "GET" "/videos/lQHK61IDFH4/progress" "" "获取播放进度"

echo ""
echo "================================"
echo "✅ 测试完成！"

