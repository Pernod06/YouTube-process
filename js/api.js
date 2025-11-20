// API服务层 - 统一管理所有数据请求
// Version: 2024-11-19 with getVideoChapters
class APIService {
    constructor(config) {
        this.config = config;
        this.baseUrl = config.getAPIConfig().BASE_URL;
        this.useLocalData = config.APP.USE_LOCAL_DATA;
        console.log('[API] APIService initialized with getVideoChapters method');
    }

    /**
     * 通用的fetch请求封装
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                // 可以添加认证token等
                // 'Authorization': `Bearer ${this.getToken()}`
            },
            ...options
        };

        try {
            const response = await fetch(url, defaultOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Request failed:', error);
            throw error;
        }
    }

    /**
     * 获取视频数据
     */
    async getVideoData(videoId = null) {
        if (this.useLocalData) {
            // 开发模式：从本地JSON文件加载
            return this.loadLocalData();
        } else {
            // 生产模式：从API获取
            const endpoint = videoId 
                ? `${this.config.getAPIConfig().VIDEO_ENDPOINT}/${videoId}`
                : this.config.getAPIConfig().VIDEO_ENDPOINT;
            return this.request(endpoint);
        }
    }


    /**
     * 发送聊天消息到 LLM
     */
    async sendChatMessage(message, videoContext = null) {
        const endpoint = this.config.CHAT.ENDPOINT;

        const requestBody = {
            message: message
        };

        // 如果启用了视频上下文，添加到请求中
        if (this.config.CHAT.SEND_VIDEO_CONTEXT && videoContext) {
            requestBody.video_context = videoContext;
        }

        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(
                () => controller.abort(),
                this.config.CHAT.TIMEOUT   
            );

            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data.response;
        } catch (error) {
            if (error.name === 'AbortErrpr') {
                throw new Error('plase try later');
            }
            console.error('Chat API failed:', error);
            throw error;
        }
    }

    /**
     * 获取 YouTube 视频详细信息
     * @param {string} videoId - 视频ID
     * @returns {Promise} - 返回视频详细信息
     */
    async getYouTubeVideoInfo(videoId) {
        const endpoint = `/video-info/${videoId}`;
        
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Get video info API failed:', error);
            throw error;
        }
    }

    /**
     * 获取视频章节列表
     * @param {string} videoId - 视频ID
     * @returns {Promise} - 返回章节数据
     */
    async getVideoChapters(videoId) {
        const endpoint = `/video-chapters/${videoId}`;
        
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Get chapters API failed:', error);
            throw error;
        }
    }

    /**
     * 批量提取视频关键帧
     * @param {string} videoId - 视频ID
     * @param {number[]} timestamps - 时间戳数组（秒）
     * @returns {Promise} - 返回关键帧数据
     */
    async extractVideoFrames(videoId, timestamps) {
        const endpoint = `/video-frames/${videoId}`;
        
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ timestamps })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            console.error('Extract frames API failed:', error);
            throw error;
        }
    }

    /**
     * 加载本地JSON数据
     */
    async loadLocalData() {
        try {
            const response = await fetch(this.config.LOCAL.DATA_PATH);
            if (!response.ok) {
                throw new Error(`Failed to load local data: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to load local data:', error);
            throw error;
        }
    }

    /**
     * 获取特定章节数据
     */
    async getSection(sectionId) {
        if (this.useLocalData) {
            const data = await this.loadLocalData();
            return data.sections.find(s => s.id === sectionId);
        } else {
            const endpoint = `${this.config.getAPIConfig().SECTIONS_ENDPOINT}/${sectionId}`;
            return this.request(endpoint);
        }
    }

    /**
     * 搜索章节
     */
    async searchSections(query) {
        if (this.useLocalData) {
            const data = await this.loadLocalData();
            return data.sections.filter(section => 
                section.title.toLowerCase().includes(query.toLowerCase()) ||
                section.content.toLowerCase().includes(query.toLowerCase())
            );
        } else {
            const endpoint = `${this.config.getAPIConfig().SECTIONS_ENDPOINT}/search`;
            return this.request(endpoint, {
                method: 'POST',
                body: JSON.stringify({ query })
            });
        }
    }

    /**
     * 保存用户笔记（示例后端接口）
     */
    async saveNote(sectionId, note) {
        if (this.useLocalData) {
            console.log('Note saved locally:', { sectionId, note });
            // 在实际应用中可以保存到 localStorage
            localStorage.setItem(`note_${sectionId}`, JSON.stringify(note));
            return { success: true };
        } else {
            return this.request('/notes', {
                method: 'POST',
                body: JSON.stringify({ sectionId, note })
            });
        }
    }

    /**
     * 获取用户笔记
     */
    async getNote(sectionId) {
        if (this.useLocalData) {
            const note = localStorage.getItem(`note_${sectionId}`);
            return note ? JSON.parse(note) : null;
        } else {
            return this.request(`/notes/${sectionId}`);
        }
    }

    /**
     * 获取YouTube视频评论
     */
    async getVideoComments(videoId, maxResults = 20) {
        try {
            const endpoint = `/videos/${videoId}/comments?maxResults=${maxResults}`;
            return await this.request(endpoint);
        } catch (error) {
            console.error('Failed to fetch comments:', error);
            throw error;
        }
    }

    /**
     * 生成 PDF 文档
     */
    async generatePDF() {
        try {
            const url = `${this.baseUrl}/generate-pdf`;
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/pdf',
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            // 获取 blob 数据
            const blob = await response.blob();
            
            // 从响应头获取文件名
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'video-document.pdf';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch && filenameMatch[1]) {
                    filename = filenameMatch[1].replace(/['"]/g, '');
                }
            }

            return { blob, filename };
        } catch (error) {
            console.error('Failed to generate PDF:', error);
            throw error;
        }
    }

    /**
     * 获取或设置认证token（示例）
     */
    setToken(token) {
        localStorage.setItem('auth_token', token);
    }

    getToken() {
        return localStorage.getItem('auth_token');
    }

    clearToken() {
        localStorage.removeItem('auth_token');
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = APIService;
}
