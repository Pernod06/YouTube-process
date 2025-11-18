// 主应用逻辑
class VideoPageApp {
    constructor(config) {
        this.config = config;
        this.apiService = new APIService(config);
        this.currentVideoData = null;
        this.player = null;
    }

    /**
     * 初始化应用
     */
    async init() {
        try {
            this.showLoading();
            
            // 加载视频数据
            this.currentVideoData = await this.apiService.getVideoData();
            
            // 渲染页面
            this.render();
            
            // 绑定事件
            this.bindEvents();
            
            // 初始化播放器
            this.initPlayer();
            
            this.hideLoading();

            this.initChat();
            
            // 初始化 Views 模块
            this.initViews();
        } catch (error) {
            this.showError('加载数据失败: ' + error.message);
        }
    }

    /**
     * 渲染页面内容
     */
    render() {
        const { videoInfo, sections } = this.currentVideoData;
        
        // 渲染标题
        this.renderTitle(videoInfo);
        
        // 渲染导航
        this.renderNavigation(sections);
        
        // 渲染主内容
        this.renderMainContent(sections);
        
        // 渲染视频播放器
        this.renderVideoPlayer(videoInfo);
    }

    /**
     * 渲染标题
     */
    renderTitle(videoInfo) {
        document.title = videoInfo.description;
        const titleElement = document.querySelector('#video-title');
        if (titleElement) {
            titleElement.textContent = videoInfo.title;
        }
        
        // 如果有缩略图URL，更新缩略图
        const thumbnailImg = document.querySelector('#video-thumbnail-img');
        if (thumbnailImg && videoInfo.thumbnail) {
            thumbnailImg.src = videoInfo.thumbnail;
        }
    }

    /**
     * 渲染导航栏
     */
    renderNavigation(sections) {
        const nav = document.querySelector('.sidebar-left nav');
        if (!nav) return;
        
        nav.innerHTML = sections.map(section => `
            <a href="#${section.id}" data-section-id="${section.id}">
                ${section.title}
            </a>
        `).join('');
    }

    /**
     * 渲染主内容区域
     */
    renderMainContent(sections) {
        const mainContent = document.querySelector('.main-content');
        if (!mainContent) return;
        
        // 保留视频头部区域（包括缩略图和标题）
        const videoHeader = mainContent.querySelector('.video-header');
        
        // 清空章节容器
        const sectionsContainer = document.querySelector('#sections-container');
        if (sectionsContainer) {
            sectionsContainer.innerHTML = '';
            
            // 渲染各个章节
            sections.forEach(section => {
                const sectionElement = this.createSectionElement(section);
                sectionsContainer.appendChild(sectionElement);
            });
        }
    }

    /**
     * 创建单个章节元素
     */
    createSectionElement(section) {
        const div = document.createElement('div');
        div.id = section.id;
        div.className = 'section';
        
        // 处理Markdown格式的粗体
        const content = this.parseMarkdown(section.content);
        
        div.innerHTML = `
            <h2>${section.title}</h2>
            <span class="timestamp-range" 
                  data-start="${section.timestampStart}" 
                  data-end="${section.timestampEnd}">
                [${section.timestampStart}] - [${section.timestampEnd}]
            </span>
            <p>${content}</p>
        `;
        
        return div;
    }

    /**
     * 简单的Markdown解析（粗体）
     */
    parseMarkdown(text) {
        // 将 **text** 转换为 <strong>text</strong>
        return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    }

    /**
     * 渲染视频播放器
     */
    renderVideoPlayer(videoInfo) {
        const playerContainer = document.querySelector('.video-player iframe');
        if (!playerContainer) return;
        
        const params = new URLSearchParams(this.config.YOUTUBE.DEFAULT_PARAMS);
        const embedUrl = `${this.config.YOUTUBE.EMBED_URL}${videoInfo.videoId}?${params.toString()}`;
        
        playerContainer.src = embedUrl;
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 导航点击事件
        this.bindNavigationEvents();
        
        // 时间戳点击事件
        this.bindTimestampEvents();
        
        // 滚动事件（高亮当前章节）
        this.bindScrollEvents();
    }

