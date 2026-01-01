// 主应用逻辑
class VideoPageApp {
    constructor(config) {
        this.config = config;
        this.apiService = new APIService(config);
        this.currentVideoData = null;
        this.player = null;
        this.currentSectionIndex = 0;
        this.totalSections = 0;
        this.youtubePlayer = null;
        this.playerReady = false;
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
            
            // 初始化关键帧提取功能
            this.initChapterFrames();
            
            // 初始化章节弹窗
            this.initChapterModal();
            
            // 加载视频描述
            // await this.loadVideoDescription();
            
            // 初始化布局交换按钮
            this.initLayoutSwap();
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
        
        // 加载视频摘要
        const descriptionEl = document.getElementById('video-description');
        if (descriptionEl && videoInfo.summary) {
            descriptionEl.innerHTML = `<p>${videoInfo.summary}</p>`;
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
            
            // 渲染所有章节，直接展示
            sections.forEach((section, index) => {
                const sectionElement = this.createSectionElement(section);
                // 所有章节都显示，不需要 active 类
                sectionsContainer.appendChild(sectionElement);
            });
            
            // 保存总章节数（用于其他功能）
            this.totalSections = sections.length;
        }
    }

    /**
     * 创建单个章节元素
     */
    createSectionElement(section) {
        const div = document.createElement('div');
        div.id = section.id;
        div.className = 'section';
        
        // 检查内容是字符串还是数组
        let contentHTML = '';
        
        if (Array.isArray(section.content)) {
            // 新格式：content 是数组，每个句子作为 span 连续显示
            contentHTML = '<div class="content-paragraph">';
            section.content.forEach((item, index) => {
                const parsedContent = this.parseMarkdown(item.content);
                contentHTML += `<span class="sentence-span" 
                                     draggable="true"
                                     data-timestamp="${item.timestampStart}"
                                     data-content="${this.escapeHtml(item.content)}"
                                     data-index="${index}"
                                     title="点击跳转 | 拖拽到聊天框">${parsedContent}</span> `;
            });
            contentHTML += '</div>';
        } else {
            // 旧格式：content 是字符串
            const content = this.parseMarkdown(section.content);
            const timestamps = (section.timestampStart && section.timestampEnd) 
                ? `<span class="timestamp-range" 
                          data-start="${section.timestampStart}" 
                          data-end="${section.timestampEnd}">
                        [${section.timestampStart}] - [${section.timestampEnd}]
                   </span>`
                : '';
            contentHTML = `${timestamps}<p>${content}</p>`;
        }
        
        div.innerHTML = `
            <h2>${section.title}</h2>
            ${contentHTML}
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
     * HTML 转义
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 渲染视频播放器
     */
    renderVideoPlayer(videoInfo) {
        const playerContainer = document.querySelector('.video-player iframe');
        if (!playerContainer) return;
        
        const params = new URLSearchParams(this.config.YOUTUBE.DEFAULT_PARAMS);
        
        // 确保启用 JavaScript API
        if (!params.has('enablejsapi')) {
            params.set('enablejsapi', '1');
        }
        
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
        navLinks.forEach((link, index) => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                
                // 获取目标章节ID
                const sectionId = link.getAttribute('data-section-id');
                const targetSection = document.getElementById(sectionId);
                
                if (targetSection) {
                    // 平滑滚动到目标章节
                    targetSection.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'start' 
                    });
                }
                
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
        // 旧格式：时间戳范围点击
        const timestamps = document.querySelectorAll('.timestamp-range');
        timestamps.forEach(timestamp => {
            timestamp.addEventListener('click', () => {
                const startTime = timestamp.getAttribute('data-start');
                this.seekVideo(startTime);
            });
        });
        
        // 新格式：可点击的句子（span格式）
        const sentenceSpans = document.querySelectorAll('.sentence-span');
        sentenceSpans.forEach(span => {
            // 点击事件
            span.addEventListener('click', () => {
                const timestamp = span.getAttribute('data-timestamp');
                console.log('[INFO] 点击句子，跳转到:', timestamp);
                this.seekVideo(timestamp);
                
                // 添加视觉反馈（短暂高亮）
                sentenceSpans.forEach(s => s.classList.remove('active'));
                span.classList.add('active');
            });
            
            // 拖拽开始事件
            span.addEventListener('dragstart', (e) => {
                const content = span.getAttribute('data-content');
                e.dataTransfer.setData('text/plain', content);
                e.dataTransfer.effectAllowed = 'copy';
                span.classList.add('dragging');
                console.log('[INFO] 开始拖拽句子:', content);
            });
            
            // 拖拽结束事件
            span.addEventListener('dragend', (e) => {
                span.classList.remove('dragging');
            });
        });
    }

    /**
     * 滚动事件
     */
    bindScrollEvents() {
        if (!this.config.APP.ENABLE_AUTO_SCROLL) return;
        
        // 监听章节容器的滚动
        const sectionsContainer = document.querySelector('.sections-container-carousel');
        if (!sectionsContainer) return;
        
        let ticking = false;
        sectionsContainer.addEventListener('scroll', () => {
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
        
        // 使用统一的跳转方法
        this.seekToTimestamp(seconds);
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
     * 初始化YouTube播放器（使用YouTube IFrame API）
     */
    initPlayer() {
        // 加载 YouTube IFrame API
        if (!window.YT) {
            const tag = document.createElement('script');
            tag.src = 'https://www.youtube.com/iframe_api';
            const firstScriptTag = document.getElementsByTagName('script')[0];
            firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
        }
        
        // 等待 API 就绪
        window.onYouTubeIframeAPIReady = () => {
            this.initYouTubePlayer();
        };
        
        // 如果 API 已经加载，直接初始化
        if (window.YT && window.YT.Player) {
            this.initYouTubePlayer();
        }
        
        console.log('Video player initialized');
    }

    /**
     * 初始化 YouTube Player 对象
     */
    initYouTubePlayer() {
        const iframe = document.getElementById('video-iframe');
        if (!iframe) {
            console.warn('[WARN] 找不到 video iframe');
            return;
        }

        try {
            this.youtubePlayer = new YT.Player('video-iframe', {
                events: {
                    'onReady': (event) => {
                        console.log('[SUCCESS] YouTube Player 已就绪');
                        this.playerReady = true;
                    },
                    'onStateChange': (event) => {
                        // 可以在这里添加播放状态变化的处理
                    }
                }
            });
        } catch (error) {
            console.error('[ERROR] 初始化 YouTube Player 失败:', error);
        }
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

        // 拖拽目标事件处理
        chatInput.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'copy';
            chatInput.classList.add('drag-over');
        });

        chatInput.addEventListener('dragleave', (e) => {
            chatInput.classList.remove('drag-over');
        });

        chatInput.addEventListener('drop', (e) => {
            e.preventDefault();
            chatInput.classList.remove('drag-over');
            
            const droppedText = e.dataTransfer.getData('text/plain');
            if (droppedText) {
                // 在光标位置插入文本
                const start = chatInput.selectionStart;
                const end = chatInput.selectionEnd;
                const currentValue = chatInput.value;
                
                const newValue = currentValue.substring(0, start) + droppedText + currentValue.substring(end);
                chatInput.value = newValue;
                
                // 设置光标位置到插入文本之后
                const newCursorPos = start + droppedText.length;
                chatInput.setSelectionRange(newCursorPos, newCursorPos);
                
                // 触发 input 事件以调整高度
                chatInput.dispatchEvent(new Event('input'));
                chatInput.focus();
                
                console.log('[INFO] 句子已拖拽到聊天框:', droppedText);
            }
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
        this.showViewPlaceholder('Related', '🔗', 'Related Videos');
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
     * 显示思维导图视图 (使用 Mermaid.js)
     */
    async showMindMapView() {
        console.log('Mind Map view activated (Mermaid.js)');
        
        const mainContent = document.querySelector('.main-content');
        if (!mainContent) return;
        
        // 保存当前内容
        if (!this.originalContent) {
            this.originalContent = mainContent.innerHTML;
        }
        
        // 显示加载状态
        mainContent.innerHTML = `
            <div class="mindmap-view">
                <div class="mindmap-header">
                    <h2><span class="view-icon">🗺️</span> 思维导图 (Mermaid)</h2>
                    <button class="back-to-content-btn" onclick="videoApp.restoreOriginalContent()">
                        ← 返回视频内容
                    </button>
                </div>
                <div class="mindmap-loading">
                    <div class="loading-spinner"></div>
                    <p>正在生成思维导图，请稍候...</p>
                    <p class="loading-hint">AI 正在分析视频内容并生成结构化思维导图</p>
                </div>
            </div>
        `;
        
        try {
            // 加载 Mermaid 库（如果尚未加载）
            await this.loadMermaidLibrary();
            
            // 调用后端 API 生成思维导图
            const result = await this.apiService.generateMindMap();
            
            console.log('[DEBUG] API 返回结果:', result);
            
            // 检查返回结果
            if (!result) {
                throw new Error('API 返回结果为空');
            }
            
            if (!result.success) {
                throw new Error(result.message || result.error || '生成失败');
            }
            
            if (!result.mermaid || result.mermaid === 'undefined' || result.mermaid.trim() === '') {
                throw new Error('AI 返回的内容为空或无效，请重试');
            }
            
            console.log('[SUCCESS] 思维导图生成成功');
            
            // 渲染思维导图
            this.renderMermaidMindMap(result.mermaid, result.videoTitle);
            
        } catch (error) {
            console.error('Failed to generate mindmap:', error);
            
            // 确定错误消息
            let errorMessage = error.message || '未知错误';
            let errorHint = '请确保后端服务已启动并配置了 OpenAI API 密钥';
            
            // 根据错误类型提供更具体的提示
            if (errorMessage.includes('API 密钥')) {
                errorHint = '请在后端 .env 文件中配置 OPENAI_API_KEY';
            } else if (errorMessage.includes('网络') || errorMessage.includes('fetch')) {
                errorHint = '请检查后端服务是否运行在 http://localhost:5500';
            } else if (errorMessage.includes('空') || errorMessage.includes('undefined')) {
                errorHint = 'AI 生成内容失败，可能是 API 配额不足或网络问题，请重试';
            }
            
            mainContent.innerHTML = `
                <div class="mindmap-view">
                    <div class="mindmap-header">
                        <h2><span class="view-icon">🗺️</span> 思维导图</h2>
                        <button class="back-to-content-btn" onclick="videoApp.restoreOriginalContent()">
                            ← 返回视频内容
                        </button>
                    </div>
                    <div class="mindmap-error">
                        <div class="error-icon">⚠️</div>
                        <h3>无法生成思维导图</h3>
                        <p class="error-message">${errorMessage}</p>
                        <p class="error-hint">${errorHint}</p>
                        <button class="retry-btn" onclick="videoApp.showMindMapView()">
                            重试
                        </button>
                    </div>
                </div>
            `;
        }
    }

    /**
     * 动态加载 Mermaid 库
     */
    async loadMermaidLibrary() {
        // 检查是否已加载
        if (window.mermaid) {
            console.log('[INFO] Mermaid 库已加载');
            return;
        }
        
        console.log('[INFO] 正在加载 Mermaid 库...');
        
        try {
            // 加载 Mermaid (从 CDN)
            await this.loadScript('https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js');
            
            // 等待初始化
            await new Promise(resolve => setTimeout(resolve, 200));
            
            // 验证并初始化
            if (window.mermaid) {
                // 初始化 Mermaid - 优化显示大小和布局均匀性
                mermaid.initialize({ 
                    startOnLoad: false,
                    theme: 'default',
                    themeVariables: {
                        fontSize: '16px',
                        fontFamily: 'Arial, sans-serif, "Microsoft YaHei"'
                    },
                    mindmap: {
                        padding: 40,
                        useMaxWidth: false,
                        nodeSpacing: 80,     // 节点横向间距
                        levelSpacing: 120,   // 层级纵向间距
                        diagramPadding: 20
                    },
                    flowchart: {
                        curve: 'basis',
                        nodeSpacing: 50,
                        rankSpacing: 50
                    }
                });
                console.log('[SUCCESS] ✅ Mermaid 库加载并初始化成功！');
            } else {
                throw new Error('Mermaid 库加载失败');
            }
        } catch (error) {
            console.error('[ERROR] Mermaid 库加载失败:', error);
            throw new Error('无法加载 Mermaid 库，请检查网络连接');
        }
    }

    /**
     * 动态加载 Markmap 库 (已弃用，保留以防需要)
     */
    async loadMarkmapLibrary() {
        // 检查是否已加载
        if (window.markmap && window.markmap.Transformer && window.markmap.Markmap) {
            console.log('[INFO] Markmap 库已加载');
            return;
        }
        
        console.log('[INFO] 正在加载 Markmap 库...');
        
        // 定义加载源（优先本地，然后 CDN）
        const loadSources = [
            {
                name: '本地文件 (standalone)',
                d3: '/libs/d3.v7.min.js',
                markmap: '/libs/markmap-view.min.js'
            },
            {
                name: 'jsdelivr (standalone)',
                d3: 'https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js',
                markmap: 'https://cdn.jsdelivr.net/npm/markmap-view@0.15.4/dist/index.min.js'
            },
            {
                name: 'unpkg (standalone)',
                d3: 'https://unpkg.com/d3@7/dist/d3.min.js',
                markmap: 'https://unpkg.com/markmap-view@0.15.4/dist/index.min.js'
            }
        ];
        
        let lastError = null;
        
        // 尝试不同的加载源
        for (const source of loadSources) {
            try {
                console.log(`[INFO] 尝试从 ${source.name} 加载...`);
                
                // 加载 d3（markmap 的依赖）
                await this.loadScript(source.d3);
                console.log(`[INFO] ✓ D3 从 ${source.name} 加载完成`);
                
                // 加载 markmap-view（包含 Transformer 和 Markmap）
                await this.loadScript(source.markmap);
                console.log(`[INFO] ✓ markmap-view 从 ${source.name} 加载完成`);
                
                // 等待库初始化（增加等待时间）
                await new Promise(resolve => setTimeout(resolve, 500));
                
                // 调试：查看 window 对象
                console.log('[DEBUG] window.markmap =', window.markmap);
                console.log('[DEBUG] typeof window.markmap =', typeof window.markmap);
                
                // 验证库是否正确加载
                if (window.markmap) {
                    console.log('[DEBUG] markmap.Transformer =', window.markmap.Transformer);
                    console.log('[DEBUG] markmap.Markmap =', window.markmap.Markmap);
                    
                    if (window.markmap.Transformer && window.markmap.Markmap) {
                        console.log(`[SUCCESS] ✅ Markmap 库从 ${source.name} 加载成功！`);
                        return;
                    } else {
                        console.warn(`[WARNING] markmap 对象存在但缺少 Transformer 或 Markmap`);
                    }
                } else {
                    console.warn(`[WARNING] window.markmap 未定义`);
                }
                
                console.warn(`[WARNING] ${source.name} 加载后验证失败，尝试下一个源...`);
                
            } catch (error) {
                console.error(`[ERROR] 从 ${source.name} 加载失败:`, error);
                lastError = error;
                // 继续尝试下一个加载源
            }
        }
        
        // 所有源都失败了
        const errorMsg = '无法从任何源加载思维导图库。\n请检查：\n1. 运行 ./download-markmap-standalone.sh\n2. 网络连接\n3. 浏览器控制台获取详细错误\n最后错误: ' + (lastError?.message || '未知');
        throw new Error(errorMsg);
    }

    /**
     * 动态加载脚本
     */
    loadScript(src) {
        return new Promise((resolve, reject) => {
            // 检查是否已加载
            const existingScript = document.querySelector(`script[src="${src}"]`);
            if (existingScript) {
                console.log(`[INFO] 脚本已存在: ${src}`);
                resolve();
                return;
            }
            
            const script = document.createElement('script');
            script.src = src;
            script.async = false; // 确保按顺序加载
            script.onload = () => {
                console.log(`[SUCCESS] 脚本加载成功: ${src}`);
                resolve();
            };
            script.onerror = (error) => {
                console.error(`[ERROR] 脚本加载失败: ${src}`, error);
                reject(new Error(`Failed to load script: ${src}`));
            };
            document.head.appendChild(script);
        });
    }

    /**
     * 渲染 Mermaid 思维导图
     */
    async renderMermaidMindMap(mermaidCode, videoTitle) {
        const mainContent = document.querySelector('.main-content');
        if (!mainContent) return;
        
        // 生成唯一 ID
        const mindmapId = 'mermaid-mindmap-' + Date.now();
        
        // 创建思维导图容器
        mainContent.innerHTML = `
            <div class="mindmap-view">
                <div class="mindmap-header">
                    <h2><span class="view-icon">🗺️</span> 思维导图</h2>
                    <div class="mindmap-actions">
                        <button class="mindmap-zoom-btn" onclick="videoApp.zoomMindMap('in')" title="放大">
                            <span>+</span>
                        </button>
                        <span class="zoom-level" id="zoom-level">120%</span>
                        <button class="mindmap-zoom-btn" onclick="videoApp.zoomMindMap('out')" title="缩小">
                            <span>-</span>
                        </button>
                        <button class="mindmap-zoom-btn" onclick="videoApp.zoomMindMap('reset')" title="重置">
                            <span>↺</span>
                        </button>
                        <button class="mindmap-download-btn" id="mindmap-download" title="下载">
                            <span>⬇️</span>
                        </button>
                        <button class="back-to-content-btn" onclick="videoApp.restoreOriginalContent()">
                            ← 返回
                        </button>
                    </div>
                </div>
                <div class="mindmap-container" id="mindmap-container">
                    <div class="mermaid-wrapper" id="mermaid-wrapper">
                        <pre class="mermaid" id="${mindmapId}">${mermaidCode}</pre>
                    </div>
                </div>
            </div>
        `;
        
        // 保存代码用于下载
        this.currentMindMapCode = mermaidCode;
        this.currentZoomLevel = 1.0;
        
        try {
            console.log('[INFO] 开始渲染 Mermaid 思维导图...');
            
            // 使用 Mermaid 渲染
            await mermaid.run({
                querySelector: `#${mindmapId}`
            });
            
            console.log('[SUCCESS] ✅ Mermaid 思维导图渲染完成');
            
            // 应用初始缩放（放大以便更清晰）
            this.applyMindMapZoom(1.2);
            
            // 绑定所有交互功能
            this.bindMermaidControls();
            this.enableMindMapPan();
            this.enableMindMapWheelZoom();
            this.enableMindMapKeyboardShortcuts();
            this.enableMindMapDoubleClickReset();
            
        } catch (error) {
            console.error('[ERROR] Mermaid 渲染失败:', error);
            throw new Error('思维导图渲染失败: ' + error.message);
        }
    }

    /**
     * 绑定 Mermaid 控制按钮
     */
    bindMermaidControls() {
        const downloadBtn = document.getElementById('mindmap-download');
        
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                this.downloadMindMapCode();
            });
        }
    }

    /**
     * 缩放思维导图
     */
    zoomMindMap(direction, delta = 0.2) {
        const oldLevel = this.currentZoomLevel;
        
        if (direction === 'in') {
            this.currentZoomLevel = Math.min(this.currentZoomLevel + delta, 3.0);
        } else if (direction === 'out') {
            this.currentZoomLevel = Math.max(this.currentZoomLevel - delta, 0.5);
        } else if (direction === 'reset') {
            this.currentZoomLevel = 1.2;
        }
        
        // 只有当缩放级别改变时才应用
        if (Math.abs(oldLevel - this.currentZoomLevel) > 0.01) {
            this.applyMindMapZoom(this.currentZoomLevel);
        }
    }

    /**
     * 应用缩放
     */
    applyMindMapZoom(scale) {
        const wrapper = document.getElementById('mermaid-wrapper');
        const zoomLevelEl = document.getElementById('zoom-level');
        
        if (wrapper) {
            wrapper.style.transform = `scale(${scale})`;
            wrapper.style.transformOrigin = 'top center';
            wrapper.style.transition = 'transform 0.2s ease-out';
            console.log(`[INFO] 缩放级别: ${scale.toFixed(1)}x`);
        }
        
        // 更新缩放比例显示
        if (zoomLevelEl) {
            zoomLevelEl.textContent = `${Math.round(scale * 100)}%`;
            
            // 添加动画效果
            zoomLevelEl.style.transform = 'scale(1.2)';
            setTimeout(() => {
                zoomLevelEl.style.transform = 'scale(1)';
            }, 200);
        }
    }

    /**
     * 启用拖拽平移
     */
    enableMindMapPan() {
        const container = document.getElementById('mindmap-container');
        if (!container) return;

        let isDragging = false;
        let startX, startY, scrollLeft, scrollTop;

        container.addEventListener('mousedown', (e) => {
            // 只在空白区域拖拽
            if (e.target === container || e.target.closest('.mermaid-wrapper')) {
                isDragging = true;
                container.style.cursor = 'grabbing';
                startX = e.pageX - container.offsetLeft;
                startY = e.pageY - container.offsetTop;
                scrollLeft = container.scrollLeft;
                scrollTop = container.scrollTop;
            }
        });

        container.addEventListener('mouseleave', () => {
            isDragging = false;
            container.style.cursor = 'default';
        });

        container.addEventListener('mouseup', () => {
            isDragging = false;
            container.style.cursor = 'default';
        });

        container.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            e.preventDefault();
            const x = e.pageX - container.offsetLeft;
            const y = e.pageY - container.offsetTop;
            const walkX = (x - startX) * 1.5;
            const walkY = (y - startY) * 1.5;
            container.scrollLeft = scrollLeft - walkX;
            container.scrollTop = scrollTop - walkY;
        });
    }

    /**
     * 启用鼠标滚轮缩放
     */
    enableMindMapWheelZoom() {
        const container = document.getElementById('mindmap-container');
        if (!container) return;

        container.addEventListener('wheel', (e) => {
            // 按住 Ctrl 键或单独滚轮都可以缩放
            if (e.ctrlKey || !e.shiftKey) {
                e.preventDefault();
                
                const delta = e.deltaY > 0 ? -0.1 : 0.1;
                const direction = delta > 0 ? 'in' : 'out';
                
                this.zoomMindMap(direction, Math.abs(delta));
            }
        }, { passive: false });

        console.log('[INFO] ✅ 鼠标滚轮缩放已启用');
    }

    /**
     * 启用键盘快捷键
     */
    enableMindMapKeyboardShortcuts() {
        const handleKeyPress = (e) => {
            // 只在思维导图视图中生效
            if (!document.getElementById('mermaid-wrapper')) return;
            
            switch(e.key) {
                case '+':
                case '=':
                    e.preventDefault();
                    this.zoomMindMap('in');
                    break;
                case '-':
                case '_':
                    e.preventDefault();
                    this.zoomMindMap('out');
                    break;
                case '0':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        this.zoomMindMap('reset');
                    }
                    break;
            }
        };

        // 移除旧的监听器（如果存在）
        if (this.keyboardHandler) {
            document.removeEventListener('keydown', this.keyboardHandler);
        }
        
        this.keyboardHandler = handleKeyPress;
        document.addEventListener('keydown', this.keyboardHandler);

        console.log('[INFO] ✅ 键盘快捷键已启用 (+/- 缩放, Ctrl+0 重置)');
    }

    /**
     * 启用双击重置
     */
    enableMindMapDoubleClickReset() {
        const container = document.getElementById('mindmap-container');
        if (!container) return;

        container.addEventListener('dblclick', (e) => {
            // 不在按钮上双击
            if (!e.target.closest('button')) {
                this.zoomMindMap('reset');
                console.log('[INFO] 双击重置缩放');
            }
        });

        console.log('[INFO] ✅ 双击重置已启用');
    }

    /**
     * 下载思维导图源码
     */
    downloadMindMapCode() {
        if (!this.currentMindMapCode) {
            console.error('No mindmap code to download');
            return;
        }
        
        const blob = new Blob([this.currentMindMapCode], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `mindmap_${new Date().toISOString().slice(0, 10)}.mmd`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(url);
        console.log('[INFO] 思维导图源码已下载');
    }

    /**
     * 渲染思维导图 (Markmap - 已弃用)
     */
    renderMindMap(markdown, videoTitle) {
        const mainContent = document.querySelector('.main-content');
        if (!mainContent) return;
        
        // 创建思维导图容器
        mainContent.innerHTML = `
            <div class="mindmap-view">
                <div class="mindmap-header">
                    <h2><span class="view-icon">🗺️</span> 思维导图</h2>
                    <div class="mindmap-actions">
                        <button class="mindmap-zoom-btn" id="mindmap-zoom-in" title="放大">
                            <span>➕</span>
                        </button>
                        <button class="mindmap-zoom-btn" id="mindmap-zoom-out" title="缩小">
                            <span>➖</span>
                        </button>
                        <button class="mindmap-zoom-btn" id="mindmap-fit" title="适应屏幕">
                            <span>🔲</span>
                        </button>
                        <button class="mindmap-download-btn" id="mindmap-download" title="下载 Markdown">
                            <span>⬇️</span> 下载 MD
                        </button>
                        <button class="back-to-content-btn" onclick="videoApp.restoreOriginalContent()">
                            ← 返回视频内容
                        </button>
                    </div>
                </div>
                <div class="mindmap-container" id="mindmap-container">
                    <svg id="mindmap-svg"></svg>
                </div>
            </div>
        `;
        
        // 保存 markdown 用于下载
        this.currentMindMapMarkdown = markdown;
        
        // 使用 Markmap 渲染
        try {
            // 验证 Markmap 库是否已加载
            if (!window.markmap) {
                throw new Error('Markmap 库未加载');
            }
            
            if (!window.markmap.Transformer) {
                throw new Error('Markmap.Transformer 未定义');
            }
            
            if (!window.markmap.Markmap) {
                throw new Error('Markmap.Markmap 未定义');
            }
            
            console.log('[INFO] 开始渲染思维导图...');
            
            const { Transformer, Markmap } = window.markmap;
            
            // 创建 Transformer 并转换 markdown
            const transformer = new Transformer();
            const { root } = transformer.transform(markdown);
            
            console.log('[INFO] Markdown 转换成功，节点数:', root);
            
            // 获取 SVG 元素
            const svg = document.getElementById('mindmap-svg');
            if (!svg) {
                throw new Error('SVG 元素未找到');
            }
            
            // 设置 SVG 尺寸
            const container = document.getElementById('mindmap-container');
            const width = container?.clientWidth || 800;
            const height = container?.clientHeight || 600;
            
            svg.setAttribute('width', width);
            svg.setAttribute('height', height);
            
            console.log(`[INFO] SVG 尺寸: ${width}x${height}`);
            
            // 创建 Markmap 实例
            const mm = Markmap.create(svg, {
                autoFit: true,
                duration: 500,
                maxWidth: 300,
                paddingX: 20,
                color: (node) => {
                    // 根据层级设置颜色
                    const colors = ['#4285F4', '#34A853', '#FBBC05', '#EA4335', '#9C27B0', '#00BCD4'];
                    return colors[node.depth % colors.length];
                }
            }, root);
            
            if (!mm) {
                throw new Error('Markmap 实例创建失败');
            }
            
            // 保存实例用于缩放控制
            this.currentMarkmap = mm;
            
            // 绑定缩放按钮事件
            this.bindMindMapControls();
            
            console.log('[SUCCESS] 思维导图渲染完成');
            
        } catch (error) {
            console.error('[ERROR] Markmap 渲染失败:', error);
            console.error('[ERROR] 错误详情:', error.stack);
            throw new Error('思维导图渲染失败: ' + error.message);
        }
    }

    /**
     * 绑定思维导图控制按钮
     */
    bindMindMapControls() {
        const zoomInBtn = document.getElementById('mindmap-zoom-in');
        const zoomOutBtn = document.getElementById('mindmap-zoom-out');
        const fitBtn = document.getElementById('mindmap-fit');
        const downloadBtn = document.getElementById('mindmap-download');
        
        if (zoomInBtn && this.currentMarkmap) {
            zoomInBtn.addEventListener('click', () => {
                const svg = document.getElementById('mindmap-svg');
                if (svg && this.currentMarkmap) {
                    this.currentMarkmap.rescale(1.25);
                }
            });
        }
        
        if (zoomOutBtn && this.currentMarkmap) {
            zoomOutBtn.addEventListener('click', () => {
                const svg = document.getElementById('mindmap-svg');
                if (svg && this.currentMarkmap) {
                    this.currentMarkmap.rescale(0.8);
                }
            });
        }
        
        if (fitBtn && this.currentMarkmap) {
            fitBtn.addEventListener('click', () => {
                if (this.currentMarkmap) {
                    this.currentMarkmap.fit();
                }
            });
        }
        
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                this.downloadMindMapMarkdown();
            });
        }
    }

    /**
     * 下载思维导图 Markdown
     */
    downloadMindMapMarkdown() {
        if (!this.currentMindMapMarkdown) {
            console.error('No markdown content to download');
            return;
        }
        
        const blob = new Blob([this.currentMindMapMarkdown], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `mindmap_${new Date().toISOString().slice(0, 10)}.md`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        URL.revokeObjectURL(url);
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

    /**
     * 初始化关键帧提取功能
     */
    initChapterFrames() {
        const extractBtn = document.getElementById('extract-frames-btn');
        if (!extractBtn) return;

        extractBtn.addEventListener('click', async () => {
            await this.extractKeyFrames();
        });
    }

    /**
     * 提取视频关键帧
     */
    async extractKeyFrames() {
        const extractBtn = document.getElementById('extract-frames-btn');
        const framesContainer = document.getElementById('chapter-frames');
        
        if (!framesContainer) return;

        try {
            // 禁用按钮
            extractBtn.disabled = true;
            extractBtn.innerHTML = '<span class="btn-icon">⏳</span><span>提取中...</span>';

            // 显示加载状态
            framesContainer.innerHTML = '<div class="frames-loading">正在提取关键帧，请稍候</div>';

            // 获取视频ID
            const videoId = this.currentVideoData?.videoInfo?.videoId || 'lQHK61IDFH4';
            
            // 根据视频章节生成时间戳
            const timestamps = this.generateKeyTimestamps();
            
            console.log('[INFO] 开始提取关键帧:', { videoId, timestamps });

            // 调用API提取关键帧
            const result = await this.apiService.extractVideoFrames(videoId, timestamps);

            if (result.success) {
                console.log('[SUCCESS] 关键帧提取成功:', result);
                this.renderKeyFrames(result.frames);
            } else {
                throw new Error(result.error || '提取失败');
            }

        } catch (error) {
            console.error('[ERROR] 提取关键帧失败:', error);
            framesContainer.innerHTML = `
                <div class="frame-error">
                    ❌ 提取失败: ${error.message}
                </div>
            `;
        } finally {
            // 恢复按钮状态
            extractBtn.disabled = false;
            extractBtn.innerHTML = '<span class="btn-icon">🎬</span><span>提取关键帧</span>';
        }
    }

    /**
     * 生成关键时间戳
     * 基于视频章节的开始时间
     */
    generateKeyTimestamps() {
        const sections = this.currentVideoData?.sections || [];
        
        // 如果有章节数据，使用章节的开始时间
        if (sections.length > 0) {
            return sections
                .map(section => section.timestampStart)
                .filter(ts => ts !== undefined && ts !== null)
                .slice(0, 10); // 最多提取10个关键帧
        }
        
        // 如果没有章节数据，使用固定间隔（每30秒一帧，最多10个）
        return [0, 30, 60, 120, 180, 300, 450, 600, 900, 1200];
    }

    /**
     * 渲染关键帧
     */
    renderKeyFrames(frames) {
        const framesContainer = document.getElementById('chapter-frames');
        if (!framesContainer) return;

        const successFrames = frames.filter(f => f.success);
        
        if (successFrames.length === 0) {
            framesContainer.innerHTML = `
                <div class="frame-error">
                    ⚠️ 没有成功提取到关键帧
                </div>
            `;
            return;
        }

        // 创建网格布局
        const gridHtml = `
            <div class="frames-grid">
                ${successFrames.map(frame => this.createFrameItemHtml(frame)).join('')}
            </div>
        `;

        framesContainer.innerHTML = gridHtml;

        // 绑定点击事件 - 点击帧跳转到对应时间
        this.bindFrameClickEvents(successFrames);
    }

    /**
     * 创建单个帧项的HTML
     */
    createFrameItemHtml(frame) {
        const timestamp = frame.timestamp;
        const timeStr = this.formatTime(timestamp);
        const imageUrl = `${this.config.getAPIConfig().BASE_URL}${frame.url}`;
        
        // 查找对应的章节标题
        const section = this.findSectionByTimestamp(timestamp);
        const title = section ? section.title : `Frame at ${timeStr}`;

        return `
            <div class="frame-item" data-timestamp="${timestamp}">
                <img src="${imageUrl}" 
                     alt="${title}" 
                     class="frame-thumbnail"
                     loading="lazy">
                <div class="frame-info">
                    <div class="frame-timestamp">${timeStr}</div>
                    <div class="frame-title">${this.escapeHtml(title)}</div>
                </div>
            </div>
        `;
    }

    /**
     * 根据时间戳查找对应的章节
     */
    findSectionByTimestamp(timestamp) {
        const sections = this.currentVideoData?.sections || [];
        return sections.find(section => section.timestampStart === timestamp);
    }

    /**
     * 绑定帧点击事件
     */
    bindFrameClickEvents(frames) {
        const frameItems = document.querySelectorAll('.frame-item');
        
        frameItems.forEach(item => {
            item.addEventListener('click', () => {
                const timestamp = parseInt(item.dataset.timestamp);
                this.seekToTimestamp(timestamp);
            });
        });
    }

    /**
     * 跳转到指定时间戳
     */
    seekToTimestamp(timestamp) {
        console.log('[INFO] 跳转到时间:', timestamp);
        
        // 优先使用 YouTube Player API
        if (this.youtubePlayer && this.playerReady && typeof this.youtubePlayer.seekTo === 'function') {
            try {
                this.youtubePlayer.seekTo(timestamp, true);
                // 如果视频暂停，自动播放
                if (this.youtubePlayer.getPlayerState() !== YT.PlayerState.PLAYING) {
                    this.youtubePlayer.playVideo();
                }
                console.log('[SUCCESS] 使用 Player API 跳转到:', timestamp);
                return;
            } catch (error) {
                console.warn('[WARN] Player API 跳转失败，使用备用方案:', error);
            }
        }
        
        // 备用方案：使用 postMessage API
        const videoId = this.currentVideoData?.videoInfo?.videoId || 'lQHK61IDFH4';
        
        // 动态查找 iframe（尝试多个可能的位置）
        let iframe = document.getElementById('video-iframe') ||
                     document.querySelector('.video-player-embedded iframe') ||
                     document.querySelector('.video-player iframe') ||
                     document.querySelector('iframe[src*="youtube.com/embed"]');
        
        if (iframe && iframe.contentWindow) {
            try {
                // 使用 YouTube postMessage API
                iframe.contentWindow.postMessage(JSON.stringify({
                    event: 'command',
                    func: 'seekTo',
                    args: [timestamp, true]
                }), '*');
                
                iframe.contentWindow.postMessage(JSON.stringify({
                    event: 'command',
                    func: 'playVideo',
                    args: []
                }), '*');
                
                console.log('[INFO] 使用 postMessage 跳转到:', timestamp);
            } catch (error) {
                console.error('[ERROR] postMessage 失败:', error);
                // 最后的备用方案：重新加载 iframe（会有闪烁）
                const newSrc = `https://www.youtube.com/embed/${videoId}?start=${timestamp}&autoplay=1&enablejsapi=1`;
                console.log('[INFO] 使用 src 更新跳转（备用方案）');
                iframe.src = newSrc;
            }
        } else {
            console.error('[ERROR] 未找到视频 iframe，尝试的选择器都失败了');
        }
    }

    /**
     * 格式化时间（秒 -> HH:MM:SS 或 MM:SS）
     */
    formatTime(seconds) {
        const hrs = Math.floor(seconds / 3600);
        const mins = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;

        if (hrs > 0) {
            return `${hrs}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
        }
        return `${mins}:${String(secs).padStart(2, '0')}`;
    }

    /**
     * 初始化布局交换功能
     */
    initLayoutSwap() {
        const swapBtn = document.getElementById('swap-layout-btn');
        if (!swapBtn) return;

        let isSwapped = false;

        swapBtn.addEventListener('click', () => {
            this.swapLayout(isSwapped);
            isSwapped = !isSwapped;
        });
    }

    /**
     * 交换布局
     */
    swapLayout(isCurrentlySwapped) {
        const swapBtn = document.getElementById('swap-layout-btn');
        const videoInfoBlock = document.querySelector('.video-info-block');
        const videoPlayer = document.querySelector('.video-player');
        const videoHeader = document.querySelector('.video-header');
        
        if (!videoInfoBlock || !videoPlayer || !videoHeader) return;

        // 添加旋转动画
        swapBtn.classList.add('swapping');
        
        if (!isCurrentlySwapped) {
            // 正常 → 交换
            this.performSwap(videoHeader, videoPlayer, videoInfoBlock);
        } else {
            // 交换 → 正常
            this.performSwapBack(videoHeader, videoPlayer);
        }
        
        // 移除动画类
        setTimeout(() => {
            swapBtn.classList.remove('swapping');
        }, 600);
    }

    /**
     * 执行交换（info → sidebar, player → main）
     */
    performSwap(videoHeader, videoPlayer, videoInfoBlock) {
        // 保存内容
        const infoHTML = videoInfoBlock.outerHTML;
        const playerHTML = videoPlayer.innerHTML;
        
        // 淡出
        videoHeader.style.opacity = '0';
        videoPlayer.style.opacity = '0';
        
        setTimeout(() => {
            // video-header 放入播放器
            videoHeader.innerHTML = `
                <div class="video-player-embedded">
                    ${playerHTML}
                </div>
            `;
            
            // sidebar 放入信息块
            videoPlayer.innerHTML = infoHTML;
            videoPlayer.style.backgroundColor = '#f8f9fa';
            videoPlayer.style.overflow = 'auto';
            
            // 淡入
            setTimeout(() => {
                videoHeader.style.opacity = '1';
                videoPlayer.style.opacity = '1';
                
                const embedded = videoHeader.querySelector('.video-player-embedded');
                if (embedded) embedded.style.opacity = '1';
                
                // 重新绑定事件（因为 DOM 被重新创建）
                this.bindTimestampEvents();
            }, 50);
        }, 300);
    }

    /**
     * 恢复原始布局
     */
    performSwapBack(videoHeader, videoPlayer) {
        // 保存当前内容
        const infoBlock = videoPlayer.querySelector('.video-info-block');
        const playerEmbedded = videoHeader.querySelector('.video-player-embedded');
        
        if (!infoBlock || !playerEmbedded) return;
        
        const infoHTML = infoBlock.outerHTML;
        const playerHTML = playerEmbedded.innerHTML;
        
        // 淡出
        videoHeader.style.opacity = '0';
        videoPlayer.style.opacity = '0';
        
        setTimeout(() => {
            // 恢复 video-header
            videoHeader.innerHTML = infoHTML;
            
            // 恢复 video-player
            videoPlayer.innerHTML = playerHTML;
            videoPlayer.style.backgroundColor = '#000';
            videoPlayer.style.overflow = 'hidden';
            
            // 淡入
            setTimeout(() => {
                videoHeader.style.opacity = '1';
                videoPlayer.style.opacity = '1';
                
                // 重新绑定事件
                this.bindTimestampEvents();
            }, 50);
        }, 300);
    }

    /**
     * 初始化章节轮播 - 已移除，现在所有章节都直接展示
     * 保留这些方法注释以供参考
     */
    // initSectionCarousel() { ... }
    // goToPrevSection() { ... }
    // goToNextSection() { ... }
    // showSection(index) { ... }

    /**
     * 渲染章节指示器
     */
    /**
     * 章节指示器和轮播相关方法 - 已移除
     * 现在所有章节都直接展示，不需要指示器和轮播功能
     */
    // renderSectionIndicators() { ... }
    // updateSectionIndicators() { ... }
    // updateCarouselButtons() { ... }

    /**
     * 加载视频描述
     */
    async loadVideoDescription() {
        const descriptionEl = document.getElementById('video-description');
        if (!descriptionEl) return;

        try {
            const videoId = this.currentVideoData?.videoInfo?.videoId || 'lQHK61IDFH4';
            console.log('[INFO] 正在加载视频描述:', videoId);

            const result = await this.apiService.getYouTubeVideoInfo(videoId);

            if (result.success && result.description) {
                console.log('[SUCCESS] 视频描述加载成功');
                
                // 将换行符转换为 <br>，处理 URL 链接
                const formattedDesc = this.formatDescription(result.description);
                descriptionEl.innerHTML = formattedDesc;
            } else {
                descriptionEl.innerHTML = '<p style="color: #999;">暂无描述</p>';
            }
        } catch (error) {
            console.error('[ERROR] 加载视频描述失败:', error);
            descriptionEl.innerHTML = '<p style="color: #999;">加载描述失败</p>';
        }
    }

    /**
     * 格式化描述文本
     */
    formatDescription(text) {
        if (!text) return '';
        
        // 转义 HTML
        text = this.escapeHtml(text);
        
        // 将换行符转换为 <br>
        text = text.replace(/\n/g, '<br>');
        
        // 将 URL 转换为链接
        const urlPattern = /(https?:\/\/[^\s<]+)/g;
        text = text.replace(urlPattern, '<a href="$1" target="_blank">$1</a>');
        
        return text;
    }

    /**
     * 初始化章节弹窗
     */
    initChapterModal() {
        console.log('[Chapter] Initializing chapter modal');
        console.log('[Chapter] apiService.getVideoChapters:', typeof this.apiService.getVideoChapters);
        
        const extractBtn = document.getElementById('extract-frames-btn');
        const closeBtn = document.getElementById('chapter-modal-close');
        
        if (!extractBtn) {
            console.error('[Chapter] Extract button not found!');
            return;
        }

        // 点击 Get 按钮显示弹窗
        extractBtn.addEventListener('click', async () => {
            await this.showChapterModal();
        });

        // 点击关闭按钮
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.hideChapterModal();
            });
        }
    }

    /**
     * 显示章节弹窗
     */
    async showChapterModal() {
        const modal = document.getElementById('chapter-modal');
        const modalBody = document.getElementById('chapter-modal-body');
        
        if (!modal || !modalBody) return;

        // 显示弹窗和加载状态
        modal.classList.add('show');
        modalBody.innerHTML = '<div class="chapter-loading">Loading chapters...</div>';

        try {
            const videoId = this.currentVideoData?.videoInfo?.videoId || 'lQHK61IDFH4';
            console.log('[INFO] 获取章节:', videoId);

            // 调用 API
            const result = await this.apiService.getVideoChapters(videoId);

            if (result.success && result.chapters?.length > 0) {
                console.log('[SUCCESS] 获取到', result.chapters.length, '个章节');
                this.renderChapters(result.chapters);
            } else {
                throw new Error('没有找到章节');
            }
        } catch (error) {
            console.error('[ERROR]', error);
            modalBody.innerHTML = `<div class="chapter-error">⚠️ ${error.message}</div>`;
        }
    }

    /**
     * 隐藏章节弹窗
     */
    hideChapterModal() {
        const modal = document.getElementById('chapter-modal');
        if (modal) modal.classList.remove('show');
    }

    /**
     * 渲染章节
     */
    renderChapters(chapters) {
        const modalBody = document.getElementById('chapter-modal-body');
        if (!modalBody) return;

        const html = `
            <div class="chapter-grid">
                ${chapters.map(ch => `
                    <div class="chapter-item" data-time="${ch.timestamp}">
                        <img src="${ch.thumbnail_url || 'data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 width=%22320%22 height=%22180%22%3E%3Crect fill=%22%23e0e0e0%22 width=%22320%22 height=%22180%22/%3E%3C/svg%3E'}" 
                             class="chapter-item-thumbnail" 
                             alt="${this.escapeHtml(ch.title)}">
                        <div class="chapter-item-info">
                            <div class="chapter-item-time">${this.formatTime(ch.timestamp)}</div>
                            <div class="chapter-item-title">${this.escapeHtml(ch.title)}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        modalBody.innerHTML = html;

        // 绑定点击事件
        modalBody.querySelectorAll('.chapter-item').forEach(item => {
            item.addEventListener('click', () => {
                const timestamp = parseInt(item.dataset.time);
                this.seekToTimestamp(timestamp);
                // this.hideChapterModal();
            });
        });
    }
}

// 可调整大小的面板处理类
class ResizablePanels {
    constructor() {
        this.sidebarLeft = document.getElementById('sidebar-left');
        this.mainContent = document.getElementById('main-content');
        this.sidebarRight = document.getElementById('sidebar-right');
        this.resizerLeft = document.getElementById('resizer-left');
        this.resizerRight = document.getElementById('resizer-right');
        this.swapBtn = document.getElementById('swap-layout-btn');
        
        this.isResizing = false;
        this.currentResizer = null;
        
        this.minWidth = 15; // 最小宽度百分比
        this.maxWidth = 45; // 最大宽度百分比
        
        // 从localStorage加载保存的宽度，如果没有则使用默认值
        this.leftWidth = parseFloat(localStorage.getItem('panelLeftWidth')) || 20;
        this.rightWidth = parseFloat(localStorage.getItem('panelRightWidth')) || 28;
    }
    
    init() {
        if (!this.resizerLeft || !this.resizerRight) {
            console.error('Resizer elements not found!');
            return;
        }
        
        console.log('ResizablePanels initialized successfully');
        console.log(`Initial widths: left=${this.leftWidth}%, right=${this.rightWidth}%`);
        
        // 绑定左侧分隔线事件
        this.resizerLeft.addEventListener('mousedown', (e) => {
            console.log('Left resizer mousedown');
            this.startResize(e, 'left');
        });
        
        // 阻止左侧分隔线的click事件
        this.resizerLeft.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
        });
        
        // 绑定右侧分隔线事件
        this.resizerRight.addEventListener('mousedown', (e) => {
            console.log('Right resizer mousedown');
            this.startResize(e, 'right');
        });
        
        // 阻止右侧分隔线的click事件
        this.resizerRight.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
        });
        
        // 阻止分隔栏上的所有可能导致跳转的事件
        const preventAllEvents = (e) => {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
        };
        
        [this.resizerLeft, this.resizerRight].forEach(resizer => {
            resizer.addEventListener('touchstart', preventAllEvents, { passive: false });
            resizer.addEventListener('touchmove', preventAllEvents, { passive: false });
            resizer.addEventListener('touchend', preventAllEvents, { passive: false });
            resizer.addEventListener('contextmenu', preventAllEvents);
            resizer.addEventListener('dragstart', preventAllEvents);
        });
        
        // 全局鼠标移动和释放事件
        document.addEventListener('mousemove', (e) => this.resize(e));
        document.addEventListener('mouseup', () => this.stopResize());
        
        // 初始化位置
        this.updateLayout();
    }
    
    saveToLocalStorage() {
        localStorage.setItem('panelLeftWidth', this.leftWidth);
        localStorage.setItem('panelRightWidth', this.rightWidth);
    }
    
    startResize(e, side) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        this.isResizing = true;
        this.currentResizer = side;
        this.resizerLeft.classList.add('dragging');
        this.resizerRight.classList.add('dragging');
        document.documentElement.classList.add('resizing');
        document.body.classList.add('resizing');
    }
    
    resize(e) {
        if (!this.isResizing) return;
        
        e.preventDefault();
        e.stopPropagation();
        
        const windowWidth = window.innerWidth;
        const mouseX = e.clientX;
        const percentage = (mouseX / windowWidth) * 100;
        
        if (this.currentResizer === 'left') {
            // 调整左侧宽度
            const newLeftWidth = Math.max(this.minWidth, Math.min(percentage, this.maxWidth));
            this.leftWidth = newLeftWidth;
            console.log(`Resizing left panel to ${this.leftWidth.toFixed(2)}%`);
        } else if (this.currentResizer === 'right') {
            // 调整右侧宽度（从右边计算）
            const newRightWidth = Math.max(this.minWidth, Math.min(100 - percentage, this.maxWidth));
            this.rightWidth = newRightWidth;
            console.log(`Resizing right panel to ${this.rightWidth.toFixed(2)}%`);
        }
        
        this.updateLayout();
    }
    
    stopResize() {
        if (!this.isResizing) return;
        
        console.log('Stop resizing');
        
        // 移除所有 dragging 类
        this.resizerLeft.classList.remove('dragging');
        this.resizerRight.classList.remove('dragging');
        document.documentElement.classList.remove('resizing');
        document.body.classList.remove('resizing');
        
        this.isResizing = false;
        this.currentResizer = null;
        
        // 保存宽度到localStorage
        this.saveToLocalStorage();
    }
    
    updateLayout() {
        // 计算中间区域宽度
        const middleWidth = 100 - this.leftWidth - this.rightWidth;
        
        console.log(`Updating layout: left=${this.leftWidth}%, middle=${middleWidth}%, right=${this.rightWidth}%`);
        
        // 更新左侧面板
        if (this.sidebarLeft) {
            this.sidebarLeft.style.width = `${this.leftWidth}%`;
        }
        
        // 更新主内容区 - 使用left和right属性
        if (this.mainContent) {
            this.mainContent.style.left = `${this.leftWidth}%`;
            this.mainContent.style.right = `${this.rightWidth}%`;
        }
        
        // 更新右侧面板
        if (this.sidebarRight) {
            this.sidebarRight.style.width = `${this.rightWidth}%`;
        }
        
        // 更新分隔线位置
        if (this.resizerLeft) {
            this.resizerLeft.style.left = `${this.leftWidth}%`;
        }
        if (this.resizerRight) {
            this.resizerRight.style.right = `${this.rightWidth}%`;
        }
        
        // 更新交换按钮位置
        if (this.swapBtn) {
            this.swapBtn.style.right = `${this.rightWidth + 1}%`;
        }
    }
}

// 当DOM加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    const app = new VideoPageApp(CONFIG);
    app.init();
    
    // 初始化可调整大小的面板
    const resizablePanels = new ResizablePanels();
    resizablePanels.init();
    
    // 将实例挂载到window对象，方便调试
    window.videoApp = app;
    window.resizablePanels = resizablePanels;
});
