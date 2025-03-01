import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path

from api.routes import router
from config import settings

# 创建FastAPI应用
app = FastAPI(
    title="微博RSS解析器",
    description="一个用于抓取微博RSS并保存到本地的工具",
    version="1.0.0"
)

# 挂载静态文件目录
static_dir = Path(__file__).parent / "static"
if not static_dir.exists():
    static_dir.mkdir(parents=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 挂载媒体文件目录
app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")

# 注册路由
app.include_router(router)

# 图片路由
@app.get("/images/{image_type}/{image_id}")
async def get_image(image_type: str, image_id: str):
    # 根据类型选择目录
    if image_type == "original":
        image_path = os.path.join(settings.ORIGINAL_IMAGES_DIR, image_id)
    elif image_type == "thumbnail":
        image_path = os.path.join(settings.THUMBNAIL_IMAGES_DIR, image_id)
    else:
        return {"error": "无效的图片类型"}
    
    # 检查文件是否存在
    if not os.path.exists(image_path):
        return {"error": "图片不存在"}
    
    # 返回文件
    return FileResponse(image_path)

# 主函数
def main():
    # 启动服务器
    uvicorn.run(
        "web:app",
        host=settings.WEB_HOST,
        port=settings.WEB_PORT,
        reload=True
    )

if __name__ == "__main__":
    main()
