from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import logging
from config.settings import DATABASE_URL

# 设置SQLAlchemy的日志级别为WARNING，这样就不会显示INFO级别的日志了
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# 创建数据库引擎，配置连接池
engine = create_engine(
    DATABASE_URL, 
    echo=False,
    poolclass=QueuePool,
    pool_size=20,           # 增加连接池大小
    max_overflow=20,        # 增加溢出连接数
    pool_timeout=60,        # 增加连接超时时间
    pool_recycle=3600,      # 每小时回收连接
    pool_pre_ping=True      # 使用前检查连接是否有效
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
