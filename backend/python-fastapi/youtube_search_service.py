"""
YouTube 搜索服务 - 使用 SerpAPI

功能：
- 通过 SerpAPI 搜索 YouTube 视频
- 10分钟缓存机制
- 错误处理
"""

import os
import hashlib
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

import httpx
from cachetools import TTLCache
from pydantic import BaseModel

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass


class YouTubeVideoResult(BaseModel):
    """YouTube 视频搜索结果模型"""
    position: Optional[int] = None
    title: str
    link: str
    thumbnail: Optional[Dict[str, Any]] = None
    channel: Optional[Dict[str, Any]] = None
    published_date: Optional[str] = None
    views: Optional[int] = None
    length: Optional[str] = None
    description: Optional[str] = None


class YouTubeSearchResponse(BaseModel):
    """YouTube 搜索响应模型"""
    video_results: List[Dict[str, Any]]
    search_metadata: Optional[Dict[str, Any]] = None
    search_parameters: Optional[Dict[str, Any]] = None


class SearchYouTubeParams(BaseModel):
    """YouTube 搜索参数"""
    search_query: str
    engine: str = "youtube"
    # 可选参数
    gl: Optional[str] = None  # 国家/地区代码 (如 "us", "cn")
    hl: Optional[str] = None  # 语言代码 (如 "en", "zh")
    sp: Optional[str] = None  # 排序/过滤参数
    # 自定义过滤参数（后端过滤，非 SerpAPI 参数）
    duration: Optional[str] = None  # 视频时长: any, short(<20min), medium(20min-1hour), long(>1hour)
    limit: Optional[int] = None  # 返回结果数量限制


class YouTubeSearchError(Exception):
    """YouTube 搜索错误"""
    def __init__(self, message: str, cause: Optional[Exception] = None):
        self.message = message
        self.cause = cause
        super().__init__(self.message)


