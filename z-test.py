# from google import genai

# client = genai.Client(api_key="AIzaSyCuCtYLgndLW5yfoR6AaagHmjmLMJyj_84")

# response = client.models.generate_content(
#     model="gemini-3-pro-preview",
#     contents=["print this vedio based transcript timestamp :https://www.youtube.com/watch?v=DxL2HoqLbyA. dont change anything."]
# )
# for chunk in response:
#     print(chunk, end="")


import os, requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('TranscriptAPI_KEY')
url = 'https://transcriptapi.com/api/v2/youtube/transcript'
params = {'video_url': 'sOvi9Iu1Dq8', 'format': 'json'}
r = requests.get(url, params=params, headers={'Authorization': 'Bearer ' + API_KEY}, timeout=30)
r.raise_for_status()
print(r.json()['transcript'])



# from youtube_client import YouTubeClient
        
# # 创建 YouTube 客户端
# print("[INFO] 正在初始化 YouTube 客户端...")
# client = YouTubeClient()
        
# # 获取评论数量参数（默认20条）
# max_results = 20
        
# print(f"[INFO] 正在调用 YouTube API 获取 {max_results} 条评论...")
# # 调用 YouTube API 获取评论
# comments = client.get_video_comments("zsOYK-sb3Qo", max_results=max_results)
# print(comments)