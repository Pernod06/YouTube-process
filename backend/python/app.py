"""
Python + Flask 后端示例
安装依赖: pip install flask flask-cors
"""

from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
import json
import os
from datetime import date, datetime
from pathlib import Path
from pdf_generator import generate_video_pdf
from video_frame_extractor import extract_frame_at_timestamp

# 添加以下代码来加载 .env 文件
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    print(f"[App] .env 文件已加载")
except ImportError:
    print("[App] python-dotenv 未安装")

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
STATIC_DIR = BASE_DIR

# 内存存储（生产环境应使用数据库）
comments_db = {}
progress_db = {}


def load_video_data():
    """加载视频数据"""
    data_path = DATA_DIR / 'video-data.json'
    with open(data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@app.route('/api/videos/<video_id>', methods=['GET'])
def get_video(video_id):
    """获取视频数据"""
    try:
        video_data = load_video_data()
        # 可以根据 video_id 过滤数据
        return jsonify(video_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/videos', methods=['GET'])
def get_videos():
    """获取视频列表"""
    videos = [
        {
            'videoId': 'lQHK61IDFH4',
            'title': 'NVIDIA GTC Washington D.C. Keynote',
            'description': 'CEO Jensen Huang keynote',
            'thumbnail': 'https://img.youtube.com/vi/lQHK61IDFH4/maxresdefault.jpg',
            'duration': '01:42:25',
            'uploadDate': '2024-03-18'
        }
    ]
    return jsonify(videos)


@app.route('/api/videos/<video_id>/comments', methods=['GET'])
def get_comments(video_id):
    """获取YouTube评论"""
    try:
        # 尝试导入 youtube_client
        import sys
        import traceback
        sys.path.append(str(BASE_DIR))
        
        print(f"[INFO] 正在获取视频 {video_id} 的评论...")
        
        from youtube_client import YouTubeClient
        
        # 创建 YouTube 客户端
        print("[INFO] 正在初始化 YouTube 客户端...")
        client = YouTubeClient()
        
        # 获取评论数量参数（默认20条）
        max_results = request.args.get('maxResults', 20, type=int)
        max_results = min(max_results, 100)  # 限制最大100条
        
        print(f"[INFO] 正在调用 YouTube API 获取 {max_results} 条评论...")
        # 调用 YouTube API 获取评论
        comments = client.get_video_comments(video_id, max_results=max_results)
        
        if comments:
            print(f"[SUCCESS] 成功获取 {len(comments)} 条评论")
            return jsonify({
                'success': True,
                'videoId': video_id,
                'comments': comments,
                'total': len(comments)
            })
        else:
            # 如果获取失败，返回空列表
            print("[WARNING] 未获取到评论")
            return jsonify({
                'success': True,
                'videoId': video_id,
                'comments': [],
                'total': 0,
                'message': '该视频没有评论或评论已关闭'
            })
    except ImportError as e:
        # 如果无法导入 youtube_client，返回模拟数据
        print(f"[ERROR] 导入错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'videoId': video_id,
            'comments': [],
            'total': 0,
            'error': str(e),
            'message': 'YouTube API 客户端导入失败'
        }), 500
    except ValueError as e:
        # YouTube API 密钥未配置
        print(f"[ERROR] 配置错误: {str(e)}")
        return jsonify({
            'success': False,
            'videoId': video_id,
            'comments': [],
            'total': 0,
            'error': str(e),
            'message': 'YouTube API 密钥未配置或无效，请检查 config.py'
        }), 500
    except Exception as e:
        print(f"[ERROR] 未知错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'videoId': video_id,
            'error': str(e),
            'error_type': type(e).__name__,
            'message': '获取评论失败，请查看后端日志'
        }), 500


@app.route('/api/videos/<video_id>/comments', methods=['POST'])
def post_comment(video_id):
    """发布评论"""
    data = request.get_json()
    
    if not data or 'comment' not in data:
        return jsonify({'error': 'Comment is required'}), 400
    
    if video_id not in comments_db:
        comments_db[video_id] = []
    
    new_comment = {
        'id': str(int(datetime.now().timestamp() * 1000)),
        'author': data.get('author', 'Anonymous'),
        'text': data['comment'],
        'timestamp': datetime.now().isoformat()
    }
    
    comments_db[video_id].append(new_comment)
    return jsonify(new_comment), 201


