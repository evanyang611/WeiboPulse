#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
初始化Settings表的脚本
"""

import sys
from pathlib import Path

# 将src目录添加到Python路径
src_dir = str(Path(__file__).parent.parent)
if src_dir not in sys.path:
    sys.path.append(src_dir)

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from database.models import Base, Settings
from config import settings
from utils.logger import get_logger

def init_settings_table():
    """初始化Settings表"""
    logger = get_logger("init_settings")
    
    # 创建数据库引擎
    engine = create_engine(settings.DATABASE_URL)
    
    # 检查Settings表是否已存在
    inspector = inspect(engine)
    if 'settings' in inspector.get_table_names():
        logger.info("Settings表已存在，无需创建")
    else:
        # 创建Settings表
        Base.metadata.create_all(engine, tables=[Settings.__table__])
        logger.info("成功创建Settings表")
    
    # 创建会话
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 检查Settings表中是否有数据
    settings_count = session.query(Settings).count()
    logger.info(f"Settings表中共有 {settings_count} 条记录")
    
    session.close()
    
    return True

if __name__ == "__main__":
    success = init_settings_table()
    if success:
        print("Settings表初始化成功")
    else:
        print("Settings表初始化失败")
        sys.exit(1) 