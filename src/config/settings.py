import os
from pathlib import Path

# 基础路径
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 基础路径配置
DATA_DIR = os.getenv('DATA_DIR', BASE_DIR / "data")
LOG_DIR = os.getenv('LOG_DIR', BASE_DIR / "logs")

# 存储路径配置
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
RSS_BASE_URL = "http://yangqihang.space:8001/rss/user/"

# 调度配置
SCHEDULE_INTERVAL = 60  # 秒

# 下载配置
DOWNLOAD_TIMEOUT = 30  # 秒
