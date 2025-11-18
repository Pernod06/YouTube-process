# 后端示例说明

本目录包含两个后端实现示例，供你参考和选择。

## 📁 目录结构

```
backend-examples/
├── nodejs/           # Node.js + Express 实现
│   ├── server.js
│   └── package.json
├── python/           # Python + Flask 实现
│   ├── app.py
│   └── requirements.txt
└── README.md         # 本文件
```

## 🚀 Node.js + Express 后端

### 安装依赖

```bash
cd backend-examples/nodejs
npm install
```

### 运行服务器

```bash
# 生产模式
npm start

# 开发模式（自动重启）
npm run dev
```

服务器将在 `http://localhost:3000` 启动

### 特点
- 使用 Express 框架
- CORS 支持
- RESTful API 设计
- 内存存储（可替换为数据库）
- 完整的错误处理

## 🐍 Python + Flask 后端

### 安装依赖

```bash
cd backend-examples/python
pip install -r requirements.txt
```

### 运行服务器

```bash
python app.py
```

服务器将在 `http://localhost:3000` 启动

### 特点
- 使用 Flask 框架
- CORS 支持
- RESTful API 设计
- 内存存储（可替换为数据库）
- 完整的错误处理

## 📡 API 端点说明

两个实现都提供相同的API端点：

### 视频相关

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/videos` | 获取所有视频 |
| GET | `/api/videos/:videoId` | 获取特定视频 |

### 章节相关

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/sections` | 获取所有章节 |
| GET | `/api/sections/:sectionId` | 获取特定章节 |
| POST | `/api/sections/search` | 搜索章节 |

### 笔记相关

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/notes` | 保存笔记 |
| GET | `/api/notes/:noteId` | 获取特定笔记 |
| GET | `/api/notes/section/:sectionId` | 获取章节的所有笔记 |
| DELETE | `/api/notes/:noteId` | 删除笔记 |

## 📝 API 使用示例

### 1. 获取视频数据

```bash
curl http://localhost:3000/api/videos
```

### 2. 搜索章节

```bash
curl -X POST http://localhost:3000/api/sections/search \
  -H "Content-Type: application/json" \
  -d '{"query": "AI"}'
```

### 3. 保存笔记

```bash
curl -X POST http://localhost:3000/api/notes \
  -H "Content-Type: application/json" \
  -d '{
    "sectionId": "section1",
    "note": {
      "text": "这是一个笔记",
      "timestamp": "2024-01-01T00:00:00Z"
    }
  }'
```

### 4. 获取章节笔记

```bash
curl http://localhost:3000/api/notes/section/section1
```

## 🔧 配置前端连接后端

编辑 `js/config.js`：

```javascript
CONFIG.API.development.BASE_URL = 'http://localhost:3000/api';
CONFIG.APP.USE_LOCAL_DATA = false;
```

## 🗄️ 数据库集成

### Node.js + MongoDB

```bash
npm install mongoose
```

```javascript
const mongoose = require('mongoose');

// 连接数据库
mongoose.connect('mongodb://localhost/youtube-process');

// 定义模型
const NoteSchema = new mongoose.Schema({
    sectionId: String,
    note: Object,
    createdAt: { type: Date, default: Date.now }
});

const Note = mongoose.model('Note', NoteSchema);

// 使用模型
app.post('/api/notes', async (req, res) => {
    const note = new Note(req.body);
    await note.save();
    res.json({ success: true, data: note });
});
```

### Python + SQLAlchemy

```bash
pip install Flask-SQLAlchemy
```

```python
from flask_sqlalchemy import SQLAlchemy

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///youtube.db'
db = SQLAlchemy(app)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    section_id = db.Column(db.String(50))
    note_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@app.route('/api/notes', methods=['POST'])
def save_note():
    data = request.json
    note = Note(
        section_id=data['sectionId'],
        note_text=json.dumps(data['note'])
    )
    db.session.add(note)
    db.session.commit()
    return jsonify({'success': True, 'data': note.id})
```

## 🔐 添加认证

### Node.js + JWT

```bash
npm install jsonwebtoken
```

```javascript
const jwt = require('jsonwebtoken');
const SECRET_KEY = 'your-secret-key';

// 认证中间件
function authenticateToken(req, res, next) {
    const authHeader = req.headers['authorization'];
    const token = authHeader && authHeader.split(' ')[1];
    
    if (!token) {
        return res.status(401).json({ error: 'Access denied' });
    }
    
    jwt.verify(token, SECRET_KEY, (err, user) => {
        if (err) {
            return res.status(403).json({ error: 'Invalid token' });
        }
        req.user = user;
        next();
    });
}

// 保护路由
app.post('/api/notes', authenticateToken, async (req, res) => {
    // 处理请求
});
```

### Python + JWT

```bash
pip install PyJWT
```

```python
import jwt
from functools import wraps

SECRET_KEY = 'your-secret-key'

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            token = token.split(' ')[1]
            data = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        except:
            return jsonify({'error': 'Invalid token'}), 403
        
        return f(*args, **kwargs)
    
    return decorated

@app.route('/api/notes', methods=['POST'])
@token_required
def save_note():
    # 处理请求
    pass
```

## 📊 性能优化建议

### 1. 缓存
```javascript
const NodeCache = require('node-cache');
const cache = new NodeCache({ stdTTL: 600 });

app.get('/api/videos', async (req, res) => {
    const cacheKey = 'all_videos';
    const cached = cache.get(cacheKey);
    
    if (cached) {
        return res.json(cached);
    }
    
    const data = await loadVideoData();
    cache.set(cacheKey, data);
    res.json(data);
});
```

### 2. 分页
```javascript
app.get('/api/sections', (req, res) => {
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 10;
    const startIndex = (page - 1) * limit;
    const endIndex = page * limit;
    
    const sections = allSections.slice(startIndex, endIndex);
    
    res.json({
        data: sections,
        page,
        totalPages: Math.ceil(allSections.length / limit)
    });
});
```

### 3. 压缩响应
```javascript
const compression = require('compression');
app.use(compression());
```

## 🧪 测试

### Node.js 测试示例

```javascript
const request = require('supertest');
const app = require('./server');

describe('API Tests', () => {
    test('GET /api/health returns ok', async () => {
        const response = await request(app).get('/api/health');
        expect(response.status).toBe(200);
        expect(response.body.status).toBe('ok');
    });
    
    test('POST /api/sections/search', async () => {
        const response = await request(app)
            .post('/api/sections/search')
            .send({ query: 'AI' });
        expect(response.status).toBe(200);
        expect(Array.isArray(response.body)).toBe(true);
    });
});
```

## 📦 部署建议

### Node.js 部署

1. **使用 PM2**
```bash
npm install -g pm2
pm2 start server.js
pm2 save
```

2. **Docker**
```dockerfile
FROM node:18
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

### Python 部署

1. **使用 Gunicorn**
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:3000 app:app
```

2. **Docker**
```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 3000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:3000", "app:app"]
```

## 🔍 调试技巧

### Node.js 调试
```bash
# 使用 Node 调试器
node --inspect server.js

# 使用 VS Code 调试配置
{
    "type": "node",
    "request": "launch",
    "name": "Launch Server",
    "program": "${workspaceFolder}/server.js"
}
```

### Python 调试
```bash
# 使用 Python 调试器
python -m pdb app.py

# Flask 调试模式
export FLASK_ENV=development
export FLASK_DEBUG=1
flask run
```

---

选择适合你的技术栈，开始构建吧！ 🚀

