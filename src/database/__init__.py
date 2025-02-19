from .models import Base, Post, Image, Video
from .config import engine, get_db

# 创建所有表
def init_db():
    Base.metadata.create_all(bind=engine)
