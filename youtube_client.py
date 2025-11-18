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
    
    def search_videos(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        搜索视频
        
        Args:
            query: 搜索关键词
            max_results: 返回结果的最大数量
            
        Returns:
            视频列表
        """
        try:
            request = self.youtube.search().list(
                q=query,
                part='id,snippet',
                maxResults=max_results,
                type='video'
            )
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                # 提取缩略图信息
                thumbnails = item['snippet'].get('thumbnails', {})
                video_data = {
                    'video_id': item['id']['videoId'],
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
                videos.append(video_data)
            
            return videos
        
        except HttpError as e:
            print(f"发生HTTP错误: {e}")
            return []
    
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
        client = YouTubeClient()
        
        # 示例1: 搜索视频
        print("\n=== 搜索视频示例 ===")
        videos = client.search_videos("Python编程", max_results=5)
        for i, video in enumerate(videos, 1):
            print(f"{i}. {video['title']}")
            print(f"   频道: {video['channel_title']}")
            print(f"   视频ID: {video['video_id']}")
            print()
        
        # 示例2: 获取视频详情（如果搜索到了视频）
        if videos:
            print("\n=== 获取第一个视频的详细信息 ===")
            video_id = videos[0]['video_id']
            details = client.get_video_details(video_id)
            if details:
                print(f"标题: {details['title']}")
                print(f"观看次数: {details['view_count']}")
                print(f"点赞数: {details['like_count']}")
                print(f"评论数: {details['comment_count']}")
                print(f"\n缩略图URL:")
                print(f"  默认: {details['thumbnails']['default']}")
                print(f"  中等: {details['thumbnails']['medium']}")
                print(f"  高清: {details['thumbnails']['high']}")
                if details['thumbnails']['maxres']:
                    print(f"  最高清: {details['thumbnails']['maxres']}")
        
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main()

