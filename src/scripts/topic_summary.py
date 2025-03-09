#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
话题总结脚本
从数据库中选取过去6小时的指定分组的全部微博条目，
然后调用通义千问大模型，根据PROMPT_DAILY_TOPIC_SUMMARY，生成话题总结
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv

# 确保src目录在sys.path中
src_path = str(Path(__file__).resolve().parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 使用绝对导入
from utils.logger import get_logger
from config.prompts import PROMPT_DAILY_TOPIC_SUMMARY

# 加载.env文件（如果存在）
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

from sqlalchemy.orm import Session
from database.config import get_db
from database.models import Post, Account
from utils.logger import get_logger
from utils.qwen_client import QwenClient
from services.account_manager import AccountManager

# 获取日志记录器
logger = get_logger("topic_summary")


def get_recent_posts_by_group(group: str, hours: int = 6):
    """获取指定分组过去几小时的微博帖子
    
    Args:
        group: 分组名称
        hours: 过去几小时，默认为6小时
        
    Returns:
        查询结果列表
    """
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        logger.info(f"查询分组 '{group}' 在 {start_time} 到 {end_time} 之间的微博")
        
        # 获取分组内的账号ID列表
        account_manager = AccountManager()
        accounts = account_manager.list_accounts(group=group)
        
        if not accounts:
            logger.warning(f"分组 '{group}' 中没有账号")
            return []
            
        account_ids = [account.id for account in accounts]
        
        # 构建查询
        query = db.query(Post).join(Account).filter(
            Post.published_at >= start_time,
            Post.published_at <= end_time,
            Post.account_id.in_(account_ids)
        )
        
        # 添加排序
        query = query.order_by(Post.published_at.desc())
        
        # 执行查询
        posts = []
        for post in query.all():
            post_dict = {
                "published_at": post.published_at.strftime("%Y-%m-%d %H:%M:%S"),
                "account_name": post.account.account_name,
                "content": post.content
            }
            posts.append(post_dict)
            
        logger.info(f"查询到 {len(posts)} 条微博")
        return posts
    finally:
        db.close()

def generate_topic_summary(topics: list, posts: list):
    """生成话题总结
    
    Args:
        topics: 关心的话题列表
        posts: 微博帖子列表
        
    Returns:
        生成的总结内容
    """
    if not posts:
        logger.warning("没有微博帖子，无法生成总结")
        return "没有找到相关微博内容，无法生成总结。"
        
    # 加载提示词模板
    prompt_template = PROMPT_DAILY_TOPIC_SUMMARY
    if not prompt_template:
        logger.error("无法加载提示词模板")
        return "加载提示词模板失败，无法生成总结。"
    
    # 替换模板中的占位符
    topics_str = json.dumps(topics, ensure_ascii=False)
    posts_str = json.dumps(posts, ensure_ascii=False)
    
    prompt = prompt_template.replace("【关心话题】", topics_str).replace("【微博内容】", posts_str)
    
    logger.info(f"准备调用大模型，提示词长度: {len(prompt)}")
    
    # 调用大模型
    try:
        qwen = QwenClient()
        response = qwen.chat(prompt, stream=False, temperature=0.2)
        logger.info("大模型调用成功")
        return response
    except Exception as e:
        logger.error(f"调用大模型失败: {e}")
        return f"调用大模型失败: {str(e)}"

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="生成微博话题总结")
    parser.add_argument("--group", default='default', help="微博账号分组名称")
    parser.add_argument("--hours", type=int, default=24, help="过去几小时的微博，默认为6小时")
    parser.add_argument("--topics", default='["日本新番制作发表", "日本歌手中国演唱会消息"]', help="关心的话题，多个话题用逗号分隔")
    parser.add_argument("--output", help="输出结果到文件")
    
    args = parser.parse_args()
    
    # 解析话题列表
    topics = [topic.strip() for topic in args.topics.split(",") if topic.strip()]

    if not topics:
        logger.error("未提供有效的话题")
        print("错误: 请提供至少一个有效的话题")
        return
    
    logger.info(f"关心的话题: {topics}")
    
    # 获取微博帖子
    posts = get_recent_posts_by_group(args.group, args.hours)
    
    if not posts:
        logger.warning(f"未找到分组 '{args.group}' 在过去 {args.hours} 小时内的微博")
        print(f"未找到分组 '{args.group}' 在过去 {args.hours} 小时内的微博")
        return
    
    # 生成总结
    summary = generate_topic_summary(topics, posts)
    
    # 输出结果
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(summary)
        logger.info(f"总结已保存到 {args.output}")
        print(f"总结已保存到 {args.output}")
    else:
        print("\n" + "="*50)
        print("话题总结")
        print("="*50)
        print(summary)
        print("="*50)
    
    logger.info("话题总结生成完成")

if __name__ == "__main__":
    main() 