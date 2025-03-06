#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
删除今天写入数据库的所有微博帖子
"""

import os
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

# 添加项目根目录到系统路径
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# 导入数据库模型和配置
from database.models import Post, Image, Video
from config.settings import DATABASE_URL
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from utils.logger import get_logger

def delete_today_posts():
    """删除今天创建的所有微博帖子及其关联的图片和视频"""
    # 创建日志记录器
    logger = get_logger("delete_today_posts")
    
    # 创建数据库连接
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # 获取今天的开始时间和结束时间
        today = datetime.now().date()
        # today = today - timedelta(days=1)
        today_start = datetime.combine(today, time.min)
        today_end = datetime.combine(today, time.max)
        
        logger.info(f"开始查询今天({today})创建的微博帖子...")
        
        # 查询今天创建的所有帖子
        today_posts = session.query(Post).filter(
            Post.created_at >= today_start,
            Post.created_at <= today_end
        ).all()
        
        post_count = len(today_posts)
        
        if post_count == 0:
            logger.info("今天没有新增的微博帖子。")
            print("今天没有新增的微博帖子。")
            return
        
        logger.info(f"找到 {post_count} 条今天创建的微博帖子，准备删除...")
        print(f"找到 {post_count} 条今天创建的微博帖子，准备删除...")
        
        # 删除每个帖子及其关联的图片和视频
        for post in today_posts:
            # 输出帖子信息
            post_title = post.title or (post.content[:30] + "..." if post.content else "无标题")
            logger.info(f"正在删除: {post_title} (ID: {post.id})")
            print(f"正在删除: {post_title} (ID: {post.id})")
            
            # 删除关联的图片
            image_count = len(post.images)
            if image_count > 0:
                logger.info(f"  - 删除 {image_count} 张关联图片")
                print(f"  - 删除 {image_count} 张关联图片")
                for image in post.images:
                    session.delete(image)
            
            # 删除关联的视频
            video_count = len(post.videos)
            if video_count > 0:
                logger.info(f"  - 删除 {video_count} 个关联视频")
                print(f"  - 删除 {video_count} 个关联视频")
                for video in post.videos:
                    session.delete(video)
            
            # 删除帖子本身
            session.delete(post)
        
        # 提交事务
        session.commit()
        logger.info(f"成功删除 {post_count} 条今天创建的微博帖子及其关联媒体。")
        print(f"成功删除 {post_count} 条今天创建的微博帖子及其关联媒体。")
        
    except Exception as e:
        session.rollback()
        logger.error(f"删除过程中发生错误: {e}")
        print(f"删除过程中发生错误: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    # 请求确认
    confirm = input("此操作将删除今天写入数据库的所有微博帖子及其关联媒体。确定要继续吗？(y/n): ")
    if confirm.lower() == 'y':
        delete_today_posts()
    else:
        print("操作已取消。") 