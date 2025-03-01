from fastapi import APIRouter, Depends, HTTPException, Query, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from pathlib import Path

from database.config import get_db
from database.models import Post, Account, Image, Video
from services.account_manager import AccountManager
from config import settings

# 创建路由
router = APIRouter()

# 设置模板目录
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# 创建账号管理器
account_manager = AccountManager()

# 首页 - 展示所有微博
@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request, 
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    group: Optional[str] = None,
    account_id: Optional[str] = None
):
    # 计算分页
    offset = (page - 1) * per_page
    
    # 构建查询
    query = db.query(Post).order_by(Post.published_at.desc())
    
    # 如果指定了分组，筛选该分组下的所有账号的微博
    if group:
        accounts = account_manager.list_accounts(group=group)
        account_ids = [account.id for account in accounts]
        if account_ids:
            query = query.filter(Post.account_id.in_(account_ids))
        else:
            # 如果分组不存在或没有账号，返回空列表
            return templates.TemplateResponse(
                "index.html", 
                {
                    "request": request, 
                    "posts": [],
                    "page": page,
                    "total_pages": 0,
                    "total_posts": 0,
                    "groups": account_manager.list_groups(),
                    "current_group": group,
                    "current_account_id": None
                }
            )
    
    # 如果指定了账号ID，只显示该账号的微博
    if account_id:
        account = account_manager.get_account(account_id)
        if account:
            query = query.filter(Post.account_id == account.id)
        else:
            # 如果账号不存在，返回空列表
            return templates.TemplateResponse(
                "index.html", 
                {
                    "request": request, 
                    "posts": [],
                    "page": page,
                    "total_pages": 0,
                    "total_posts": 0,
                    "groups": account_manager.list_groups(),
                    "current_group": None,
                    "current_account_id": account_id
                }
            )
    
    # 获取总数
    total_posts = query.count()
    total_pages = (total_posts + per_page - 1) // per_page
    
    # 获取当前页的数据
    posts = query.offset(offset).limit(per_page).all()
    
    # 预加载每个帖子的图片和视频
    for post in posts:
        post.images
        post.videos
    
    # 获取所有分组
    groups = account_manager.list_groups()
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "posts": posts,
            "page": page,
            "total_pages": total_pages,
            "total_posts": total_posts,
            "groups": groups,
            "current_group": group,
            "current_account_id": account_id
        }
    )

# 设置页面 - 展示所有账号
@router.get("/settings", response_class=HTMLResponse)
async def settings_page(
    request: Request,
    include_disabled: bool = Query(False, alias="show_disabled"),
    group: Optional[str] = None
):
    # 获取账号列表
    accounts = account_manager.list_accounts(include_disabled=include_disabled, group=group)
    
    # 获取所有分组
    groups = account_manager.list_groups()
    
    return templates.TemplateResponse(
        "settings.html", 
        {
            "request": request, 
            "accounts": accounts,
            "groups": groups,
            "current_group": group,
            "show_disabled": include_disabled
        }
    )

# 添加账号
@router.post("/accounts/add")
async def add_account(
    account_id: str = Form(...),
    group: str = Form("default")
):
    # 添加账号
    account = account_manager.add_account(account_id, group)
    if not account:
        raise HTTPException(status_code=400, detail="添加账号失败")
    
    # 重定向回设置页面
    return RedirectResponse(url="/settings", status_code=303)

# 删除账号
@router.post("/accounts/delete")
async def delete_account(
    account_id: str = Form(...),
    hard_delete: bool = Form(False)
):
    # 删除账号
    success = account_manager.delete_account(account_id, hard_delete)
    if not success:
        raise HTTPException(status_code=400, detail="删除账号失败")
    
    # 重定向回设置页面
    return RedirectResponse(url="/settings", status_code=303)

# 获取图片
@router.get("/images/{image_type}/{image_id}")
async def get_image(image_type: str, image_id: str):
    # 根据类型选择目录
    if image_type == "original":
        image_path = os.path.join(settings.ORIGINAL_IMAGES_DIR, image_id)
    elif image_type == "thumbnail":
        image_path = os.path.join(settings.THUMBNAIL_IMAGES_DIR, image_id)
    else:
        raise HTTPException(status_code=400, detail="无效的图片类型")
    
    # 检查文件是否存在
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="图片不存在")
    
    # 返回文件
    return FileResponse(image_path)

# API路由 - 获取所有微博
@router.get("/api/posts")
async def get_posts(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    group: Optional[str] = None,
    account_id: Optional[str] = None
):
    # 计算分页
    offset = (page - 1) * per_page
    
    # 构建查询
    query = db.query(Post).order_by(Post.published_at.desc())
    
    # 如果指定了分组，筛选该分组下的所有账号的微博
    if group:
        accounts = account_manager.list_accounts(group=group)
        account_ids = [account.id for account in accounts]
        if account_ids:
            query = query.filter(Post.account_id.in_(account_ids))
    
    # 如果指定了账号ID，只显示该账号的微博
    if account_id:
        account = account_manager.get_account(account_id)
        if account:
            query = query.filter(Post.account_id == account.id)
    
    # 获取总数
    total_posts = query.count()
    
    # 获取当前页的数据
    posts = query.offset(offset).limit(per_page).all()
    
    # 转换为字典列表
    result = []
    for post in posts:
        post_dict = {
            "id": post.id,
            "source": post.source,
            "source_id": post.source_id,
            "title": post.title,
            "content": post.content,
            "link": post.link,
            "published_at": post.published_at.isoformat(),
            "account": {
                "id": post.account.id,
                "account_id": post.account.account_id,
                "account_name": post.account.account_name,
                "group": post.account.group
            },
            "images": [
                {
                    "id": image.id,
                    "image_id": image.image_id,
                    "original_url": f"/images/original/{image.image_id}",
                    "thumbnail_url": f"/images/thumbnail/{image.image_id}"
                }
                for image in post.images
            ],
            "videos": [
                {
                    "id": video.id,
                    "video_id": video.video_id,
                    "video_url": video.video_url
                }
                for video in post.videos
            ]
        }
        result.append(post_dict)
    
    return {
        "posts": result,
        "page": page,
        "per_page": per_page,
        "total": total_posts
    }

# API路由 - 获取所有账号
@router.get("/api/accounts")
async def get_accounts(
    include_disabled: bool = Query(False),
    group: Optional[str] = None
):
    # 获取账号列表
    accounts = account_manager.list_accounts(include_disabled=include_disabled, group=group)
    
    # 转换为字典列表
    result = []
    for account in accounts:
        account_dict = {
            "id": account.id,
            "account_id": account.account_id,
            "account_name": account.account_name,
            "account_subtitle": account.account_subtitle,
            "account_link": account.account_link,
            "rss_link": account.rss_link,
            "status": account.status,
            "group": account.group,
            "created_at": account.created_at.isoformat(),
            "updated_at": account.updated_at.isoformat()
        }
        result.append(account_dict)
    
    return result

# API路由 - 获取所有分组
@router.get("/api/groups")
async def get_groups():
    # 获取所有分组
    groups = account_manager.list_groups()
    
    return groups
