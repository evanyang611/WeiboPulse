#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
删除指定账号的所有帖子
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from database.models import Account, Post, Image, Video
from config.settings import DATABASE_URL

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建数据库引擎和会话
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def delete_account_posts(account_ids=None, account_names=None):
    """
    删除指定账号的所有帖子
    
    Args:
        account_ids: 账号ID列表
        account_names: 账号名称列表
    """
    if not account_ids and not account_names:
        logger.error("必须指定account_ids或account_names")
        return
    
    db = SessionLocal()
    try:
        # 查找账号
        query = db.query(Account)
        if account_ids:
            query = query.filter(Account.account_id.in_(account_ids))
        if account_names:
            query = query.filter(Account.account_name.in_(account_names))
        
        accounts = query.all()
        
        if not accounts:
            logger.warning(f"未找到指定的账号")
            return
        
        for account in accounts:
            logger.info(f"开始删除账号 {account.account_name} (ID: {account.account_id}) 的帖子")
            
            # 获取该账号的所有帖子ID
            post_ids = [post.id for post in account.posts]
            
            if not post_ids:
                logger.info(f"账号 {account.account_name} 没有帖子")
                continue
            
            # 删除相关的图片
            images_count = db.query(Image).filter(Image.post_id.in_(post_ids)).delete(synchronize_session=False)
            logger.info(f"已删除 {images_count} 张图片")
            
            # 删除相关的视频
            videos_count = db.query(Video).filter(Video.post_id.in_(post_ids)).delete(synchronize_session=False)
            logger.info(f"已删除 {videos_count} 个视频")
            
            # 删除帖子
            posts_count = db.query(Post).filter(Post.account_id == account.id).delete(synchronize_session=False)
            logger.info(f"已删除 {posts_count} 条帖子")
            
            db.commit()
            logger.info(f"账号 {account.account_name} 的所有帖子已删除")
    
    except Exception as e:
        db.rollback()
        logger.exception(f"删除帖子时出错: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    # 删除account4和account5的所有帖子
    delete_account_posts(account_ids=["1864696473", "5130681470"])
    logger.info("删除完成")
