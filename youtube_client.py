"""
YouTube API Client
用于连接和操作YouTube API的客户端类
"""

import os
import re
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, List
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 导入配置
try:
    from config import YOUTUBE_API_KEY
except ImportError:
    YOUTUBE_API_KEY = None


class YouTubeClient:
    """YouTube API客户端类"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化YouTube客户端
        
        Args:
            api_key: YouTube API密钥。如果未提供，将从config.py或环境变量YOUTUBE_API_KEY中读取
        """
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY') or YOUTUBE_API_KEY
        
        if not self.api_key:
            raise ValueError("未找到YouTube API密钥。请在config.py中设置YOUTUBE_API_KEY或传入api_key参数")
        
        # 创建YouTube API服务
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        print("✓ YouTube API连接成功建立")
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """
        从YouTube URL中提取视频ID
        
        支持的URL格式：
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/v/VIDEO_ID
        
        Args:
            url: YouTube视频URL
            
        Returns:
            视频ID，如果无法提取则返回None
        """
        # 如果已经是视频ID（11个字符），直接返回
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url
        
        # 解析URL
        parsed_url = urlparse(url)
        
        # youtube.com/watch?v=VIDEO_ID
        if parsed_url.hostname in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
            if parsed_url.path == '/watch':
                query_params = parse_qs(parsed_url.query)
                return query_params.get('v', [None])[0]
            # youtube.com/embed/VIDEO_ID 或 youtube.com/v/VIDEO_ID
            elif parsed_url.path.startswith(('/embed/', '/v/')):
                return parsed_url.path.split('/')[2]
        
        # youtu.be/VIDEO_ID
        elif parsed_url.hostname == 'youtu.be':
            return parsed_url.path[1:]
        
        return None
    
    def get_video_by_url(self, url: str) -> Optional[Dict]:
        """
        通过URL获取视频详细信息
        
        Args:
            url: YouTube视频URL或视频ID
            
        Returns:
            视频详细信息字典
        """
        video_id = self.extract_video_id(url)
        
        if not video_id:
            print(f"无法从URL中提取视频ID: {url}")
            return None
        
        print(f"提取到视频ID: {video_id}")
        return self.get_video_details(video_id)
    
    def search_videos(self, query: str, max_results: int = 10, order: str = 'viewCount', 
                      published_after: str = None, duration: str = 'long') -> List[Dict]:
        """
        搜索视频（包含时长和观看量信息）
        
        Args:
            query: 搜索关键词
            max_results: 返回结果的最大数量
            order: 排序方式
                - 'relevance': 相关性
                - 'date': 发布日期（最新优先）
                - 'viewCount': 观看次数（最高优先，默认）
                - 'rating': 评分（最高优先）
                - 'title': 标题（字母顺序）
            published_after: 时间过滤
                - 'hour': 最近1小时
                - 'today': 最近24小时
                - 'week': 最近7天
                - 'month': 最近30天
                - 'year': 最近1年
                - 或 ISO 8601 格式日期 (如 '2024-01-01T00:00:00Z')
            duration: 视频时长过滤
                - 'any': 不过滤
                - 'short': 少于4分钟
                - 'medium': 4-20分钟
                - 'long': 超过20分钟（默认）
            
        Returns:
            视频列表（包含 duration 和 view_count）
        """
        try:
            from datetime import datetime, timedelta
            
            # 构建搜索参数
            search_params = {
                'q': query,
                'part': 'id,snippet',
                'maxResults': max_results,
                'type': 'video',
                'order': order
            }
            
            # 处理视频时长过滤
            if duration and duration != 'any':
                search_params['videoDuration'] = duration
            
            # 处理时间过滤
            if published_after:
                time_mapping = {
                    'hour': timedelta(hours=1),
                    'today': timedelta(days=1),
                    'week': timedelta(days=7),
                    'month': timedelta(days=30),
                    'year': timedelta(days=365)
                }
                
                if published_after in time_mapping:
                    after_date = datetime.utcnow() - time_mapping[published_after]
                    search_params['publishedAfter'] = after_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                elif 'T' in published_after:  # ISO 8601 格式
                    search_params['publishedAfter'] = published_after
            
            request = self.youtube.search().list(**search_params)
            response = request.execute()
            
            # 收集视频ID用于获取详细信息
            video_ids = []
            search_results = {}
            
            for item in response.get('items', []):
                video_id = item['id']['videoId']
                video_ids.append(video_id)
                # 提取缩略图信息
                thumbnails = item['snippet'].get('thumbnails', {})
                search_results[video_id] = {
                    'video_id': video_id,
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'channel_title': item['snippet']['channelTitle'],
                    'published_at': item['snippet']['publishedAt'],
                    'thumbnails': {
                        'default': thumbnails.get('default', {}).get('url'),
                        'medium': thumbnails.get('medium', {}).get('url'),
                        'high': thumbnails.get('high', {}).get('url'),
                        'standard': thumbnails.get('standard', {}).get('url'),
                        'maxres': thumbnails.get('maxres', {}).get('url')
                    }
                }
            
            # 获取视频详细信息（包括时长和观看量）
            if video_ids:
                details_request = self.youtube.videos().list(
                    part='contentDetails,statistics',
                    id=','.join(video_ids)
                )
                details_response = details_request.execute()
                
                for item in details_response.get('items', []):
                    video_id = item['id']
                    if video_id in search_results:
                        # 添加时长（ISO 8601 格式，如 PT1H2M3S）
                        iso_duration = item['contentDetails'].get('duration', '')
                        search_results[video_id]['duration'] = iso_duration
                        search_results[video_id]['duration_formatted'] = self._format_duration(iso_duration)
                        
                        # 添加统计信息
                        stats = item.get('statistics', {})
                        search_results[video_id]['view_count'] = int(stats.get('viewCount', 0))
                        search_results[video_id]['like_count'] = int(stats.get('likeCount', 0))
            
            # 按原始顺序返回结果
            videos = [search_results[vid] for vid in video_ids if vid in search_results]
            return videos
        
        except HttpError as e:
            print(f"发生HTTP错误: {e}")
            return []
    
    def _format_duration(self, iso_duration: str) -> str:
        """
        将 ISO 8601 时长格式转换为可读格式
        
        Args:
            iso_duration: ISO 8601 格式时长 (如 PT1H2M3S)
            
        Returns:
            可读格式时长 (如 1:02:03 或 2:03)
        """
        import re
        
        if not iso_duration:
            return ""
        
        # 解析 ISO 8601 时长格式
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, iso_duration)
        
        if not match:
            return iso_duration
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
    
    def get_video_details(self, video_id: str) -> Optional[Dict]:
        """
        获取视频详细信息
        
        Args:
            video_id: 视频ID
            
        Returns:
            视频详细信息字典
        """
        try:
            request = self.youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=video_id
            )
            response = request.execute()
            
            if not response.get('items'):
                print(f"未找到视频ID: {video_id}")
                return None
            
            item = response['items'][0]
            # 提取缩略图信息
            thumbnails = item['snippet'].get('thumbnails', {})
            video_details = {
                'video_id': video_id,
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'channel_title': item['snippet']['channelTitle'],
                'published_at': item['snippet']['publishedAt'],
                'duration': item['contentDetails']['duration'],
                'view_count': item['statistics'].get('viewCount', 0),
                'like_count': item['statistics'].get('likeCount', 0),
                'comment_count': item['statistics'].get('commentCount', 0),
                'thumbnails': {
                    'default': thumbnails.get('default', {}).get('url'),
                    'medium': thumbnails.get('medium', {}).get('url'),
                    'high': thumbnails.get('high', {}).get('url'),
                    'standard': thumbnails.get('standard', {}).get('url'),
                    'maxres': thumbnails.get('maxres', {}).get('url')
                }
            }
            
            return video_details
        
        except HttpError as e:
            print(f"发生HTTP错误: {e}")
            return None
    
    def get_video_comments(self, video_id: str, max_results: int = 20) -> List[Dict]:
        """
        获取视频评论
        
        Args:
            video_id: 视频ID
            max_results: 返回评论的最大数量
            
        Returns:
            评论列表
        """
        try:
            request = self.youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=max_results,
                textFormat='plainText'
            )
            response = request.execute()
            
            comments = []
            for item in response.get('items', []):
                comment_data = {
                    'author': item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                    'text': item['snippet']['topLevelComment']['snippet']['textDisplay'],
                    'like_count': item['snippet']['topLevelComment']['snippet']['likeCount'],
                    'published_at': item['snippet']['topLevelComment']['snippet']['publishedAt']
                }
                comments.append(comment_data)
            
            return comments
        
        except HttpError as e:
            print(f"发生HTTP错误: {e}")
            return []
    
    def get_channel_info(self, channel_id: str) -> Optional[Dict]:
        """
        获取频道信息
        
        Args:
            channel_id: 频道ID
            
        Returns:
            频道信息字典
        """
        try:
            request = self.youtube.channels().list(
                part='snippet,contentDetails,statistics',
                id=channel_id
            )
            response = request.execute()
            
            if not response.get('items'):
                print(f"未找到频道ID: {channel_id}")
                return None
            
            item = response['items'][0]
            channel_info = {
                'channel_id': channel_id,
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'subscriber_count': item['statistics'].get('subscriberCount', 0),
                'video_count': item['statistics'].get('videoCount', 0),
                'view_count': item['statistics'].get('viewCount', 0)
            }
            
            return channel_info
        
        except HttpError as e:
            print(f"发生HTTP错误: {e}")
            return None
    
    @staticmethod
    def get_thumbnail_url_by_quality(video_id: str, quality: str = 'maxresdefault') -> str:
        """
        通过质量等级直接构建YouTube缩略图URL（无需API调用）
        
        Args:
            video_id: 视频ID
            quality: 缩略图质量，可选值：
                    - 'maxresdefault': 1920x1080 (最高清，部分视频可能没有)
                    - 'sddefault': 640x480 (标清)
                    - 'hqdefault': 480x360 (高清)
                    - 'mqdefault': 320x180 (中等)
                    - 'default': 120x90 (默认)
                    - '0', '1', '2', '3': 特定帧的缩略图
        
        Returns:
            缩略图URL
            
        Example:
            >>> url = YouTubeClient.get_thumbnail_url_by_quality('dQw4w9WgXcQ', 'maxresdefault')
            >>> print(url)
            https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg
        """
        return f"https://img.youtube.com/vi/{video_id}/{quality}.jpg"
    
    @staticmethod
    def get_all_thumbnail_urls(video_id: str) -> Dict[str, str]:
        """
        获取视频所有可用质量的缩略图URL（无需API调用）
        
        Args:
            video_id: 视频ID
        
        Returns:
            包含所有质量等级缩略图URL的字典
        """
        qualities = {
            'maxresdefault': 'https://img.youtube.com/vi/{}/maxresdefault.jpg',
            'sddefault': 'https://img.youtube.com/vi/{}/sddefault.jpg',
            'hqdefault': 'https://img.youtube.com/vi/{}/hqdefault.jpg',
            'mqdefault': 'https://img.youtube.com/vi/{}/mqdefault.jpg',
            'default': 'https://img.youtube.com/vi/{}/default.jpg',
            'frame_0': 'https://img.youtube.com/vi/{}/0.jpg',
            'frame_1': 'https://img.youtube.com/vi/{}/1.jpg',
            'frame_2': 'https://img.youtube.com/vi/{}/2.jpg',
            'frame_3': 'https://img.youtube.com/vi/{}/3.jpg',
        }
        
        return {key: url.format(video_id) for key, url in qualities.items()}


def main():
    """示例使用"""
    try:
        # 创建YouTube客户端

        url = "https://www.youtube.com/watch?v=DxL2HoqLbyA&t"

        client = YouTubeClient()
        
        video_id = client.extract_video_id(url)

        
        
        # 示例1: 获取comments
        comments = client.get_video_comments(video_id, max_results=100)
        print(comments)
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    # main()

    client = YouTubeClient()
    Query = "Python 教程"
    
    results = client.search_videos(Query, max_results=10)
    print(results)