@app.route('/api/videos/<video_id>/progress', methods=['GET'])
def get_progress(video_id):
    """获取播放进度"""
    user_progress = progress_db.get(video_id, {'timestamp': 0})
    return jsonify(user_progress)


@app.route('/api/videos/<video_id>/progress', methods=['PUT'])
def update_progress(video_id):
    """更新播放进度"""
    data = request.get_json()
    
    if not data or 'timestamp' not in data:
        return jsonify({'error': 'Timestamp is required'}), 400
    
    if not isinstance(data['timestamp'], (int, float)):
        return jsonify({'error': 'Invalid timestamp'}), 400
    
    progress_db[video_id] = {
        'timestamp': data['timestamp'],
        'updatedAt': datetime.now().isoformat()
    }
    
    return jsonify({
        'success': True,
        'progress': progress_db[video_id]
    })


@app.route('/api/search', methods=['GET'])
def search():
    """搜索内容"""
    query = request.args.get('q', '').lower()
    
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    try:
        video_data = load_video_data()
        results = []
        
        for section in video_data.get('sections', []):
            title = section['title'].lower()
            content = section['content'].lower()
            
            if query in title or query in content:
                # 提取匹配片段
                index = content.find(query)
                if index != -1:
                    snippet_start = max(0, index - 50)
                    snippet_end = min(len(section['content']), index + len(query) + 50)
                    snippet = '...' + section['content'][snippet_start:snippet_end] + '...'
                else:
                    snippet = section['content'][:100] + '...'
                
                results.append({
                    'videoId': video_data['videoInfo']['videoId'],
                    'sectionId': section['id'],
                    'title': section['title'],
                    'snippet': snippet,
                    'timestamp': section['timestampStart']
                })
        
        return jsonify({
            'results': results,
            'total': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })


# 提供静态文件
@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(STATIC_DIR, path)


