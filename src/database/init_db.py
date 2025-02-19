from src.database.models import Base
from src.database.config import engine

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    init_db()
    print("数据库表已创建")
