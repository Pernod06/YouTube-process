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


@app.route('/api/process-video', methods=['POST'])
def process_video():
    """
    处理前端传来的 YouTube 视频 URL：
    - 提取视频 ID
    - 通过 get_full_transcript 获取完整字幕和视频信息
    - 将字幕写入 data/transcript_{video_id}.txt
    - 返回基本处理状态给前端
    """
    data = request.get_json()

    if not data or 'url' not in data:
        return jsonify({
            'success': False,
            'error': 'URL is required'
        }), 400

    url = data.get('url')

    try:
        print(f"[INFO] 开始处理视频: {url}")

        import sys
        sys.path.append(str(BASE_DIR))

        from get_full_transcript import get_full_transcript, display_full_transcript
        from youtube_client import YouTubeClient

        # 提取视频 ID
        video_id = YouTubeClient.extract_video_id(url)
        if not video_id:
            return jsonify({
                'success': False,
                'error': '无法从URL提取视频ID'
            }), 400

        print(f"[INFO] 提取到视频 ID: {video_id}")

        # 获取完整字幕与视频详情（注意传入的是完整 URL）
        result = get_full_transcript(url, language='en')
        if not result:
            return jsonify({
                'success': False,
                'error': '无法获取视频字幕'
            }), 500

        transcript, details = result

        # 保存字幕到文件，供后续 /api/videos/<video_id> 使用
        output_file = DATA_DIR / f"transcript_{video_id}.txt"
        display_full_transcript(transcript, output_file=str(output_file), details=details)

        print(f"[SUCCESS] 字幕已写入文件: {output_file}")

        # 这里暂时不调用 chat_with_gemini，避免外部 API 造成阻塞或 SSL 错误
        # 如需启用，可在保证 GEMINI_API_KEY 和网络环境正常后再调用
        # optimized = chat_with_gemini({'transcript': transcript, 'details': details})

        return jsonify({
            'success': True,
            'videoId': video_id,
            'title': details.get('title', ''),
            'transcriptLength': len(transcript),
            'message': '视频处理成功'
        })

    except Exception as e:
        import traceback
        print(f"[ERROR] /api/process-video 处理失败: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '视频处理失败'
        }), 500




