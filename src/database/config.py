from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
from src.config.settings import DATABASE_URL

# 设置SQLAlchemy的日志级别为WARNING，这样就不会显示INFO级别的日志了
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# 创建数据库引擎
engine = create_engine(DATABASE_URL, echo=False)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