# 错误处理
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    LLM 聊天接口
    """
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({'error': 'Message is required'}), 400
    
    user_message = data['message']
    video_context = data.get('video_context', None)

    try:
        # 调用 Claude API 进行聊天
        response = chat_with_openai(user_message, video_context)

        return jsonify({
            'success': True,
            'response': response,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'response': 'sorry, please try again later.'
        }), 500


@app.route('/api/generate-pdf', methods=['GET'])
def generate_pdf():
    """
    生成视频数据的 PDF 文档
    """
    try:
        print('[INFO] 开始生成 PDF...')
        
        # 加载视频数据
        video_data = load_video_data()
        
        # 生成 PDF（在内存中）
        pdf_buffer = generate_video_pdf(video_data, output_path=None)
        
        # 生成文件名
        video_title = video_data.get('videoInfo', {}).get('title', 'video')
        # 清理文件名中的特殊字符
        safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title[:50]  # 限制长度
        filename = f"{safe_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        print(f'[SUCCESS] PDF 生成成功: {filename}')
        
        # 返回 PDF 文件
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f'[ERROR] PDF 生成失败: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'PDF 生成失败'
        }), 500

@app.route('/api/video-frame/<video_id>', methods=['GET'])
def get_video_frame(video_id):
    """
    获取视频指定时间戳的帧图片
    
    Query Parameters:
        - timestamp: 时间戳（秒），默认为 0
    
    Example:
        GET /api/video-frame/EF8C4v7JIbA?timestamp=1794
    """
    timestamp = request.args.get('timestamp', 0, type=int)
    
    try:
        print(f"[INFO] 收到帧提取请求 - 视频ID: {video_id}, 时间戳: {timestamp}")
        
        # 提取帧
        frame_path = extract_frame_at_timestamp(video_id, timestamp)
        
        # 返回图片文件
        return send_file(
            frame_path,
            mimetype='image/jpeg',
            as_attachment=False,
            download_name=f"frame_{video_id}_{timestamp}.jpg"
        )
        
    except Exception as e:
        print(f"[ERROR] 帧提取失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '无法提取视频帧'
        }), 500


@app.route('/api/video-info/<video_id>', methods=['GET'])
def get_video_info(video_id):
    """获取 YouTube 视频信息（标题、描述等）"""
    try:
        print(f"[INFO] 获取视频信息 - 视频ID: {video_id}")
        
        import sys
        sys.path.append(str(BASE_DIR))
        from youtube_get_video_information import get_video_information
        
        # 获取视频信息
        video_info = get_video_information(video_id)
        
        if not video_info:
            return jsonify({'success': False, 'message': '无法获取视频信息'}), 404
        
        print(f"[SUCCESS] 视频信息获取成功")
        
        return jsonify({
            'success': True,
            'videoId': video_id,
            'title': video_info.get('title', ''),
            'description': video_info.get('description', ''),
            'channelTitle': video_info.get('channel_title', ''),
            'publishedAt': video_info.get('published_at', ''),
            'duration': video_info.get('duration', ''),
            'viewCount': video_info.get('view_count', 0),
            'likeCount': video_info.get('like_count', 0),
            'thumbnail': video_info.get('thumbnails', {}).get('maxres', '')
        })
        
    except Exception as e:
        print(f"[ERROR] 获取视频信息失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/video-chapters/<video_id>', methods=['GET'])
def get_video_chapters(video_id):
    """获取视频章节列表（直接调用现有函数）"""
    try:
        from video_frame_extractor import extract_youtube_chapters
        chapters = extract_youtube_chapters(video_id)
        
        if not chapters:
            return jsonify({'success': False, 'message': '未找到章节'}), 404
        
        return jsonify({'success': True, 'chapters': chapters, 'total': len(chapters)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/video-frames/<video_id>', methods=['POST'])
def get_video_frames_batch(video_id):
    """
    批量获取视频多个时间戳的帧图片
    
    Request Body:
        {
            "timestamps": [10, 30, 60, 120, 180]  // 时间戳数组（秒）
        }
    
    Response:
        {
            "success": true,
            "videoId": "xxx",
            "frames": [
                {
                    "timestamp": 10,
                    "success": true,
                    "url": "/api/video-frame/xxx?timestamp=10"
                },
                ...
            ]
        }
    
    Example:
        POST /api/video-frames/EF8C4v7JIbA
        Body: {"timestamps": [10, 30, 60]}
    """
    data = request.get_json()
    
    if not data or 'timestamps' not in data:
        return jsonify({
            'success': False,
            'error': 'timestamps array is required'
        }), 400
    
    timestamps = data['timestamps']
    
    if not isinstance(timestamps, list):
        return jsonify({
            'success': False,
            'error': 'timestamps must be an array'
        }), 400
    
    try:
        print(f"[INFO] 收到批量帧提取请求 - 视频ID: {video_id}, 时间戳数量: {len(timestamps)}")
        
        from video_frame_extractor import extract_multiple_frames
        
        # 提取多个帧
        results = extract_multiple_frames(video_id, timestamps)
        
        # 转换结果格式，添加 URL
        frames = []
        for result in results:
            if result['success']:
                frames.append({
                    'timestamp': result['timestamp'],
                    'success': True,
                    'url': f"/api/video-frame/{video_id}?timestamp={result['timestamp']}"
                })
            else:
                frames.append({
                    'timestamp': result['timestamp'],
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                })
        
        success_count = sum(1 for f in frames if f['success'])
        print(f"[SUCCESS] 批量帧提取完成 - 成功: {success_count}/{len(timestamps)}")
        
        return jsonify({
            'success': True,
            'videoId': video_id,
            'frames': frames,
            'total': len(frames),
            'successCount': success_count
        })
        
    except Exception as e:
        print(f"[ERROR] 批量帧提取失败: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '批量提取视频帧失败'
        }), 500


@app.route('/api/generate-mindmap', methods=['GET'])
def generate_mindmap():
    """
    生成视频内容的 Mermaid 思维导图
    """
    try:
        print('[INFO] 开始生成 Mermaid 思维导图...')
        
        # 加载视频数据
        video_data = load_video_data()
        
        # 调用 LLM 生成 Mermaid 格式思维导图
        mermaid_code = generate_mindmap_with_llm(video_data)
        
        print('[SUCCESS] Mermaid 思维导图生成成功')
        print('[DEBUG] Mermaid 代码:')
        print(mermaid_code)
        
        return jsonify({
            'success': True,
            'mermaid': mermaid_code,
            'videoTitle': video_data.get('videoInfo', {}).get('title', 'Video'),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        print(f'[ERROR] 思维导图生成失败: {str(e)}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '思维导图生成失败'
        }), 500


def generate_mindmap_with_llm(video_data):
    """
    使用 OpenAI 生成 Mermaid 格式的思维导图
    """
    from openai import OpenAI
    import os

    # 检查 API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or api_key == 'YOUR_API_KEY_HERE':
        raise ValueError("OPENAI_API_KEY 未配置，请在 .env 文件中设置")

    # 初始化客户端
    client = OpenAI(
        api_key=api_key
    )
    
    # 准备视频内容摘要
    video_info = video_data.get('videoInfo', {})
    sections = video_data.get('sections', [])
    
    # 构建内容文本
    content_text = f"视频标题: {video_info.get('title', '')}\n"
    content_text += f"视频摘要: {video_info.get('summary', '')}\n\n"
    content_text += "章节内容:\n"
    
    for section in sections:
        content_text += f"\n## {section.get('title', '')}\n"
        content_text += f"时间: {section.get('timestampStart', '')} - {section.get('timestampEnd', '')}\n"
        content_text += f"{section.get('content', '')}\n"
    
    system_prompt = """你是一个专业的思维导图生成助手。请根据提供的视频内容生成简洁清晰的 Mermaid mindmap 格式思维导图。