    /**
     * 导航点击事件
     */
    bindNavigationEvents() {
        const navLinks = document.querySelectorAll('.sidebar-left nav a');
        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const sectionId = link.getAttribute('data-section-id');
                this.scrollToSection(sectionId);
                
                // 更新active状态
                navLinks.forEach(l => l.classList.remove('active'));
                link.classList.add('active');
            });
        });
    }

    /**
     * 时间戳点击事件
     */
    bindTimestampEvents() {
        const timestamps = document.querySelectorAll('.timestamp-range');
        timestamps.forEach(timestamp => {
            timestamp.addEventListener('click', () => {
                const startTime = timestamp.getAttribute('data-start');
                this.seekVideo(startTime);
            });
        });
    }

    /**
     * 滚动事件
     */
    bindScrollEvents() {
        if (!this.config.APP.ENABLE_AUTO_SCROLL) return;
        
        let ticking = false;
        window.addEventListener('scroll', () => {
            if (!ticking) {
                window.requestAnimationFrame(() => {
                    this.updateActiveSection();
                    ticking = false;
                });
                ticking = true;
            }
        });
    }

    /**
     * 更新当前激活的章节
     */
    updateActiveSection() {
        const sections = document.querySelectorAll('.section');
        const navLinks = document.querySelectorAll('.sidebar-left nav a');
        
        let currentSection = null;
        sections.forEach(section => {
            const rect = section.getBoundingClientRect();
            if (rect.top <= 100 && rect.bottom >= 100) {
                currentSection = section.id;
            }
        });
        
        if (currentSection) {
            navLinks.forEach(link => {
                if (link.getAttribute('data-section-id') === currentSection) {
                    link.classList.add('active');
                } else {
                    link.classList.remove('active');
                }
            });
        }
    }

    /**
     * 滚动到指定章节
     */
    scrollToSection(sectionId) {
        const section = document.getElementById(sectionId);
        if (section) {
            section.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'start' 
            });
        }
    }

    /**
     * 跳转视频到指定时间
     */
    seekVideo(timeString) {
        // 将时间字符串转换为秒数
        const seconds = this.timeStringToSeconds(timeString);
        
        // 如果使用YouTube IFrame API
        if (this.player && this.player.seekTo) {
            this.player.seekTo(seconds, true);
        } else {
            // 简单方式：更新iframe src
            const iframe = document.querySelector('.video-player iframe');
            const currentSrc = iframe.src.split('?')[0];
            const params = new URLSearchParams(this.config.YOUTUBE.DEFAULT_PARAMS);
            params.set('start', seconds);
            iframe.src = `${currentSrc}?${params.toString()}`;
        }
    }

    /**
     * 时间字符串转秒数
     */
    timeStringToSeconds(timeString) {
        const parts = timeString.split(':').map(Number);
        if (parts.length === 2) {
            return parts[0] * 60 + parts[1];
        } else if (parts.length === 3) {
            return parts[0] * 3600 + parts[1] * 60 + parts[2];
        }
        return 0;
    }

    /**
     * 初始化YouTube播放器（可选：使用YouTube IFrame API）
     */
    initPlayer() {
        // 如果需要更高级的控制，可以使用YouTube IFrame API
        // 这里提供一个简单的实现
        console.log('Video player initialized');
    }

    /**
     * 显示加载状态
     */
    showLoading() {
        const sectionsContainer = document.querySelector('#sections-container');
        if (sectionsContainer) {
            sectionsContainer.innerHTML = '<div class="loading">加载中</div>';
        }
    }

    /**
     * 隐藏加载状态
     */
    hideLoading() {
        const loading = document.querySelector('.loading');
        if (loading) {
            loading.remove();
        }
    }

    /**
     * 显示错误信息
     */
    showError(message) {
        const mainContent = document.querySelector('.main-content');
        if (mainContent) {
            mainContent.innerHTML = `
                <div class="error">
                    <h3>错误</h3>
                    <p>${message}</p>
                    <button onclick="location.reload()">重新加载</button>
                </div>
            `;
        }
    }

    /**
     * 搜索功能（示例）
     */
    async search(query) {
        try {
            const results = await this.apiService.searchSections(query);
            console.log('Search results:', results);
            return results;
        } catch (error) {
            console.error('Search failed:', error);
            return [];
        }
    }
    /**
     * 初始化聊天功能
     */
    initChat() {
        const chatInput = document.getElementById('chat-input');
        const sendBtn = document.getElementById('chat-send-btn');
        const messagesContainer = document.getElementById('chat-messages');
    
        if (!chatInput || !sendBtn) return;
    
        // 发送消息函数
        const sendMessage = () => {
            const message = chatInput.value.trim();
            if (!message) return;

            // 添加用户消息
            this.addChatMessage(message, 'user');
             
            // 清空输入框
            chatInput.value = '';
            chatInput.style.height = 'auto';

            // 模拟机器人回复（这里可以接入真实的 API）
            setTimeout(async () => {
                await this.handleBotResponse(message);
            }, 500);
        };
    
        // 点击发送按钮
        sendBtn.addEventListener('click', sendMessage);
    
        // 按 Enter 发送（Shift+Enter 换行）
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    
        // 自动调整输入框高度
        chatInput.addEventListener('input', () => {
            chatInput.style.height = 'auto';
            chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
        });
    }
    
    /**
     * 添加聊天消息
     */
    addChatMessage(message, type = 'user') {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;
    
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${type}`;
            
        const avatar = type === 'user' ? '👤' : '🤖';
            
        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <p>${this.escapeHtml(message)}</p>
            </div>
        `;
    
        messagesContainer.appendChild(messageDiv);
            
        // 滚动到底部
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    /**
     * 处理机器人回复
     */
    async handleBotResponse(userMessage) {
        const useLLM = this.config.CHAT && this.config.CHAT.USE_LLM;

        if (useLLM) {
            // 使用后端 LLM
            try {
                this.showTypingIndicator();

                const videoContext = this.config.CHAT.SEND_VIDEO_CONTEXT ? {
                    title: this.currentVideoData.videoInfo.title,
                    videoId: this.currentVideoData.videoInfo.videoId,
                    sections: this.currentVideoData.sections.map(s => ({
                        id: s.id,
                        title: s.title,
                        timestamp: `${s.timestampStart} - ${s.timestampEnd}`
                    }))
                } : null;


                // 调用 LLM API
                const response = await this.apiService.sendChatMessage(
                    userMessage,
                    videoContext
                );
                
                this.removeTypingIndicator();

                this.addChatMessage(response, 'bot');

            } catch (error) {
                this.removeTypingIndicator();
                console.error('LLM response failed:', error);

                const failbackResponse = 'sorry!';
                this.addChatMessage(failbackResponse, 'bot');
            }
        } else {
            const message = userMessage.toLowerCase();
            let response = '';

            // 简单的关键词匹配（可以替换为 AI API 调用）
            if (message.includes('视频') || message.includes('内容')) {
                response = '这个视频讲述了 NVIDIA CEO Jensen Huang 在华盛顿 GTC 大会上的主题演讲，涵盖了 AI、加速计算、量子计算等主题。你可以点击左侧导航查看具体章节。';
            } else if (message.includes('时长') || message.includes('多久')) {
                response = '视频总时长约 1 小时 42 分钟，分为 10 个主要章节。';
            } else if (message.includes('章节') || message.includes('目录')) {
               response = '视频包含 10 个章节，从美国创新历史讲到 AI 工厂和企业转型。你可以点击任意章节标题快速跳转。';
            } else if (message.includes('搜索')) {
                response = '你可以使用浏览器的搜索功能 (Ctrl+F) 在页面中查找关键词，或者告诉我你想了解什么内容。';
            } else {
                response = `收到你的消息："${userMessage}"。我可以帮你介绍视频内容、查找特定章节或回答相关问题。有什么我可以帮你的吗？`;
            }
    
            this.addChatMessage(response, 'bot');
        }
    }
    
    /**
     * 显示"正在输入"指示器
     */
    showTypingIndicator() {
        const messagesContainer = document.getElementById('chat-messages');
        if (!messagesContainer) return;
        
        const typingDiv = document.createElement('div');
        typingDiv.className = 'chat-message bot typing-indicator';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="message-avatar">🤖</div>
            <div class="message-content typing">
                <span></span>
                <span></span>
                <span></span>
            </div>
        `;
        
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    /**
     * 移除"正在输入"指示器
     */
    removeTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * 转义 HTML 防止 XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 初始化 Views 模块
     */
    initViews() {
        const viewItems = document.querySelectorAll('.view-item');
        
        if (!viewItems.length) return;
        
        viewItems.forEach(item => {
            item.addEventListener('click', () => {
                const viewType = item.getAttribute('data-view');
                
                // 移除所有 active 状态
                viewItems.forEach(v => v.classList.remove('active'));
                
                // 添加当前 active 状态
                item.classList.add('active');
                
                // 处理不同的视图切换
                this.handleViewChange(viewType);
            });
        });
    }

    /**
     * 处理视图切换
     */
    handleViewChange(viewType) {
        console.log(`Switching to view: ${viewType}`);
        
        switch(viewType) {
            case 'wiki':
                this.showWikiView();
                break;
            case 'pdf':
                this.showPdfView();
                break;
            case 'mindmap':
                this.showMindMapView();
                break;
            case 'comments':
                this.showCommentsView();
                break;
            default:
                console.warn(`Unknown view type: ${viewType}`);
        }
    }

    /**
     * 显示 Wiki 视图
     */
    showWikiView() {
        // TODO: 实现 Wiki 视图
        console.log('Wiki view activated');
        this.showViewPlaceholder('Wiki', '📚', '维基百科式的内容展示');
    }

    /**
     * 显示 PDF 视图
     */
    async showPdfView() {
        console.log('PDF view activated');
        
        const mainContent = document.querySelector('.main-content');
        if (!mainContent) return;
        
        // 保存当前内容
        if (!this.originalContent) {
            this.originalContent = mainContent.innerHTML;
        }
        
        // 显示加载状态
        mainContent.innerHTML = `
            <div class="pdf-view">
                <div class="pdf-header">
                    <h2><span class="view-icon">📄</span> PDF 文档生成</h2>
                    <button class="back-to-content-btn" onclick="videoApp.restoreOriginalContent()">
                        ← 返回视频内容
                    </button>
                </div>
                <div class="pdf-loading">
                    <div class="loading-spinner"></div>
                    <p>正在生成 PDF 文档...</p>
                </div>
            </div>
        `;
        
        try {
            // 调用后端 API 生成 PDF
            const { blob, filename } = await this.apiService.generatePDF();
            
            // 创建 PDF 预览 URL
            const pdfUrl = URL.createObjectURL(blob);
            
            // 渲染 PDF 查看器
            mainContent.innerHTML = `
                <div class="pdf-view">
                    <div class="pdf-header">
                        <h2><span class="view-icon">📄</span> PDF 文档</h2>
                        <div class="pdf-actions">
                            <button class="pdf-download-btn" id="pdf-download-btn">
                                <span>⬇️</span> 下载 PDF
                            </button>
                            <button class="back-to-content-btn" onclick="videoApp.restoreOriginalContent()">
                                ← 返回视频内容
                            </button>
                        </div>
                    </div>
                    <div class="pdf-viewer-container">
                        <iframe 
                            src="${pdfUrl}" 
                            class="pdf-viewer"
                            type="application/pdf"
                            width="100%" 
                            height="800px">
                            <p>您的浏览器不支持 PDF 预览。
                                <a href="${pdfUrl}" download="${filename}">点击这里下载 PDF</a>
                            </p>
                        </iframe>
                    </div>
                </div>
            `;
            
            // 绑定下载按钮事件
            const downloadBtn = document.getElementById('pdf-download-btn');
            if (downloadBtn) {
                downloadBtn.addEventListener('click', () => {
                    const link = document.createElement('a');
                    link.href = pdfUrl;
                    link.download = filename;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                });
            }
            
            // 保存 URL 以便后续清理
            this.currentPdfUrl = pdfUrl;
            
        } catch (error) {
            console.error('Failed to generate PDF:', error);
            mainContent.innerHTML = `
                <div class="pdf-view">
                    <div class="pdf-header">
                        <h2><span class="view-icon">📄</span> PDF 文档</h2>
                        <button class="back-to-content-btn" onclick="videoApp.restoreOriginalContent()">
                            ← 返回视频内容
                        </button>
                    </div>
                    <div class="pdf-error">
                        <div class="error-icon">⚠️</div>
                        <h3>无法生成 PDF</h3>
                        <p>${error.message}</p>
                        <p class="error-hint">请确保后端服务已启动并安装了必要的依赖</p>
                        <button class="retry-btn" onclick="videoApp.showPdfView()">
                            重试
                        </button>
                    </div>
                </div>
            `;
        }
    }

    /**
     * 显示思维导图视图
     */
    showMindMapView() {
        // TODO: 实现思维导图视图
        console.log('Mind Map view activated');
        this.showViewPlaceholder('Mind Map', '🗺️', '思维导图可视化');
    }

    /**
     * 显示评论视图
     */
    async showCommentsView() {
        console.log('Comments view activated');
        
        const mainContent = document.querySelector('.main-content');
        if (!mainContent) return;
        
        // 保存当前内容
        if (!this.originalContent) {
            this.originalContent = mainContent.innerHTML;
        }
        
        // 显示加载状态
        mainContent.innerHTML = `
            <div class="comments-view">
                <div class="comments-header">
                    <h2><span class="view-icon">💬</span> 视频评论</h2>
                    <button class="back-to-content-btn" onclick="videoApp.restoreOriginalContent()">
                        ← 返回视频内容
                    </button>
                </div>
                <div class="comments-loading">
                    <div class="loading-spinner"></div>
                    <p>正在加载评论...</p>
                </div>
            </div>
        `;
        
        try {
            // 获取视频ID
            const videoId = this.currentVideoData?.videoInfo?.videoId;
            if (!videoId) {
                throw new Error('视频ID不存在');
            }
            
            // 调用后端API获取YouTube评论
            const response = await this.apiService.getVideoComments(videoId, 50);
            console.log(videoId);
            
            // 渲染评论
            this.renderComments(response);
            
        } catch (error) {
            console.error('Failed to load comments:', error);
            mainContent.innerHTML = `
                <div class="comments-view">
                    <div class="comments-header">
                        <h2><span class="view-icon">💬</span> 视频评论</h2>
                        <button class="back-to-content-btn" onclick="videoApp.restoreOriginalContent()">
                            ← 返回视频内容
                        </button>
                    </div>
                    <div class="comments-error">
                        <div class="error-icon">⚠️</div>
                        <h3>无法加载评论</h3>
                        <p>${error.message}</p>
                        <p class="error-hint">请确保后端服务已启动并配置了YouTube API密钥</p>
                    </div>
                </div>
            `;
        }
    }

    /**
     * 渲染评论列表
     */
    renderComments(response) {
        const mainContent = document.querySelector('.main-content');
        if (!mainContent) return;
        
        const comments = response.comments || [];
        const total = response.total || 0;
        
        let commentsHTML = '';
        
        if (comments.length === 0) {
            commentsHTML = `
                <div class="no-comments">
                    <div class="no-comments-icon">💭</div>
                    <p>该视频暂无评论或评论已关闭</p>
                </div>
            `;
        } else {
            commentsHTML = comments.map((comment, index) => `
                <div class="comment-item" data-index="${index}">
                    <div class="comment-header">
                        <div class="comment-author">
                            <span class="author-avatar">👤</span>
                            <span class="author-name">${this.escapeHtml(comment.author)}</span>
                        </div>
                        <div class="comment-meta">
                            <span class="comment-likes">👍 ${comment.like_count || 0}</span>
                            <span class="comment-date">${this.formatCommentDate(comment.published_at)}</span>
                        </div>
                    </div>
                    <div class="comment-text">
                        ${this.formatCommentText(comment.text)}
                    </div>
                </div>
            `).join('');
        }
        
        mainContent.innerHTML = `
            <div class="comments-view">
                <div class="comments-header">
                    <h2><span class="view-icon">💬</span> 视频评论 <span class="comment-count">(${total})</span></h2>
                    <button class="back-to-content-btn" onclick="videoApp.restoreOriginalContent()">
                        ← 返回视频内容
                    </button>
                </div>
                <div class="comments-container">
                    ${commentsHTML}
                </div>
            </div>
        `;
    }

    /**
     * 格式化评论文本（保留换行和链接）
     */
    formatCommentText(text) {
        if (!text) return '';
        
        // 转义HTML
        let formattedText = this.escapeHtml(text);
        
        // 转换换行符为<br>
        formattedText = formattedText.replace(/\n/g, '<br>');
        
        // 转换URL为链接
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        formattedText = formattedText.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
        
        return formattedText;
    }

    /**
     * 格式化评论日期
     */
    formatCommentDate(dateString) {
        if (!dateString) return '';
        
        try {
            const date = new Date(dateString);
            const now = new Date();
            const diffMs = now - date;
            const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
            
            if (diffDays === 0) {
                const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
                if (diffHours === 0) {
                    const diffMinutes = Math.floor(diffMs / (1000 * 60));
                    return diffMinutes <= 1 ? '刚刚' : `${diffMinutes}分钟前`;
                }
                return `${diffHours}小时前`;
            } else if (diffDays === 1) {
                return '昨天';
            } else if (diffDays < 7) {
                return `${diffDays}天前`;
            } else if (diffDays < 30) {
                const weeks = Math.floor(diffDays / 7);
                return `${weeks}周前`;
            } else if (diffDays < 365) {
                const months = Math.floor(diffDays / 30);
                return `${months}个月前`;
            } else {
                const years = Math.floor(diffDays / 365);
                return `${years}年前`;
            }
        } catch (e) {
            return dateString;
        }
    }

    /**
     * 显示视图占位符
     */
    showViewPlaceholder(title, icon, description) {
        const mainContent = document.querySelector('.main-content');
        if (!mainContent) return;
        
        // 保存当前内容（如果需要切换回来）
        if (!this.originalContent) {
            this.originalContent = mainContent.innerHTML;
        }
        
        mainContent.innerHTML = `
            <div class="view-placeholder">
                <div class="view-placeholder-icon">${icon}</div>
                <h2>${title} 视图</h2>
                <p>${description}</p>
                <button class="back-to-content-btn" onclick="videoApp.restoreOriginalContent()">
                    返回视频内容
                </button>
            </div>
        `;
    }

    /**
     * 恢复原始内容
     */
    restoreOriginalContent() {
        const mainContent = document.querySelector('.main-content');
        if (!mainContent || !this.originalContent) return;
        
        mainContent.innerHTML = this.originalContent;
        
        // 移除所有 view-item 的 active 状态
        const viewItems = document.querySelectorAll('.view-item');
        viewItems.forEach(item => item.classList.remove('active'));
        
        // 重新绑定事件
        this.bindEvents();
    }
}

// 当DOM加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    const app = new VideoPageApp(CONFIG);
    app.init();
    
    // 将app实例挂载到window对象，方便调试
    window.videoApp = app;
});
