import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///bot.db')
    
    # Settings
    DEFAULT_WELCOME_TEXT = "به ربات فروش کانفیگ V2Ray خوش آمدید!"
    DEFAULT_RULES_TEXT = "قوانین استفاده از ربات:\n1. ...\n2. ..."
    DEFAULT_GUIDE_TEXT = "راهنمای اتصال:\n1. ...\n2. ..."
    
    # Channel
    SALES_CHANNEL_ID = None

config = Config()


# ================================================
# 📢 کانال تلگرامی ما: @LearnJan
# 🎬 کانال یوتیوب ما: LearnTem
# برای آموزش‌های بیشتر و پشتیبانی به ما بپیوندید
# ================================================