Mermaid mindmap 语法说明：
1. 以 `mindmap` 开头
2. 使用缩进表示层级关系（2个空格为一级缩进）
3. 根节点使用 root((文本)) 格式
4. 其他节点直接写文本即可

示例格式：
mindmap
  root((主题))
    分类A
      要点1
      要点2
    分类B
      要点3
      要点4

核心要求（严格遵守）：
1. 根节点：最多6个字，提取核心主题
2. 一级分支：3-5个主要分类，每个4-8字
3. 二级分支：每个一级分支下最多3-4个子节点，每个3-6字
4. 严禁第三层及以上，只保持2层结构（根节点 + 一级分支 + 二级分支）
5. 总节点数控制在15-20个以内
6. 提取最核心的概念和关键词，去掉冗余信息
7. 使用中文输出
8. 只输出 Mermaid 代码，不要额外解释
9. 确保缩进正确（2个空格）
10. 每个分支下的节点数量要均衡，保持视觉对称

布局建议：
- 第一级分支：3-4个（奇数更好看）
- 每个第一级分支下：2-3个第二级节点
- 保持左右平衡
"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"请根据以下视频内容生成 Mermaid mindmap 格式的思维导图：\n\n{content_text}"}
    ]
    
    # 调用 OpenAI API
    print("[INFO] 正在调用 OpenAI API 生成 Mermaid 思维导图...")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=4000,
        temperature=0.3
    )
    
    # 提取返回内容
    mermaid_content = response.choices[0].message.content
    
    # 清理返回内容（移除可能的代码块标记）
    if mermaid_content.startswith('```mermaid'):
        mermaid_content = mermaid_content.replace('```mermaid', '').replace('```', '').strip()
    elif mermaid_content.startswith('```'):
        mermaid_content = mermaid_content.replace('```', '').strip()
    
    # 检查返回内容是否为空
    if not mermaid_content or mermaid_content.strip() == '':
        print("[ERROR] OpenAI 返回内容为空")
        raise ValueError("AI 生成的思维导图内容为空，请重试")
    
    # 验证是否以 mindmap 开头
    if not mermaid_content.strip().startswith('mindmap'):
        print("[WARNING] 返回内容不是标准的 Mermaid mindmap 格式，尝试修复...")
        mermaid_content = 'mindmap\n  root((视频主题))\n' + mermaid_content
    
    print(f"[SUCCESS] OpenAI API 调用成功，返回 {len(mermaid_content)} 字符")
    return mermaid_content


def chat_with_openai(user_message, video_context):
    """
    使用Open AI (新版 API >= 1.0.0)
    """
    from openai import OpenAI
    import os

    # 初始化客户端
    client = OpenAI(
        api_key=os.getenv('OPENAI_API_KEY')
    )
    
    system_prompt = """你是一个视频助手，帮助用户理解和查找视频内容。
当前视频是关于 NVIDIA GTC 大会的主题演讲，涵盖了 AI、加速计算、量子计算等主题。
请用简洁、友好的方式回答用户问题。"""
    
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    if video_context:
        messages.append({
            "role": "system",
            "content": f"视频信息：{json.dumps(video_context, ensure_ascii=False)}"
        })
    
    # 添加用户消息
    messages.append({"role": "user", "content": user_message})
    
    # 调用 OpenAI API (新版)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=500,
        temperature=0.7
    )
    
    return response.choices[0].message.content

if __name__ == '__main__':
    print('🚀 Server is running on http://localhost:5500')
    print('📊 API endpoint: http://localhost:5500/api')
    print('🌐 Frontend: http://localhost:5500/index.html')
    app.run(debug=True, host='0.0.0.0', port=5500)

