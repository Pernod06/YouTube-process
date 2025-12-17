"""
配置管理模块
用于管理YouTube API密钥和其他配置
"""

import os
from pathlib import Path

# 尝试加载 .env 文件（如果存在）
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(dotenv_path=env_path)
    print(f"[Config] .env 文件已加载: {env_path}")
except ImportError:
    print("[Config] python-dotenv 未安装，使用系统环境变量")

# YouTube API配置
# 从 .env 文件或系统环境变量读取
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == 'YOUR_API_KEY_HERE':
    print("[WARNING] YouTube API 密钥未配置！")
    print("[提示] 请在 .env 文件中设置: YOUTUBE_API_KEY=你的密钥")
else:
    print(f"[Config] YouTube API 密钥已加载（长度: {len(YOUTUBE_API_KEY)}）")

# SerpAPI 配置（用于 YouTube 搜索）
SERP_API_KEY = os.getenv('SERP_API_KEY')

if not SERP_API_KEY or SERP_API_KEY == 'YOUR_SERP_API_KEY_HERE':
    print("[WARNING] SERP API 密钥未配置！")
    print("[提示] 请在 .env 文件中设置: SERP_API_KEY=你的密钥")
else:
    print(f"[Config] SERP API 密钥已加载（长度: {len(SERP_API_KEY)}）")

# API配置
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

# 默认配置
DEFAULT_MAX_RESULTS = 10
DEFAULT_MAX_COMMENTS = 20

