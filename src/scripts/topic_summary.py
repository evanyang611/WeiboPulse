#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
话题总结脚本
从数据库中选取过去24小时的指定分组的全部微博条目，
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

from sqlalchemy.orm import Session
from database.config import get_db
from database.models import Post, Account, LLMResult, Settings
from utils.logger import get_logger
from utils.qwen_client import QwenClient
from services.account_manager import AccountManager
from config.prompts import PROMPT_DAILY_TOPIC_SUMMARY

# 加载.env文件（如果存在）
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# 获取日志记录器
logger = get_logger("topic_summary")

def parse_interval(interval_str: str) -> int:
    """解析时间间隔字符串，转换为小时数
    
    Args:
        interval_str: 时间间隔字符串，格式为"{value} {unit}"，例如"30 minutes"
        
    Returns:
        int: 转换后的小时数
    
    Raises:
        ValueError: 如果格式无效或单位不支持
    """
    try:
        value, unit = interval_str.split()
        value = int(value)
        
        # 转换单位到小时
        if unit == 'seconds':
            return value / 3600  # 秒转小时
        elif unit == 'minutes':
            return value / 60  # 分钟转小时
        elif unit == 'hours':
            return value  # 小时
        else:
            raise ValueError(f"不支持的时间单位: {unit}")
    except Exception as e:
        raise ValueError(f"无效的时间间隔格式: {interval_str}, {str(e)}")

def get_topic_summary_settings():
    """从数据库中获取topic_summary设置
    
    Returns:
        dict: 包含interval、group和topics的字典，如果设置不存在则返回None
    """
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 查询设置
        setting = db.query(Settings).filter(Settings.key == "topic_summary").first()
        
        if not setting:
            logger.warning("未找到topic_summary设置")
            return None
            
        try:
            # 解析设置值
            setting_value = json.loads(setting.value)
            
            # 验证设置值
            if not isinstance(setting_value, dict):
                logger.error("topic_summary设置值不是有效的JSON对象")
                return None
                
            # 检查必要字段
            required_fields = ["interval", "group", "topics"]
            for field in required_fields:
                if field not in setting_value:
                    logger.error(f"topic_summary设置缺少必要字段: {field}")
                    return None
            
            # 确保topics是列表
            if not isinstance(setting_value["topics"], list):
                logger.error("topics字段不是有效的列表")
                return None
                
            logger.info(f"已加载topic_summary设置: {setting_value}")
            return setting_value
            
        except json.JSONDecodeError:
            logger.error(f"无法解析topic_summary设置值: {setting.value}")
            return None
            
    except Exception as e:
        logger.error(f"获取topic_summary设置时出错: {str(e)}")
        return None
    finally:
        db.close()

def get_recent_posts_by_group(group: str, hours: float):
    """获取指定分组过去几小时的微博帖子
    
    Args:
        group: 分组名称
        hours: 过去几小时
        
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

def save_llm_result(objective, model, input_content, output_content):
    """保存大模型调用结果到数据库
    
    Args:
        objective: 调用目的
        model: 使用的模型名称
        input_content: 输入内容
        output_content: 输出内容
        
    Returns:
        新创建记录的ID，如果保存失败则返回None
    """
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 如果输入内容不是字符串，转换为JSON字符串
        if not isinstance(input_content, str):
            input_content = json.dumps(input_content, ensure_ascii=False)
        
        # 创建新记录
        llm_result = LLMResult(
            time=datetime.now(),
            objective=objective,
            model=model,
            input=input_content,
            output=output_content
        )
        
        # 添加到数据库
        db.add(llm_result)
        db.commit()
        
        # 刷新以获取ID
        db.refresh(llm_result)
        
        logger.info(f"已保存大模型调用结果，ID: {llm_result.id}, 目的: {objective}")
        return llm_result.id
        
    except Exception as e:
        db.rollback()
        logger.error(f"保存大模型调用结果失败: {str(e)}")
        return None
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
    
    # 使用导入的提示词模板
    prompt_template = PROMPT_DAILY_TOPIC_SUMMARY
    
    # 替换模板中的占位符
    topics_str = json.dumps(topics, ensure_ascii=False)
    posts_str = json.dumps(posts, ensure_ascii=False)
    
    prompt = prompt_template.replace("【关心话题】", topics_str).replace("【微博内容】", posts_str)
    
    logger.info(f"准备调用大模型，提示词长度: {len(prompt)}")
    
    # 调用大模型
    try:
        qwen = QwenClient()
        model_name = os.getenv('TEXT_MODEL', "qwen-max-latest")
        
        # 构建messages作为input
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # 调用大模型
        response = qwen.chat(prompt, stream=False, temperature=0.2)
        logger.info("大模型调用成功")
        
        # 保存调用结果到数据库
        result_id = save_llm_result(
            objective="daily_topic_summary",
            model=model_name,
            input_content=messages,  # 使用messages作为input
            output_content=response  # 使用summary作为output
        )
        
        if result_id:
            logger.info(f"已保存大模型调用结果，ID: {result_id}")
        else:
            logger.warning("保存大模型调用结果失败")
        
        return response
    except Exception as e:
        logger.error(f"调用大模型失败: {e}")
        return f"调用大模型失败: {str(e)}"

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="生成微博话题总结")
    parser.add_argument("--interval", default="24 hours", help="时间间隔，格式为'{value} {unit}'，例如'30 minutes'。支持的单位有: seconds, minutes, hours")
    parser.add_argument("--group", default='default', help="微博账号分组名称")
    parser.add_argument("--topics", default='["日本新番制作发表", "日本歌手中国演唱会消息"]', help="关心的话题，多个话题用逗号分隔")
    parser.add_argument("--output", help="输出结果到文件")
    parser.add_argument("--use-settings", action="store_true", help="使用数据库中的topic_summary设置")
    
    args = parser.parse_args()
    
    # 如果指定了使用数据库设置
    if args.use_settings:
        settings = get_topic_summary_settings()
        if settings:
            args.group = settings["group"]
            args.interval = settings["interval"]
            args.topics = settings["topics"]
            logger.info(f"使用数据库设置: 分组={args.group}, 时间间隔={args.interval}, 话题={args.topics}")
        else:
            logger.warning("未找到有效的topic_summary设置，将使用命令行参数")
    
    # 解析时间间隔
    try:
        hours = parse_interval(args.interval)
        logger.info(f"时间间隔: {args.interval} (转换为 {hours:.2f} 小时)")
    except ValueError as e:
        logger.error(f"无效的时间间隔: {str(e)}")
        print(f"错误: {str(e)}")
        return
    
    # 解析话题列表
    if isinstance(args.topics, list):
        topics = args.topics
    else:
        try:
            # 尝试解析JSON格式
            if args.topics.startswith('[') and args.topics.endswith(']'):
                topics = json.loads(args.topics)
            else:
                # 否则按逗号分隔
                topics = [topic.strip() for topic in args.topics.split(",") if topic.strip()]
        except json.JSONDecodeError:
            # JSON解析失败，按逗号分隔
            topics = [topic.strip() for topic in args.topics.split(",") if topic.strip()]

    if not topics:
        logger.error("未提供有效的话题")
        print("错误: 请提供至少一个有效的话题")
        return
    
    logger.info(f"关心的话题: {topics}")
    
    # 获取微博帖子
    posts = get_recent_posts_by_group(args.group, hours)
    
    if not posts:
        logger.warning(f"未找到分组 '{args.group}' 在过去 {hours:.2f} 小时内的微博")
        print(f"未找到分组 '{args.group}' 在过去 {hours:.2f} 小时内的微博")
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