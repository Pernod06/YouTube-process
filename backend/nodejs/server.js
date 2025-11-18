/**
 * Node.js + Express 后端示例
 * 安装依赖: npm install express cors body-parser
 */

const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const path = require('path');
const fs = require('fs').promises;

const app = express();
const PORT = process.env.PORT || 3000;

// 中间件
app.use(cors());
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname, '../../'))); // 提供静态文件

// 内存存储（生产环境应使用数据库）
const comments = {};
const progress = {};

/**
 * 获取视频数据
 */
app.get('/api/videos/:videoId', async (req, res) => {
    try {
        const { videoId } = req.params;
        
        // 从数据库或文件读取
        const dataPath = path.join(__dirname, '../../data/video-data.json');
        const data = await fs.readFile(dataPath, 'utf8');
        const videoData = JSON.parse(data);
        
        // 可以根据 videoId 过滤或从数据库查询
        res.json(videoData);
    } catch (error) {
        console.error('Error fetching video:', error);
        res.status(500).json({ error: 'Failed to fetch video data' });
    }
});

/**
 * 获取视频列表
 */
app.get('/api/videos', async (req, res) => {
    try {
        // 示例：返回所有可用视频
        const videos = [
            {
                videoId: 'lQHK61IDFH4',
                title: 'NVIDIA GTC Washington D.C. Keynote',
                description: 'CEO Jensen Huang keynote',
                thumbnail: 'https://img.youtube.com/vi/lQHK61IDFH4/maxresdefault.jpg',
                duration: '01:42:25',
                uploadDate: '2024-03-18'
            }
        ];
        
        res.json(videos);
    } catch (error) {
        console.error('Error fetching videos:', error);
        res.status(500).json({ error: 'Failed to fetch videos' });
    }
});

/**
 * 获取评论
 */
app.get('/api/videos/:videoId/comments', (req, res) => {
    const { videoId } = req.params;
    const videoComments = comments[videoId] || [];
    res.json(videoComments);
});

/**
 * 发布评论
 */
app.post('/api/videos/:videoId/comments', (req, res) => {
    const { videoId } = req.params;
    const { comment, author = 'Anonymous' } = req.body;
    
    if (!comment) {
        return res.status(400).json({ error: 'Comment is required' });
    }
    
    if (!comments[videoId]) {
        comments[videoId] = [];
    }
    
    const newComment = {
        id: Date.now().toString(),
        author,
        text: comment,
        timestamp: new Date().toISOString()
    };
    
    comments[videoId].push(newComment);
    res.status(201).json(newComment);
});

/**
 * 获取播放进度
 */
app.get('/api/videos/:videoId/progress', (req, res) => {
    const { videoId } = req.params;
    const userProgress = progress[videoId] || { timestamp: 0 };
    res.json(userProgress);
});

/**
 * 更新播放进度
 */
app.put('/api/videos/:videoId/progress', (req, res) => {
    const { videoId } = req.params;
    const { timestamp } = req.body;
    
    if (typeof timestamp !== 'number') {
        return res.status(400).json({ error: 'Invalid timestamp' });
    }
    
    progress[videoId] = { timestamp, updatedAt: new Date().toISOString() };
    res.json({ success: true, progress: progress[videoId] });
});

/**
 * 搜索内容
 */
app.get('/api/search', async (req, res) => {
    try {
        const { q } = req.query;
        
        if (!q) {
            return res.status(400).json({ error: 'Query parameter "q" is required' });
        }
        
        // 读取视频数据
        const dataPath = path.join(__dirname, '../../data/video-data.json');
        const data = await fs.readFile(dataPath, 'utf8');
        const videoData = JSON.parse(data);
        
        // 搜索匹配的内容
        const results = [];
        const query = q.toLowerCase();
        
        videoData.sections.forEach(section => {
            if (section.title.toLowerCase().includes(query) || 
                section.content.toLowerCase().includes(query)) {
                
                // 提取匹配片段
                const contentLower = section.content.toLowerCase();
                const index = contentLower.indexOf(query);
                const snippetStart = Math.max(0, index - 50);
                const snippetEnd = Math.min(section.content.length, index + query.length + 50);
                const snippet = '...' + section.content.substring(snippetStart, snippetEnd) + '...';
                
                results.push({
                    videoId: videoData.videoInfo.videoId,
                    sectionId: section.id,
                    title: section.title,
                    snippet,
                    timestamp: section.timestampStart
                });
            }
        });
        
        res.json({ results, total: results.length });
    } catch (error) {
        console.error('Search error:', error);
        res.status(500).json({ error: 'Search failed' });
    }
});

/**
 * 健康检查
 */
app.get('/api/health', (req, res) => {
    res.json({ 
        status: 'ok', 
        timestamp: new Date().toISOString(),
        version: '1.0.0'
    });
});

// 错误处理中间件
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ error: 'Something went wrong!' });
});

// 启动服务器
app.listen(PORT, () => {
    console.log(`🚀 Server is running on http://localhost:${PORT}`);
    console.log(`📊 API endpoint: http://localhost:${PORT}/api`);
    console.log(`🌐 Frontend: http://localhost:${PORT}/index.html`);
});

module.exports = app;

