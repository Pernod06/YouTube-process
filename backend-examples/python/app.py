"""
Python + Flask 后端示例
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 数据存储路径
DATA_PATH = os.path.join(os.path.dirname(__file__), '../../data/video-data.json')

# 简单的内存存储（生产环境应使用数据库）
notes_storage = {}


def load_video_data():
    """读取视频数据"""
    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading video data: {e}")
        raise


@app.before_request
def log_request():
    """请求日志"""
    print(f"{datetime.now().isoformat()} - {request.method} {request.path}")


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/videos', methods=['GET'])
def get_all_videos():
    """获取所有视频信息"""
    try:
        data = load_video_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/videos/<video_id>', methods=['GET'])
def get_video(video_id):
    """获取特定视频信息"""
    try:
        data = load_video_data()
        if data['videoInfo']['videoId'] == video_id:
            return jsonify(data)
        else:
            return jsonify({'error': 'Video not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sections', methods=['GET'])
def get_all_sections():
    """获取所有章节"""
    try:
        data = load_video_data()
        return jsonify(data['sections'])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sections/<section_id>', methods=['GET'])
def get_section(section_id):
    """获取特定章节"""
    try:
        data = load_video_data()
        section = next((s for s in data['sections'] if s['id'] == section_id), None)
        
        if section:
            return jsonify(section)
        else:
            return jsonify({'error': 'Section not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sections/search', methods=['POST'])
def search_sections():
    """搜索章节"""
    try:
        query = request.json.get('query', '').lower()
        
        if not query:
            return jsonify({'error': 'Query parameter is required'}), 400
        
        data = load_video_data()
        results = [
            section for section in data['sections']
            if query in section['title'].lower() or query in section['content'].lower()
        ]
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes', methods=['POST'])
def save_note():
    """保存笔记"""
    try:
        data = request.json
        section_id = data.get('sectionId')
        note = data.get('note')
        
        if not section_id or not note:
            return jsonify({
                'error': 'sectionId and note are required'
            }), 400
        
        note_id = f"note_{int(datetime.now().timestamp() * 1000)}"
        notes_storage[note_id] = {
            'id': note_id,
            'sectionId': section_id,
            'note': note,
            'createdAt': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'noteId': note_id,
            'data': notes_storage[note_id]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes/section/<section_id>', methods=['GET'])
def get_section_notes(section_id):
    """获取章节的所有笔记"""
    try:
        section_notes = [
            note for note in notes_storage.values()
            if note['sectionId'] == section_id
        ]
        return jsonify(section_notes)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes/<note_id>', methods=['GET'])
def get_note(note_id):
    """获取特定笔记"""
    try:
        note = notes_storage.get(note_id)
        
        if note:
            return jsonify(note)
        else:
            return jsonify({'error': 'Note not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/notes/<note_id>', methods=['DELETE'])
def delete_note(note_id):
    """删除笔记"""
    try:
        if note_id in notes_storage:
            del notes_storage[note_id]
            return jsonify({
                'success': True,
                'message': 'Note deleted'
            })
        else:
            return jsonify({'error': 'Note not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({'error': 'Route not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return jsonify({
        'error': 'Internal server error',
        'message': str(error)
    }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    print(f"Server is running on http://localhost:{port}")
    print(f"API endpoints available at http://localhost:{port}/api")
    app.run(host='0.0.0.0', port=port, debug=True)

