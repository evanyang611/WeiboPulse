#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
从数据库中查询posts表的数据的测试脚本
使用ORM方式查询最新的微博帖子
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime
import json

# 将src目录添加到Python路径
src_path = str(Path(__file__).resolve().parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from database.config import get_db
from database.models import Post, Account
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger("query_posts")

def get_latest_posts(limit=10):
    """使用ORM查询最新的微博帖子
    
    Args:
        limit: 限制返回的记录数，默认为10条
        
    Returns:
        查询结果列表
    """
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 构建查询
        query = db.query(Post).join(Account)
        
        # 添加排序和限制
        query = query.order_by(Post.published_at.desc()).limit(limit)
        
        # 执行查询
        posts = []
        for post in query.all():
            post_dict = {
                "id": post.id,
                "source": post.source,
                "source_id": post.source_id,
                "title": post.title,
                "content": post.content,
                "link": post.link,
                "published_at": post.published_at.strftime("%Y-%m-%d %H:%M:%S"),
                "created_at": post.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "account_id": post.account_id,
                "account_name": post.account.account_name,
                "weibo_id": post.account.account_id,
                "images": []  # 初始化空的图片列表
            }
            
            # 添加图片信息
            for image in post.images:
                post_dict["images"].append({
                    "image_id": image.image_id,
                    "original_url": image.original_url,
                    "thumbnail_url": image.thumbnail_url
                })
            
            posts.append(post_dict)
            
        return posts
    finally:
        db.close()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="查询最新的微博帖子数据")
    parser.add_argument("--limit", type=int, default=10, help="限制返回的记录数，默认为10条")
    parser.add_argument("--output", help="输出结果到文件")
    
    args = parser.parse_args()
    
    # 执行查询
    logger.info(f"查询最新的 {args.limit} 条微博帖子...")
    posts = get_latest_posts(limit=args.limit)
    
    # 输出结果
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
        logger.info(f"查询结果已保存到 {args.output}")
    else:
        # 打印结果
        print(f"共查询到 {len(posts)} 条微博帖子:")
        for i, post in enumerate(posts, 1):
            post_info = {
                "published_at": post['published_at'],
                "account_name": post['account_name'],
                "content": post['content'],
                "images": [img["original_url"] for img in post['images']] if post['images'] else []
            }
            print(post_info)

            # print(f"\n--- 帖子 {i} ---")
            # print(f"发布时间: {post_info['published_at']}")
            # print(f"账号: {post_info['account_name']}")
            # print(f"内容: {post_info['content'][:100]}..." if len(post_info['content']) > 100 else f"内容: {post_info['content']}")
            
            # if post_info['images']:
            #     print(f"图片数量: {len(post_info['images'])}")
            #     for j, img_url in enumerate(post_info['images'], 1):
            #         print(f"  图片 {j}: {img_url}")
            # else:
            #     print("无图片")
    
    logger.info(f"查询完成，共 {len(posts)} 条记录")

if __name__ == "__main__":
    main() 