def chat_with_gemini(video_info):
    """
    使用Gemini API 进行聊天
    """
    import google.generativeai as genai
    import os
    import json

    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        raise ValueError("GEMINI_API_KEY 未配置")

    genai.configure(api_key=gemini_api_key)

    # Gemini 2.5 Flash model
    model = genai.GenerativeModel("gemini-2.5-flash")

    system_prompt = """
You are a helpful assistant that can answer questions about the video content.
Please fully optimize and integrate the content provided in the .txt file 
for exapmle:
{
  "videoInfo": {
    "title": "NVIDIA GTC Washington, D.C. Keynote with CEO Jensen Huang",
    "videoId": "IgsA00IsrQo",
    "description": "NVIDIA GTC Washington D.C. Keynote - Optimized Transcript",
    "thumbnail": "https://img.youtube.com/vi/lQHK61IDFH4/maxresdefault.jpg"
  },
  "sections": [
    {
      "id": "section1",
      "title": "American Innovation and the AI Revolution",
      "timestampStart": "00:00",
      "timestampEnd": "02:54",
      "content": "America has always been the land of innovation, where invention shaped destiny and technology helped dreams take flight. This history includes foundational breakthroughs like the transistor at Bell Labs, sparking the age of semiconductors and Silicon Valley, Hedy Lamarr's work paving the way for wireless connectivity, the universal computer of IBM's System 360, Intel's microprocessor, and Cray's supercomputers. Later, Apple made computing personal and portable with the iPod and iPhone, while Microsoft opened the window to new software, and ARPANET laid the foundation for the internet. Now, the next era is here, launched by a revolutionary new computing model: **Artificial Intelligence (AI)**. AI is described as the **new industrial revolution** and is considered essential infrastructure, much like electricity and the internet. Every company and nation will build it, and winning this competition will be a test of our capacities unlike anything since the space age. Today, AI factories are rising, built in America for scientists, engineers, and dreamers, clearing the way for abundance, saving lives, and extending humanity's reach to the stars in what is called America's next Apollo moment."
    },
    {
      "id": "section2",
      "title": "Welcome to GTC and the End of Moore's Law",
      "timestampStart": "02:54",
      "timestampEnd": "07:36",
      "content": "Jensen Huang welcomed the GTC audience in Washington D.C., emphasizing that the conference is where industry, science, computing, the present, and the future converge. He introduced the core innovation: the **Accelerated Computing** model, the first new computing model in 60 years. This model was invented to solve problems that general-purpose computers, or \"normal computers,\" could not. The need for this shift arose because the slowing down of Dennard Scaling and Moore's Law, limited by the laws of physics, is now a reality. While the number of transistors continues to grow, the performance and power efficiency have slowed tremendously. For 30 years, NVIDIA has advanced Accelerated Computing, inventing the **GPU** and the programming model **CUDA**. The core observation was that adding a parallel-processing GPU to a sequential-processing CPU could extend the capabilities of computing well beyond what was previously possible, and that inflection point has now arrived."
    },
    {
      "id": "section3",
      "title": "The CUDA-X Ecosystem and 30 Years of Libraries",
      "timestampStart": "07:36",
      "timestampEnd": "15:07",
      "content": "Accelerated computing is a fundamentally different programming model; simply moving sequential CPU software to a GPU will, in fact, make it run slower. This required the **reinvention of new algorithms and libraries**, and the rewriting of applications—a 30-year effort that was tackled one domain at a time. The real treasure of NVIDIA is not just the GPU, but the programming model **CUDA**, which has been kept compatible over generations (now on the cusp of CUDA 14), and the vast ecosystem of libraries known as **CUDA-X**. These libraries, which redesign algorithms for accelerated computing, open new markets and enable the entire ecosystem. Key examples include **cuLitho** for computational lithography (used by TSMC, Samsung, ASML), **cuOpt** for numerical optimization (breaking records in problems like the traveling salesperson problem), **QDF** for accelerating data frame databases, and **Megatron Core** for training extremely large language models. The list also includes **Monai** (the number one medical imaging AI framework) and **cuQuantum** for quantum computing. A demonstration showed that CUDA-X enables simulation across every industry—from healthcare and life sciences to robotics, autonomous vehicles, and computer graphics—all powered by the beauty of mathematics and deep computer science."
    },
    {
      "id": "section4",
      "title": "NVIDIA Arc and the 6G Telecommunications Platform",
      "timestampStart": "15:07",
      "timestampEnd": "21:33",
      "content": "Telecommunications is the lifeblood of our economy and national security, but wireless technology has largely been deployed on foreign standards for a long time. This fundamental platform shift presents a once-in-a-lifetime opportunity for American technology to get back into the game. NVIDIA is partnering with **Nokia**, the second-largest telecommunications maker in the world, to be at the center of the next revolution in **6G**. The new product line is the **NVIDIA Arc (Aerial Radio Network Computer)**, built from the **Grace CPU**, **Blackwell GPU**, and **ConnectX** networking, and running the **Aerial** CUDA-X library. Arc creates a **software-defined programmable computer** capable of both wireless communication and AI processing. Nokia will make Arc its future base station, which is compatible with their current Airscale stations, allowing millions of base stations globally to be upgraded with 6G and AI. The two fundamental benefits are **AI for RAN** (Radio Access Network) and **AI on RAN**. AI for RAN uses reinforcement learning to dynamically adjust beamforming and traffic, which improves spectral efficiency and reduces the world's power consumption (currently 1.5-2%). AI on RAN creates a brand new opportunity: an **edge industrial robotics cloud** on top of the wireless network, essentially extending cloud computing to the edge where base stations exist."
    },
    {
      "id": "section5",
      "title": "NVQLink: Hybrid Quantum-GPU Supercomputing",
      "timestampStart": "21:33",
      "timestampEnd": "30:36",
      "content": "The pursuit of quantum computing, first imagined by Richard Feynman in 1981 to simulate nature, recently reached a fundamental breakthrough: the ability to create one stable, error-corrected **logical qubit** (which itself consists of tens or hundreds of fragile physical qubits). To manage the instability and perform the trillions of operations required for meaningful problem-solving, a new solution is necessary: directly connecting a quantum computer (QPU) to a **GPU supercomputer**. NVIDIA's answer is **NVQLink**, a new interconnect architecture that performs **quantum error correction**, control, and calibration, and co-simulations by connecting the two computers side-by-side. NVQLink is capable of moving terabytes of data thousands of times per second, which is essential for error correction and scaling quantum computers from hundreds to hundreds of thousands of qubits in the future. The open platform at its heart is **CUDA-Q**, which extends the CUDA model to support the QPU. This vision is supported by 17 different quantum computer companies and eight DOE labs (including Berkeley, Los Alamos, and Oak Ridge) to integrate quantum computing into the future of science. In a major announcement, the Department of Energy is partnering with NVIDIA to build **seven new AI supercomputers** to advance US science, embracing the simultaneous platform shifts to accelerated computing, AI-enhanced principal solvers, quantum computing, and robotic laboratories."
    },
    {
      "id": "section6",
      "title": "AI: Reinventing the Computing Stack as 'Work'",
      "timestampStart": "30:36",
      "timestampEnd": "39:20",
      "content": "While chatbots are the public face of AI, the world of AI is much more, extending to basic science, AGI, and every industry. Fundamentally, AI has **completely reinvented the computing stack**. Software has shifted from hand-coding on CPUs to machine learning, data-intensive programming trained and learned by AI running on GPUs. This new stack requires enormous amounts of energy, which GPU supercomputers transform into **tokens**—the computational unit and vocabulary of artificial intelligence. Anything with structure and information content can be tokenized, including English words, images, video, 3D structures (like factories), chemicals, proteins, and genes. Once tokenized, AI can learn the language and meaning to translate, respond, and generate, just as ChatGPT does. The profound difference is that **AI is not a tool; AI is work**. The software industry of the past created tools (like Excel or a web browser) that humans used. AI, conversely, creates **workers**—agentic AI systems (like Perplexity or the developer partner Cursor)—that can actually use tools to perform tasks. This monumental shift allows AI to address a segment of the economy it has never touched, augmenting labor and engaging the **$100 trillion global economy** to make it more productive. Furthermore, AI itself is a **new industry**: an \"AI factory\" designed to produce these smart tokens."
    },
    {
      "id": "section7",
      "title": "The AI Factory and the Three New Scaling Laws",
      "timestampStart": "39:20",
      "timestampEnd": "45:00",
      "content": "The immense computational need for AI has necessitated the invention of the **AI factory**, a new type of system unlike the general-purpose data centers of the past. This factory is designed primarily to run AI and produce high-value, smart tokens at incredible rates for immediate response. The explosion of AI is driven by three new scaling laws: The first is **Scale**, involving larger models with more data and parameters, like the concept of a multi-trillion dollar AI model. The second is **Post-Training**, which moves beyond pre-training (the basic memorization and generalization akin to preschool) to teach the AI essential skills like problem-solving, coding, reasoning, and thinking about problems step-by-step using **first-principle reasoning**. The third, and most computationally demanding, is **Inference**, or thinking. When an AI acts as an agent—breaking down problems, reasoning, planning, and executing—it requires an enormous number of tokens to be generated. Thinking is hard, which is why the computation necessary for AI to think on behalf of every human has put extraordinary pressure on the infrastructure."
    },
    {
      "id": "section8",
      "title": "Extreme Co-Design and Manufacturing the Rubin Platform in America",
      "timestampStart": "45:00",
      "timestampEnd": "01:09:51",
      "content": "To achieve the necessary scale and performance, NVIDIA has pioneered **extreme co-design** in its infrastructure. They use **NVLink** to create one giant fabric where the entire multi-trillion parameter model, broken into \"experts,\" can communicate efficiently. This architecture is enabled by the custom **Spectrum Ethernet** (Spectrum X) designed specifically for AI performance, which is then scaled across multiple data centers via **Spectrum XGS (Gigascale X)**. This code-design is so extreme that it delivers \"shocking\" generational performance benefits—much more than typical gains. The latest platform is the **Rubin platform** (the third generation NVLink 72 rack scale computer), a system that has been \"ground up, reinvented\" since the IBM System 360. This new node, completely cableless and **100% liquid-cooled**, features the **ConnectX-9**, **BlueField-4 DPU**, **Vera CPUs**, and **Rubin GPUs**, delivering 100 times the performance of the DGX-1 delivered just nine years ago. Critically, NVIDIA is also manufacturing the **Blackwell** and future generations of these AI factory systems in America, with production starting in Arizona, Indiana, and Texas, fulfilling the call to **bring manufacturing back** for national security and reindustrialization."
    },
    {
      "id": "section9",
      "title": "AI Agents and the Transformation of Enterprise",
      "timestampStart": "01:09:51",
      "timestampEnd": "01:26:21",
      "content": "The next frontier for this powerful computing is the **Enterprise**, where workloads and workflows will transition to **Agentic SaaS (Software as a Service)**. NVIDIA is partnering with industry leaders to integrate its libraries (CUDA-X, Nemo, NeMo-Triton) and AI systems to create AI agents and accelerate platforms across the global economy. Key partnerships include: **ServiceNow**, which handles 85% of the world's enterprise workflows; **SAP**, which facilitates 80% of the world's commerce; and major EDA/CAD firms like **Synopsis** and **Cadence**, accelerating their stacks and working towards having AI agent ASIC and system designers. Furthermore, recognizing that AI will supercharge cyber security challenges, NVIDIA is partnering with **CrowdStrike** to build an incredible defender platform. Finally, a partnership with **Palantir** will accelerate everything they do, allowing for data processing and business insight—for both structured and unstructured data—at the speed of light for government and enterprises globally."
    },
    {
      "id": "section10",
      "title": "Conclusion: Two Platform Transitions and the Future",
      "timestampStart": "01:26:21",
      "timestampEnd": "01:42:25",
      "content": "In closing, the world is experiencing an extraordinary period of growth fueled by two concurrent platform transitions. The first is the inflection point of **Accelerated Computing**, and the second is the fundamental transition of software to **Artificial Intelligence**. The new platforms introduced—**ARC** for 6G, **Hyperion** for robotics cars, **DSX** for the AI factory, and **Mega** for factories with AI—demonstrate this comprehensive transformation. NVIDIA celebrates the return of manufacturing and the building of these technologies in America, marking a new chapter in industry and history. The keynote concludes by thanking the attendees for their service and for allowing GTC to be hosted in Washington D.C."
    }
  ]
}
    """

    response = model.generate_content(system_prompt, video_info)

    json = json.loads(response.choices[0].message.content)

    print(f"video data json information: {json}")
    return json



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
    print('🚀 Server is running on http://localhost:5000')
    print('📊 API endpoint: http://localhost:5000/api')
    print('🌐 Frontend: http://localhost:5000/index.html')
    app.run(debug=True, host='0.0.0.0', port=5000)

