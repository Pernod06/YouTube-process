"""
配置管理模块
用于管理YouTube API密钥和其他配置
"""

import os

# YouTube API配置
# 方式1: 直接在这里设置（不推荐用于生产环境）
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# 方式2: 从环境变量读取（推荐）
# 如果设置了环境变量，优先使用环境变量
if os.getenv('YOUTUBE_API_KEY'):
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# API配置
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# 默认配置
DEFAULT_MAX_RESULTS = 10
DEFAULT_MAX_COMMENTS = 20

