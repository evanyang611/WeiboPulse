import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件（如果存在）
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# 基础路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 基础路径配置
DATA_DIR = os.getenv('DATA_DIR', BASE_DIR / "data")

# 存储路径配置
LOG_DIR = os.path.join(DATA_DIR, 'logs')
DB_DIR = os.path.join(DATA_DIR, 'db')
MEDIA_DIR = os.path.join(DATA_DIR, 'media')
IMAGES_DIR = os.path.join(MEDIA_DIR, 'images')
ORIGINAL_IMAGES_DIR = os.path.join(IMAGES_DIR, 'original')
THUMBNAIL_IMAGES_DIR = os.path.join(IMAGES_DIR, 'thumbnail')
VIDEOS_DIR = os.path.join(MEDIA_DIR, 'videos')

# 数据库配置
DB_PATH = os.path.join(DB_DIR, "weibo.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# RSS地址
RSS_BASE_URL = os.getenv('RSS_BASE_URL', 'http://localhost:8001/rss/user/')

# Web应用配置
WEB_HOST = os.getenv('WEB_HOST', '127.0.0.1')
WEB_PORT = int(os.getenv('WEB_PORT', 8080))
