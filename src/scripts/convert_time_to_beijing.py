#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
将数据库中所有Post的published_at从GMT时间转换为北京时间
"""

import sys
from pathlib import Path
import os

# 将src目录添加到Python路径
current_dir = Path(__file__).resolve()
src_dir = current_dir.parent
sys.path.append(str(src_dir.parent))

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from database.models import Post
from database.config import engine
from utils.logger import get_logger

def convert_time_to_beijing():
    """将所有Post的published_at从GMT时间转换为北京时间"""
    logger = get_logger("time_converter")
    
    logger.info("开始转换时间为北京时间...")
    
    # 创建北京时区对象
    beijing_tz = timezone(timedelta(hours=8))
    
    with Session(engine) as session:
        # 获取所有Post
        posts = session.query(Post).all()
        logger.info(f"找到 {len(posts)} 条微博记录")
        
        # 统计计数
        converted_count = 0
        already_beijing_count = 0
        error_count = 0
        
        for post in posts:
            try:
                # 检查当前时区
                current_tz = post.published_at.tzinfo
                
                # 如果没有时区信息，假设是UTC时间
                if current_tz is None:
                    logger.info(f"Post ID {post.id}: 没有时区信息，假设为UTC时间")
                    utc_time = post.published_at.replace(tzinfo=timezone.utc)
                    beijing_time = utc_time.astimezone(beijing_tz)
                    post.published_at = beijing_time
                    converted_count += 1
                    logger.info(f"Post ID {post.id}: 转换时间 {utc_time} -> {beijing_time}")
                # 如果已经是北京时间，跳过
                elif current_tz == beijing_tz:
                    already_beijing_count += 1
                    logger.debug(f"Post ID {post.id}: 已经是北京时间 {post.published_at}")
                # 如果是其他时区，转换为北京时间
                else:
                    original_time = post.published_at
                    beijing_time = original_time.astimezone(beijing_tz)
                    post.published_at = beijing_time
                    converted_count += 1
                    logger.info(f"Post ID {post.id}: 转换时间 {original_time} -> {beijing_time}")
            except Exception as e:
                error_count += 1
                logger.error(f"Post ID {post.id}: 转换时间出错 - {str(e)}")
        
        # 提交更改
        if converted_count > 0:
            try:
                session.commit()
                logger.info(f"成功提交更改，共转换 {converted_count} 条记录")
            except Exception as e:
                session.rollback()
                logger.error(f"提交更改失败: {str(e)}")
        
        # 输出统计信息
        logger.info("时间转换完成")
        logger.info(f"总记录数: {len(posts)}")
        logger.info(f"已转换: {converted_count}")
        logger.info(f"已是北京时间: {already_beijing_count}")
        logger.info(f"转换失败: {error_count}")

if __name__ == "__main__":
    convert_time_to_beijing() 