def hash_object(obj: dict) -> str:
    """
    计算对象的哈希值（用于缓存键）
    对应 NestJS 版本的 hashObject 函数
    """
    # 排序键以确保相同内容产生相同的哈希
    sorted_json = json.dumps(obj, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(sorted_json.encode('utf-8')).hexdigest()


def parse_duration_to_seconds(duration_str: str) -> int:
    """
    将时长字符串转换为秒数
    
    支持格式:
    - "1:30:45" (1小时30分45秒)
    - "25:30" (25分30秒)
    - "45" (45秒)
    
    Args:
        duration_str: 时长字符串
        
    Returns:
        秒数
    """
    if not duration_str:
        return 0
    
    try:
        parts = duration_str.split(':')
        if len(parts) == 3:
            # H:M:S
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            # M:S
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 1:
            # S
            return int(parts[0])
    except (ValueError, IndexError):
        pass
    
    return 0


# 自定义时长范围（秒）
DURATION_RANGES = {
    'short': (0, 1200),        # < 20 min
    'medium': (1200, 3600),    # 20 min - 1 hour
    'long': (3600, float('inf'))  # > 1 hour
}


class SearchYouTubeService:
    """
    YouTube 搜索服务
    对应 NestJS 的 SearchYouTubeService
    """
    
    # 缓存配置：最多 100 个条目，TTL 10 分钟
    _cache: TTLCache = TTLCache(maxsize=100, ttl=600)  # 600秒 = 10分钟
    
    def __init__(self):
        self._serp_api_key = os.getenv('SERP_API_KEY')
        if not self._serp_api_key:
            print("[WARNING] SERP_API_KEY 未配置！请在 .env 文件中设置")
    
    @property
    def serp_api_key(self) -> Optional[str]:
        """获取 SERP API 密钥"""
        return self._serp_api_key
    
    async def search_youtube(self, params: SearchYouTubeParams) -> YouTubeSearchResponse:
        """
        搜索 YouTube 视频
        
        Args:
            params: 搜索参数 (search_query, engine 等)
            
        Returns:
            YouTubeSearchResponse: 包含 video_results 的搜索结果
            
        Raises:
            YouTubeSearchError: 搜索失败时抛出
        """
        # 提取自定义过滤参数
        duration_filter = params.duration
        limit = params.limit or 50  # 默认获取更多结果以便过滤
        
        # 将 params 转为 dict 用于缓存键计算（包含过滤参数）
        params_dict = params.model_dump(exclude_none=True)
        cache_key = hash_object(params_dict)
        
        # 检查缓存
        if cache_key in self._cache:
            print(f"[YouTube Search] 缓存命中: {params.search_query[:30]}...")
            return self._cache[cache_key]
        
        # 构建请求参数（排除自定义过滤参数，这些不是 SerpAPI 参数）
        serp_params = {k: v for k, v in params_dict.items() if k not in ['duration', 'limit']}
        serp_params['api_key'] = self.serp_api_key
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    'https://serpapi.com/search',
                    params=serp_params
                )
                response.raise_for_status()
                data = response.json()
                
                video_results = data.get('video_results', [])
                
                # 应用时长过滤
                if duration_filter and duration_filter != 'any' and duration_filter in DURATION_RANGES:
                    min_seconds, max_seconds = DURATION_RANGES[duration_filter]
                    filtered_results = []
                    
                    for video in video_results:
                        # SerpAPI 返回的 length 字段格式如 "1:30:45" 或 "25:30"
                        length_str = video.get('length', '')
                        video_seconds = parse_duration_to_seconds(length_str)
                        
                        if min_seconds <= video_seconds < max_seconds:
                            filtered_results.append(video)
                    
                    print(f"[YouTube Search] 时长过滤 ({duration_filter}): {len(video_results)} -> {len(filtered_results)}")
                    video_results = filtered_results
                
                # 应用数量限制
                if limit and len(video_results) > limit:
                    video_results = video_results[:limit]
                
                # 构建响应对象
                result = YouTubeSearchResponse(
                    video_results=video_results,
                    search_metadata=data.get('search_metadata'),
                    search_parameters=data.get('search_parameters')
                )
                
                # 存入缓存
                self._cache[cache_key] = result
                print(f"[YouTube Search] 搜索成功: {params.search_query[:30]}..., 结果数: {len(result.video_results)}")
                
                return result
                
        except httpx.HTTPStatusError as e:
            error_msg = "Unknown error"
            try:
                error_data = e.response.json()
                error_msg = error_data.get('error', str(e))
            except:
                error_msg = e.response.text or str(e)
            
            print(f"[YouTube Search] HTTP 错误: {error_msg}")
            raise YouTubeSearchError(
                message=f"搜索 YouTube 视频失败: {error_msg}",
                cause=e
            )
        except httpx.RequestError as e:
            print(f"[YouTube Search] 请求错误: {e}")
            raise YouTubeSearchError(
                message=f"搜索请求失败: {str(e)}",
                cause=e
            )
        except Exception as e:
            print(f"[YouTube Search] 未知错误: {e}")
            raise YouTubeSearchError(
                message=f"搜索失败: {str(e)}",
                cause=e
            )
    
    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        print("[YouTube Search] 缓存已清空")
    
    def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        return {
            'size': len(self._cache),
            'maxsize': self._cache.maxsize,
            'ttl': self._cache.ttl
        }


# 全局单例实例
_youtube_search_service: Optional[SearchYouTubeService] = None


def get_youtube_search_service() -> SearchYouTubeService:
    """获取 YouTube 搜索服务单例"""
    global _youtube_search_service
    if _youtube_search_service is None:
        _youtube_search_service = SearchYouTubeService()
    return _youtube_search_service


# 便捷函数
async def search_youtube_videos(
    query: str,
    gl: Optional[str] = None,
    hl: Optional[str] = None,
    duration: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    便捷函数：搜索 YouTube 视频
    
    Args:
        query: 搜索关键词
        gl: 国家/地区代码
        hl: 语言代码
        duration: 视频时长过滤 (any, short, medium, long)
            - short: < 20 min
            - medium: 20 min - 1 hour
            - long: > 1 hour
        limit: 返回结果数量限制
        
    Returns:
        视频结果列表
    """
    service = get_youtube_search_service()
    params = SearchYouTubeParams(
        search_query=query,
        engine="youtube",
        gl=gl,
        hl=hl,
        duration=duration,
        limit=limit
    )
    response = await service.search_youtube(params)
    return response.video_results

