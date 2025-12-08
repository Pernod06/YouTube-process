"""
Bilibili 视频信息获取客户端
基于 bilibili-api-python 库和 Bilibili Web API

安装依赖:
    pip install bilibili-api-python httpx

官方API文档参考:
    - bilibili-api-python: https://github.com/Nemo2011/bilibili-api
    - Bilibili开放平台: https://open.bilibili.com
"""

import re
import asyncio
import httpx
from typing import Optional, Dict, List
from urllib.parse import urlparse, parse_qs


class BilibiliClient:
    """Bilibili API客户端类"""
    
    # Bilibili Web API 基础URL
    BASE_URL = "https://api.bilibili.com"
    
    # 默认请求头（模拟浏览器访问，需要完整headers绑过反爬虫）
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Origin": "https://www.bilibili.com",
    }
    
    def __init__(self, sessdata: str = None):
        """
        初始化Bilibili客户端
        
        Args:
            sessdata: 可选的登录cookie SESSDATA，用于需要登录的API（如搜索）
                     获取方式: 登录B站后，在浏览器开发者工具-Application-Cookies中找到SESSDATA
        """
        cookies = {}
        if sessdata:
            cookies["SESSDATA"] = sessdata
        
        self.client = httpx.Client(
            headers=self.DEFAULT_HEADERS, 
            cookies=cookies,
            timeout=30.0
        )
        print("✓ Bilibili API客户端初始化成功")
    
    @staticmethod
    def extract_video_id(url: str) -> Dict[str, Optional[str]]:
        """
        从Bilibili URL中提取视频ID (BV号或AV号)
        
        支持的URL格式：
        - https://www.bilibili.com/video/BV1xx411c7mD
        - https://www.bilibili.com/video/av170001
        - https://b23.tv/BV1xx411c7mD
        - BV1xx411c7mD (直接BV号)
        - av170001 (直接AV号)
        
        Args:
            url: Bilibili视频URL或视频ID
            
        Returns:
            包含 bvid 和 aid 的字典
        """
        result = {"bvid": None, "aid": None}
        
        # 如果是BV号格式 (BV开头，后跟10-12个字符)
        bv_match = re.search(r'(BV[a-zA-Z0-9]{10,12})', url, re.IGNORECASE)
        if bv_match:
            result["bvid"] = bv_match.group(1)
            return result
        
        # 如果是AV号格式
        av_match = re.search(r'av(\d+)', url, re.IGNORECASE)
        if av_match:
            result["aid"] = av_match.group(1)
            return result
        
        return result
    
    def get_video_info(self, bvid: str = None, aid: str = None) -> Optional[Dict]:
        """
        获取视频基本信息
        
        API: https://api.bilibili.com/x/web-interface/view
        
        Args:
            bvid: 视频BV号
            aid: 视频AV号 (与bvid二选一)
            
        Returns:
            视频信息字典
        """
        url = f"{self.BASE_URL}/x/web-interface/view"
        params = {}
        
        if bvid:
            params["bvid"] = bvid
        elif aid:
            params["aid"] = aid
        else:
            print("错误: 必须提供 bvid 或 aid")
            return None
        
        try:
            response = self.client.get(url, params=params)
            data = response.json()
            
            if data["code"] != 0:
                print(f"API错误: {data.get('message', '未知错误')}")
                return None
            
            video_data = data["data"]
            
            # 提取关键信息
            result = {
                "bvid": video_data.get("bvid"),
                "aid": video_data.get("aid"),
                "title": video_data.get("title"),
                "description": video_data.get("desc"),
                "duration": video_data.get("duration"),  # 秒数
                "duration_formatted": self._format_duration(video_data.get("duration", 0)),
                "cover_url": video_data.get("pic"),  # 封面图
                "owner": {
                    "uid": video_data.get("owner", {}).get("mid"),
                    "name": video_data.get("owner", {}).get("name"),
                    "face": video_data.get("owner", {}).get("face"),  # 头像
                },
                "stats": {
                    "view": video_data.get("stat", {}).get("view"),  # 播放量
                    "danmaku": video_data.get("stat", {}).get("danmaku"),  # 弹幕数
                    "reply": video_data.get("stat", {}).get("reply"),  # 评论数
                    "favorite": video_data.get("stat", {}).get("favorite"),  # 收藏数
                    "coin": video_data.get("stat", {}).get("coin"),  # 投币数
                    "share": video_data.get("stat", {}).get("share"),  # 分享数
                    "like": video_data.get("stat", {}).get("like"),  # 点赞数
                },
                "pubdate": video_data.get("pubdate"),  # 发布时间戳
                "cid": video_data.get("cid"),  # 视频cid，用于获取弹幕等
                "pages": video_data.get("pages", []),  # 分P信息
                "raw_data": video_data,  # 原始数据
            }
            
            return result
            
        except Exception as e:
            print(f"请求错误: {e}")
            return None
    
    def get_video_by_url(self, url: str) -> Optional[Dict]:
        """
        通过URL获取视频信息
        
        Args:
            url: Bilibili视频URL
            
        Returns:
            视频信息字典
        """
        video_ids = self.extract_video_id(url)
        
        if video_ids["bvid"]:
            print(f"提取到BV号: {video_ids['bvid']}")
            return self.get_video_info(bvid=video_ids["bvid"])
        elif video_ids["aid"]:
            print(f"提取到AV号: av{video_ids['aid']}")
            return self.get_video_info(aid=video_ids["aid"])
        else:
            print(f"无法从URL中提取视频ID: {url}")
            return None
    
    def get_video_subtitle(self, bvid: str = None, aid: str = None, cid: int = None) -> List[Dict]:
        """
        获取视频字幕列表
        
        API: https://api.bilibili.com/x/player/v2
        
        Args:
            bvid: 视频BV号
            aid: 视频AV号
            cid: 视频cid (如果不提供会自动获取)
            
        Returns:
            字幕列表
        """
        # 如果没有cid，先获取视频信息
        if not cid:
            video_info = self.get_video_info(bvid=bvid, aid=aid)
            if not video_info:
                return []
            cid = video_info.get("cid")
            if not aid:
                aid = video_info.get("aid")
        
        url = f"{self.BASE_URL}/x/player/v2"
        params = {"cid": cid}
        
        if bvid:
            params["bvid"] = bvid
        elif aid:
            params["aid"] = aid
        
        try:
            response = self.client.get(url, params=params)
            data = response.json()
            
            if data["code"] != 0:
                print(f"获取字幕失败: {data.get('message', '未知错误')}")
                return []
            
            subtitles = data.get("data", {}).get("subtitle", {}).get("subtitles", [])
            return subtitles
            
        except Exception as e:
            print(f"请求错误: {e}")
            return []
    
    def download_subtitle(self, subtitle_url: str) -> Optional[Dict]:
        """
        下载字幕内容
        
        Args:
            subtitle_url: 字幕URL (从get_video_subtitle返回)
            
        Returns:
            字幕内容
        """
        try:
            # 字幕URL可能需要添加https前缀
            if subtitle_url.startswith("//"):
                subtitle_url = "https:" + subtitle_url
            
            response = self.client.get(subtitle_url)
            return response.json()
            
        except Exception as e:
            print(f"下载字幕失败: {e}")
            return None
    
    def get_danmaku(self, cid: int) -> Optional[str]:
        """
        获取弹幕数据 (XML格式)
        
        API: https://comment.bilibili.com/{cid}.xml
        
        Args:
            cid: 视频cid
            
        Returns:
            弹幕XML数据
        """
        url = f"https://comment.bilibili.com/{cid}.xml"
        
        try:
            response = self.client.get(url)
            response.encoding = 'utf-8'
            return response.text
            
        except Exception as e:
            print(f"获取弹幕失败: {e}")
            return None
    
    def search_videos(self, keyword: str, page: int = 1, page_size: int = 20, 
                      order: str = "totalrank") -> List[Dict]:
        """
        搜索视频
        
        API: https://api.bilibili.com/x/web-interface/search/type
        
        注意: 此API可能需要登录cookie才能正常使用，否则可能返回空结果或被拦截
        
        Args:
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量 (最大50)
            order: 排序方式
                - totalrank: 综合排序
                - click: 最多点击
                - pubdate: 最新发布
                - dm: 最多弹幕
                - stow: 最多收藏
                - scores: 最多评论
            
        Returns:
            视频列表
        """
        url = f"{self.BASE_URL}/x/web-interface/search/type"
        params = {
            "search_type": "video",
            "keyword": keyword,
            "page": page,
            "page_size": min(page_size, 50),
            "order": order,
        }
        
        try:
            response = self.client.get(url, params=params)
            
            # 检查响应状态和内容类型
            if response.status_code != 200:
                print(f"搜索请求失败，HTTP状态码: {response.status_code}")
                return []
            
            # 检查是否返回JSON
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type:
                print(f"搜索API返回非JSON响应 (可能需要登录cookie)")
                return []
            
            data = response.json()
            
            if data["code"] != 0:
                print(f"搜索失败: {data.get('message', '未知错误')}")
                return []
            
            results = []
            for item in data.get("data", {}).get("result", []):
                results.append({
                    "bvid": item.get("bvid"),
                    "aid": item.get("aid"),
                    "title": self._clean_html(item.get("title", "")),
                    "description": item.get("description"),
                    "author": item.get("author"),
                    "mid": item.get("mid"),  # UP主ID
                    "duration": item.get("duration"),
                    "play": item.get("play"),
                    "danmaku": item.get("danmaku"),
                    "pic": item.get("pic"),
                })
            
            return results
            
        except httpx.RequestError as e:
            print(f"搜索网络错误: {e}")
            return []
        except Exception as e:
            print(f"搜索错误: {e}")
            return []
    
    def get_user_videos(self, mid: int, page: int = 1, page_size: int = 30) -> Dict:
        """
        获取UP主的视频列表
        
        API: https://api.bilibili.com/x/space/wbi/arc/search
        
        Args:
            mid: UP主的用户ID
            page: 页码
            page_size: 每页数量
            
        Returns:
            包含视频列表和分页信息的字典
        """
        url = f"{self.BASE_URL}/x/space/arc/search"
        params = {
            "mid": mid,
            "pn": page,
            "ps": page_size,
            "order": "pubdate",
        }
        
        try:
            response = self.client.get(url, params=params)
            data = response.json()
            
            if data["code"] != 0:
                print(f"获取用户视频失败: {data.get('message', '未知错误')}")
                return {"videos": [], "total": 0}
            
            vlist = data.get("data", {}).get("list", {}).get("vlist", [])
            total = data.get("data", {}).get("page", {}).get("count", 0)
            
            videos = []
            for item in vlist:
                videos.append({
                    "bvid": item.get("bvid"),
                    "aid": item.get("aid"),
                    "title": item.get("title"),
                    "description": item.get("description"),
                    "duration": item.get("length"),  # 格式: "MM:SS"
                    "play": item.get("play"),
                    "comment": item.get("comment"),
                    "created": item.get("created"),
                    "pic": item.get("pic"),
                })
            
            return {"videos": videos, "total": total}
            
        except Exception as e:
            print(f"请求错误: {e}")
            return {"videos": [], "total": 0}
    
    @staticmethod
    def _format_duration(seconds: int) -> str:
        """将秒数转换为 HH:MM:SS 格式"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def _clean_html(text: str) -> str:
        """清理HTML标签"""
        return re.sub(r'<[^>]+>', '', text)
    
    def close(self):
        """关闭客户端"""
        self.client.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ==================== 使用 bilibili-api-python 库的异步版本 ====================

async def get_video_info_async(bvid: str):
    """
    使用 bilibili-api-python 库获取视频信息 (异步版本)
    
    需要安装: pip install bilibili-api-python
    
    Args:
        bvid: 视频BV号
    """
    try:
        from bilibili_api import video
        
        v = video.Video(bvid=bvid)
        info = await v.get_info()
        
        return {
            "bvid": info.get("bvid"),
            "aid": info.get("aid"),
            "title": info.get("title"),
            "description": info.get("desc"),
            "duration": info.get("duration"),
            "cover_url": info.get("pic"),
            "owner": info.get("owner"),
            "stat": info.get("stat"),
            "cid": info.get("cid"),
            "pages": info.get("pages"),
        }
        
    except ImportError:
        print("请先安装 bilibili-api-python: pip install bilibili-api-python")
        return None
    except Exception as e:
        print(f"获取视频信息失败: {e}")
        return None


async def get_video_subtitle_async(bvid: str):
    """
    使用 bilibili-api-python 库获取视频字幕 (异步版本)
    
    Args:
        bvid: 视频BV号
    """
    try:
        from bilibili_api import video
        
        v = video.Video(bvid=bvid)
        subtitle = await v.get_subtitle(0)  # 获取第一个分P的字幕
        
        return subtitle
        
    except ImportError:
        print("请先安装 bilibili-api-python: pip install bilibili-api-python")
        return None
    except Exception as e:
        print(f"获取字幕失败: {e}")
        return None


# ==================== 示例使用 ====================

def main():
    """示例：同步版本使用"""
    print("=" * 60)
    print("Bilibili 视频信息获取示例 (同步版本)")
    print("=" * 60)
    
    with BilibiliClient() as client:
        # 示例1: 通过URL获取视频信息
        # 使用一个热门视频作为测试 (可以替换为任意有效的BV号)
        url = "https://www.bilibili.com/video/BV1uv411q7Mv"
        print(f"\n正在获取视频: {url}")
        
        video_info = client.get_video_by_url(url)
        
        if video_info:
            print(f"\n📺 标题: {video_info['title']}")
            print(f"👤 UP主: {video_info['owner']['name']}")
            print(f"⏱️ 时长: {video_info['duration_formatted']}")
            print(f"👁️ 播放: {video_info['stats']['view']:,}")
            print(f"💬 弹幕: {video_info['stats']['danmaku']:,}")
            print(f"❤️ 点赞: {video_info['stats']['like']:,}")
            print(f"⭐ 收藏: {video_info['stats']['favorite']:,}")
            print(f"🖼️ 封面: {video_info['cover_url']}")
            
            # 获取字幕
            print("\n正在获取字幕...")
            subtitles = client.get_video_subtitle(bvid=video_info['bvid'])
            if subtitles:
                print(f"找到 {len(subtitles)} 个字幕:")
                for sub in subtitles:
                    print(f"  - {sub.get('lan_doc', sub.get('lan'))}: {sub.get('subtitle_url')}")
            else:
                print("该视频没有字幕 (大部分视频没有CC字幕)")
            
            # 获取弹幕示例
            print("\n正在获取弹幕...")
            danmaku = client.get_danmaku(video_info['cid'])
            if danmaku:
                # 统计弹幕数量
                danmaku_count = danmaku.count('<d p=')
                print(f"获取到 {danmaku_count} 条弹幕")
        else:
            print("获取视频信息失败，请检查BV号是否正确")
        
        # 示例2: 搜索视频 (注意：搜索API可能需要登录cookie才能正常使用)
        print("\n" + "=" * 60)
        print("搜索视频: Python教程")
        print("=" * 60)
        print("注意: 搜索API可能需要登录cookie，如无结果属正常现象")
        
        results = client.search_videos("Python教程", page_size=5)
        if results:
            for i, video in enumerate(results, 1):
                print(f"\n{i}. {video['title']}")
                print(f"   UP主: {video['author']} | 播放: {video['play']} | BV: {video['bvid']}")
        else:
            print("搜索未返回结果 (可能需要添加cookie)")


async def main_async():
    """示例：异步版本使用 (使用bilibili-api-python库)"""
    print("=" * 60)
    print("Bilibili 视频信息获取示例 (异步版本)")
    print("=" * 60)
    
    bvid = "BV1uv411q7Mv"
    
    # 获取视频信息
    info = await get_video_info_async(bvid)
    if info:
        print(f"\n📺 标题: {info['title']}")
        print(f"👤 UP主: {info['owner'].get('name')}")
        print(f"⏱️ 时长: {info['duration']}秒")
    
    # 获取字幕
    subtitle = await get_video_subtitle_async(bvid)
    if subtitle:
        print(f"\n字幕信息: {subtitle}")


if __name__ == "__main__":
    # 运行同步版本示例
    main()
    
    # 如果要运行异步版本，取消下面的注释：
    # asyncio.run(main_async())

