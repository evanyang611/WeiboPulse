from fastapi import APIRouter, Depends, HTTPException, Query, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
import os
from pathlib import Path
import datetime

from database.config import get_db
from database.models import Post, Account, Image, Video
from services.account_manager import AccountManager
from services.settings_manager import SettingsManager
from config import settings

# 创建路由
router = APIRouter()

# 设置模板目录
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# 创建账号管理器
account_manager = AccountManager()
# 创建设置管理器
settings_manager = SettingsManager()

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
    
    # 获取定时任务设置
    schedule_settings = settings_manager.get_schedule_settings()
    
    return templates.TemplateResponse(
        "settings.html", 
        {
            "request": request, 
            "accounts": accounts,
            "groups": groups,
            "current_group": group,
            "show_disabled": include_disabled,
            "schedule_settings": schedule_settings
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

# 日志页面 - 展示日志
@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request, date: Optional[str] = None):
    """显示指定日期的日志页面，默认为当天"""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 获取所有可用的日志文件
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    available_logs = []
    
    if logs_dir.exists():
        # 获取所有.log文件并提取日期部分
        for log_file in logs_dir.glob("*.log"):
            # 只处理符合日期格式的日志文件（如2025-03-01.log）
            if log_file.stem.count("-") == 2 and len(log_file.stem) == 10:
                available_logs.append(log_file.stem)
    
    # 按日期降序排序（最新的在前）
    available_logs.sort(reverse=True)
    
    # 如果没有指定日期或指定的日期不在可用列表中，使用当天或最新的日志
    if not date or date not in available_logs:
        date = today if today in available_logs else (available_logs[0] if available_logs else today)
    
    log_file = f"{date}.log"
    log_path = logs_dir / log_file
    
    log_content = []
    last_updated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if log_path.exists():
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                # 读取最后100行
                log_content = f.readlines()[-100:]
                # 去除每行末尾的换行符
                log_content = [line.rstrip() for line in log_content]
        except Exception as e:
            log_content = [f"读取日志文件出错: {str(e)}"]
    
    return templates.TemplateResponse(
        "logs.html",
        {
            "request": request,
            "current_date": date,
            "log_file": log_file,
            "log_content": log_content,
            "last_updated": last_updated,
            "available_logs": available_logs
        }
    )

# API路由 - 获取最新日志
@router.get("/api/logs", response_class=JSONResponse)
async def get_logs(date: Optional[str] = None):
    """获取指定日期的日志内容，默认为当天"""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 获取所有可用的日志文件
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    available_logs = []
    
    if logs_dir.exists():
        # 获取所有.log文件并提取日期部分
        for log_file in logs_dir.glob("*.log"):
            # 只处理符合日期格式的日志文件（如2025-03-01.log）
            if log_file.stem.count("-") == 2 and len(log_file.stem) == 10:
                available_logs.append(log_file.stem)
    
    # 按日期降序排序（最新的在前）
    available_logs.sort(reverse=True)
    
    # 如果没有指定日期或指定的日期不在可用列表中，使用当天或最新的日志
    if not date or date not in available_logs:
        date = today if today in available_logs else (available_logs[0] if available_logs else today)
    
    log_file = f"{date}.log"
    log_path = logs_dir / log_file
    
    log_content = []
    last_updated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if log_path.exists():
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                # 读取最后100行
                log_content = f.readlines()[-100:]
                # 去除每行末尾的换行符
                log_content = [line.rstrip() for line in log_content]
        except Exception as e:
            log_content = [f"读取日志文件出错: {str(e)}"]
    
    return {
        "log_file": log_file,
        "log_content": log_content,
        "last_updated": last_updated,
        "available_logs": available_logs
    }

# 添加或更新定时任务设置
@router.post("/settings/schedule")
async def set_schedule(
    group: str = Form(...),
    schedule_value: int = Form(...),
    schedule_unit: str = Form(...)
):
    # 验证单位
    if schedule_unit not in ["seconds", "minutes", "hours"]:
        raise HTTPException(status_code=400, detail="无效的时间单位")
    
    # 验证值
    if schedule_value < 1:
        raise HTTPException(status_code=400, detail="时间值必须大于0")
    
    # 组合成简单的格式："{value} {unit}"
    schedule = f"{schedule_value} {schedule_unit}"
    
    # 设置键名格式为 schedule_group_{group_name}
    key = f"schedule_group_{group}"
    description = f"定时刷新分组 {group} 的时间设置"
    
    # 保存设置
    setting = settings_manager.set_setting(key, schedule, description)
    if not setting:
        raise HTTPException(status_code=400, detail="保存设置失败")
    
    # 重定向回设置页面
    return RedirectResponse(url="/settings", status_code=303)

# 删除定时任务设置
@router.post("/settings/schedule/delete")
async def delete_schedule(
    group: str = Form(...)
):
    # 设置键名格式为 schedule_group_{group_name}
    key = f"schedule_group_{group}"
    
    # 删除设置
    success = settings_manager.delete_setting(key)
    if not success:
        raise HTTPException(status_code=400, detail="删除设置失败")
    
    # 重定向回设置页面
    return RedirectResponse(url="/settings", status_code=303)
