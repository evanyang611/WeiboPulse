#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WeiboScraper 主入口文件
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

# 将src目录添加到Python路径
src_dir = str(Path(__file__).parent.parent)
if src_dir not in sys.path:
    sys.path.append(src_dir)

from fastapi import FastAPI
import uvicorn
from api.routes import router
from database.models import Base
from database.config import engine
from services.scheduler_service import scheduler_service
from config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时的初始化操作
    Base.metadata.create_all(bind=engine)
    await scheduler_service.start()
    
    yield
    
    # 关闭时的清理操作
    await scheduler_service.stop()

# 创建FastAPI应用
app = FastAPI(
    title="WeiboScraper",
    description="微博RSS订阅和内容展示系统",
    version="1.0.0",
    lifespan=lifespan
)

# 注册路由
app.include_router(router)

if __name__ == "__main__":
    # 运行应用
    uvicorn.run(
        "web:app",
        host=settings.WEB_HOST,
        port=settings.WEB_PORT,
        reload=True
    )