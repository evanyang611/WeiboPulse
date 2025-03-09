#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
添加topic_summary设置脚本
在settings表中添加topic_summary设置，包含interval、group和topics字段
"""

import sys
from pathlib import Path
import argparse
import json
from datetime import datetime


# 确保src目录在sys.path中
src_path = str(Path(__file__).resolve().parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from sqlalchemy.orm import Session
from database.config import get_db
from database.models import Settings
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger("add_topic_summary_settings")

def add_topic_summary_settings(interval: str, group: str, topics: list, description: str = None):
    """添加topic_summary设置
    
    Args:
        interval: 时间间隔，格式为"{value} {unit}"，例如"30 minutes"
        group: 对应的分组
        topics: 需要识别的话题列表
        description: 设置描述
        
    Returns:
        bool: 是否成功添加设置
    """
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 验证interval格式
        try:
            value, unit = interval.split()
            value = int(value)
            if unit not in ['seconds', 'minutes', 'hours']:
                raise ValueError(f"不支持的时间单位: {unit}，支持的单位有: seconds, minutes, hours")
            if value <= 0:
                raise ValueError(f"时间值必须大于0: {value}")
        except ValueError as e:
            logger.error(f"无效的时间间隔格式: {interval}, {str(e)}")
            return False
        
        # 检查设置是否已存在
        existing_setting = db.query(Settings).filter(Settings.key == "topic_summary").first()
        
        # 构建设置值
        setting_value = json.dumps({
            "interval": interval,
            "group": group,
            "topics": topics
        }, ensure_ascii=False)
        
        if existing_setting:
            # 更新现有设置
            existing_setting.value = setting_value
            if description:
                existing_setting.description = description
            existing_setting.updated_at = datetime.now()
            
            db.commit()
            logger.info(f"已更新topic_summary设置: {setting_value}")
            return True
        else:
            # 创建新设置
            if not description:
                description = "话题总结设置，包含时间间隔、分组和话题列表"
                
            new_setting = Settings(
                key="topic_summary",
                value=setting_value,
                description=description
            )
            
            db.add(new_setting)
            db.commit()
            
            logger.info(f"已添加topic_summary设置: {setting_value}")
            return True
            
    except Exception as e:
        db.rollback()
        logger.error(f"添加topic_summary设置失败: {str(e)}")
        return False
    finally:
        db.close()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="添加topic_summary设置")
    parser.add_argument("--interval", default="24 hours", help="时间间隔，格式为'{value} {unit}'，例如'30 minutes'。支持的单位有: seconds, minutes, hours")
    parser.add_argument("--group", default="default", help="对应的分组，默认为default")
    parser.add_argument("--topics", default='["日本动漫制作发表", "日本歌手中国演唱会消息"]', help="需要识别的话题，JSON格式的数组或逗号分隔的字符串")
    parser.add_argument("--description", help="设置描述")
    
    args = parser.parse_args()
    
    # 解析话题列表
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
    
    # 添加设置
    success = add_topic_summary_settings(
        interval=args.interval,
        group=args.group,
        topics=topics,
        description=args.description
    )
    
    if success:
        print(f"已成功添加/更新topic_summary设置:")
        print(f"  - 时间间隔: {args.interval}")
        print(f"  - 分组: {args.group}")
        print(f"  - 话题: {topics}")
    else:
        print("添加/更新topic_summary设置失败，请查看日志了解详情")

if __name__ == "__main__":
    main() 