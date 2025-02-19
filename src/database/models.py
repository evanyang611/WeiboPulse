from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, create_engine, Text, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Post(Base):
    """微博帖子模型"""
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    source = Column(String(32), nullable=False) # 默认为weibo
    source_id = Column(String(32), unique=True, nullable=False)  # weibo 原始ID
    title = Column(String(512))
    content = Column(Text)
    original_content = Column(Text)
    link = Column(String(512))
    published_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联关系
    images = relationship("Image", back_populates="post")
    videos = relationship("Video", back_populates="post")

    def __repr__(self):
        return f"<Post(source='{self.source}', source_id='{self.source_id}', title='{self.title}')>"


class Image(Base):
    """图片模型"""
    __tablename__ = 'images'

    id = Column(Integer, primary_key=True)
    image_id = Column(String, nullable=False)  # 图片的唯一标识，但允许在不同微博中重复
    original_url = Column(String, nullable=False)  # 原始图片 URL
    thumbnail_url = Column(String, nullable=False)  # 缩略图 URL
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)  # 关联的微博 ID
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    # 关联关系
    post = relationship("Post", back_populates="images")

    # 复合唯一约束，确保同一个图片不会被重复添加到同一个微博中
    __table_args__ = (
        UniqueConstraint('image_id', 'post_id', name='uix_image_post'),
    )

    def __repr__(self):
        return f"<Image(image_id='{self.image_id}')>"


class Video(Base):
    """微博视频模型"""
    __tablename__ = 'videos'

    id = Column(Integer, primary_key=True)
    video_id = Column(String, nullable=False)  # weibo_video_xxx 格式
    video_url = Column(String(1024), nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联关系
    post = relationship("Post", back_populates="videos")

    def __repr__(self):
        return f"<Video(video_id='{self.video_id}')>"
