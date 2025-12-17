import os, requests
API_KEY = os.getenv('API_KEY', 'sk_xEEnrdnWKBMM4zt6wI8klBfnaX3KspU86fGw1V0oMnU')
url = 'https://transcriptapi.com/api/v2/youtube/transcript'
params = {'video_url': '0Yh0wExU_VM', 'format': 'json'}
r = requests.get(url, params=params, headers={'Authorization': 'Bearer ' + API_KEY}, timeout=30)
r.raise_for_status()
print(r.json()['transcript'])