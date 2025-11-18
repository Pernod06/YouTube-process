// 配置文件 - 可根据环境切换
const CONFIG = {
    // API配置
    API: {
        // 开发环境
        development: {
            BASE_URL: 'http://localhost:5000/api',
            VIDEO_ENDPOINT: '/videos',
            SECTIONS_ENDPOINT: '/sections'
        },
        // 生产环境
        production: {
            BASE_URL: 'https://api.yourproduction.com/api',
            VIDEO_ENDPOINT: '/videos',
            SECTIONS_ENDPOINT: '/sections'
        },
        // 当前使用的环境
        current: 'development'
    },

    // 本地数据配置（开发阶段）
    LOCAL: {
        DATA_PATH: './data/video-data.json'
    },

    // YouTube配置
    YOUTUBE: {
        EMBED_URL: 'https://www.youtube.com/embed/',
        DEFAULT_PARAMS: {
            autoplay: 1,
            rel: 0,
            modestbranding: 1
        }
    },

    CHAT: {
        USE_LLM: true,
        ENDPOINT: '/chat',
        SEND_VIDEO_CONTEXT: true,
        MAX_TOKENS: 500,
        TIMEOUT: 30000
    },

    OPENAI: {
        API_KEY: '',
        MODEL: 'gpt-3.5-turbo'
    },

    // 应用配置
    APP: {
        USE_LOCAL_DATA: true, // 设置为false时使用API
        ENABLE_AUTO_SCROLL: true,
        SMOOTH_SCROLL_DURATION: 500,
        ENABLE_CHAT: true, // 聊天功能开关
        ENABLE_COMMENTS: true // 评论功能开关
    }
};

// 获取当前API配置
CONFIG.getAPIConfig = function() {
    return this.API[this.API.current];
};

// 导出配置
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}

