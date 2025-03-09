#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
创建LLMResult表的脚本
在现有数据库中添加LLMResult表，用于存储大模型调用的结果
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime
import logging

# 确保src目录在sys.path中
src_path = str(Path(__file__).resolve().parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)


from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from database.config import get_db, engine
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger("create_llm_result_table")

# 创建Base类
Base = declarative_base()

class LLMResult(Base):
    """大模型调用结果模型"""
    __tablename__ = 'llm_results'

    id = Column(Integer, primary_key=True)
    time = Column(DateTime, default=datetime.now, nullable=False)  # 调用时间
    objective = Column(String(128), nullable=False)  # 调用目的，如daily_topic_summary
    model = Column(String(128), nullable=False)  # 使用的模型名称
    input = Column(Text, nullable=False)  # 输入内容
    output = Column(Text, nullable=False)  # 输出内容
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self):
        return f"<LLMResult(id='{self.id}', objective='{self.objective}', model='{self.model}')>"

def create_llm_result_table():
    """创建LLMResult表"""
    try:
        # 检查表是否已存在
        inspector = inspect(engine)
        if 'llm_results' in inspector.get_table_names():
            logger.warning("LLMResult表已存在，跳过创建")
            print("LLMResult表已存在，跳过创建")
            return False
        
        # 创建表
        logger.info("开始创建LLMResult表...")
        LLMResult.__table__.create(engine)
        logger.info("LLMResult表创建成功")
        print("LLMResult表创建成功")
        return True
    
    except Exception as e:
        logger.error(f"创建LLMResult表时出错: {str(e)}")
        print(f"错误: {str(e)}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="在数据库中创建LLMResult表")
    parser.add_argument("--force", action="store_true", help="如果表已存在，则先删除再创建")
    
    args = parser.parse_args()
    
    # 如果指定了force参数，且表已存在，则先删除
    if args.force:
        try:
            inspector = inspect(engine)
            if 'llm_results' in inspector.get_table_names():
                logger.info("正在删除已存在的LLMResult表...")
                LLMResult.__table__.drop(engine)
                logger.info("已删除LLMResult表")
                print("已删除LLMResult表")
        except Exception as e:
            logger.error(f"删除LLMResult表时出错: {str(e)}")
            print(f"删除表时出错: {str(e)}")
            return
    
    # 创建表
    success = create_llm_result_table()
    
    if success:
        logger.info("脚本执行完成")
    else:
        logger.warning("脚本执行完成，但可能存在问题")

if __name__ == "__main__":
    main() 