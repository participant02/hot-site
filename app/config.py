import os

# 数据库
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/hotsite.db")

# AI API 配置（部署时改成你自己的）
AI_API_KEY = os.getenv("AI_API_KEY", "sk-your-api-key-here")
AI_API_URL = os.getenv("AI_API_URL", "https://api.deepseek.com/v1")
AI_MODEL = os.getenv("AI_MODEL", "deepseek-chat")

# 网站配置
SITE_NAME = "热点快讯"
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")
SITE_DESC = "每日热点资讯，带你了解天下事"

# 广告（部署后替换为你的广告代码）
BAIDU_AD_SCRIPT = os.getenv("BAIDU_AD_SCRIPT", "")
GOOGLE_AD_SCRIPT = os.getenv("GOOGLE_AD_SCRIPT", "")
