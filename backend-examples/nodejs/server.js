// Node.js + Express 后端示例
const express = require('express');
const cors = require('cors');
const fs = require('fs').promises;
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// 中间件
app.use(cors());
app.use(express.json());

// 日志中间件
app.use((req, res, next) => {
    console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
    next();
});

// 数据存储路径
const DATA_PATH = path.join(__dirname, '../../data/video-data.json');

/**
 * 读取视频数据
 */
async function loadVideoData() {
    try {
        const data = await fs.readFile(DATA_PATH, 'utf-8');
        return JSON.parse(data);
    } catch (error) {
        console.error('Error loading video data:', error);
        throw new Error('Failed to load video data');
    }
}

/**
 * API路由
 */

// 健康检查
app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// 获取所有视频信息
app.get('/api/videos', async (req, res) => {
    try {
        const data = await loadVideoData();
        res.json(data);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 获取特定视频信息
app.get('/api/videos/:videoId', async (req, res) => {
    try {
        const data = await loadVideoData();
        // 这里可以根据videoId过滤
        if (data.videoInfo.videoId === req.params.videoId) {
            res.json(data);
        } else {
            res.status(404).json({ error: 'Video not found' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 获取所有章节
app.get('/api/sections', async (req, res) => {
    try {
        const data = await loadVideoData();
        res.json(data.sections);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 获取特定章节
app.get('/api/sections/:sectionId', async (req, res) => {
    try {
        const data = await loadVideoData();
        const section = data.sections.find(s => s.id === req.params.sectionId);
        
        if (section) {
            res.json(section);
        } else {
            res.status(404).json({ error: 'Section not found' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 搜索章节
app.post('/api/sections/search', async (req, res) => {
    try {
        const { query } = req.body;
        
        if (!query) {
            return res.status(400).json({ error: 'Query parameter is required' });
        }
        
        const data = await loadVideoData();
        const results = data.sections.filter(section => {
            const searchText = `${section.title} ${section.content}`.toLowerCase();
            return searchText.includes(query.toLowerCase());
        });
        
        res.json(results);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 简单的笔记存储（内存中）
// 生产环境应该使用数据库
let notes = {};

// 保存笔记
app.post('/api/notes', (req, res) => {
    try {
        const { sectionId, note } = req.body;
        
        if (!sectionId || !note) {
            return res.status(400).json({ 
                error: 'sectionId and note are required' 
            });
        }
        
        const noteId = `note_${Date.now()}`;
        notes[noteId] = {
            id: noteId,
            sectionId,
            note,
            createdAt: new Date().toISOString()
        };
        
        res.json({ 
            success: true, 
            noteId,
            data: notes[noteId]
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 获取章节的所有笔记
app.get('/api/notes/section/:sectionId', (req, res) => {
    try {
        const sectionId = req.params.sectionId;
        const sectionNotes = Object.values(notes).filter(
            note => note.sectionId === sectionId
        );
        
        res.json(sectionNotes);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 获取特定笔记
app.get('/api/notes/:noteId', (req, res) => {
    try {
        const note = notes[req.params.noteId];
        
        if (note) {
            res.json(note);
        } else {
            res.status(404).json({ error: 'Note not found' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 删除笔记
app.delete('/api/notes/:noteId', (req, res) => {
    try {
        const noteId = req.params.noteId;
        
        if (notes[noteId]) {
            delete notes[noteId];
            res.json({ success: true, message: 'Note deleted' });
        } else {
            res.status(404).json({ error: 'Note not found' });
        }
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// 404处理
app.use((req, res) => {
    res.status(404).json({ error: 'Route not found' });
});

// 错误处理中间件
app.use((err, req, res, next) => {
    console.error('Error:', err);
    res.status(500).json({ 
        error: 'Internal server error',
        message: err.message 
    });
});

// 启动服务器
app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
    console.log(`API endpoints available at http://localhost:${PORT}/api`);
});

module.exports = app;

