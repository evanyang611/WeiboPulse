#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调度器服务
负责管理所有定时任务
"""

from typing import Dict, Any, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.job import Job
from datetime import datetime
import logging

from services.rss_parser import RSSParser
from services.account_manager import AccountManager
from services.settings_manager import SettingsManager
from utils.logger import get_logger

class SchedulerService:
    """调度器服务类"""
    
    def __init__(self):
        """初始化调度器服务"""
        self.scheduler = AsyncIOScheduler()
        self.logger = get_logger("scheduler")
        self.account_manager = AccountManager()
        self.settings_manager = SettingsManager()
        self._jobs: Dict[str, Job] = {}  # 存储任务ID到任务对象的映射
        
    async def start(self):
        """启动调度器并加载所有定时任务"""
        if not self.scheduler.running:
            self.scheduler.start()
            await self.reload_all_jobs()
            self.logger.info("调度器已启动")
    
    async def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.logger.info("调度器已停止")
    
    async def reload_all_jobs(self):
        """重新加载所有定时任务"""
        # 获取所有定时任务设置
        schedule_settings = self.settings_manager.list_settings(prefix="schedule_group_")
        
        # 清除所有现有任务
        self._remove_all_jobs()
        
        # 添加新任务
        for setting in schedule_settings:
            group = setting.key.replace("schedule_group_", "")
            schedule = setting.value
            await self.add_job(group, schedule)
    
    def _remove_all_jobs(self):
        """移除所有定时任务"""
        for job_id in list(self._jobs.keys()):
            self.remove_job(job_id)
    
    def remove_job(self, job_id: str):
        """移除指定的定时任务
        
        Args:
            job_id: 任务ID
        """
        if job_id in self._jobs:
            self.scheduler.remove_job(job_id)
            del self._jobs[job_id]
            self.logger.info(f"已移除定时任务: {job_id}")
    
    async def add_job(self, group: str, schedule: str) -> Optional[str]:
        """添加定时任务
        
        Args:
            group: 分组名称
            schedule: 调度设置（格式："{value} {unit}"）
            
        Returns:
            str: 任务ID，如果添加失败则返回None
        """
        try:
            # 解析调度设置
            value, unit = schedule.split()
            value = int(value)
            
            # 转换单位到秒
            seconds = {
                'seconds': 1,
                'minutes': 60,
                'hours': 3600
            }.get(unit, 1) * value
            
            # 生成任务ID
            job_id = f"refresh_group_{group}"
            
            # 如果任务已存在，先移除
            if job_id in self._jobs:
                self.remove_job(job_id)
            
            # 创建新任务
            job = self.scheduler.add_job(
                self._refresh_group,
                trigger=IntervalTrigger(seconds=seconds),
                args=[group],
                id=job_id,
                name=f"刷新分组 {group}",
                replace_existing=True
            )
            
            self._jobs[job_id] = job
            self.logger.info(f"已添加定时任务: {job_id}, 间隔: {value} {unit}")
            
            return job_id
            
        except Exception as e:
            self.logger.error(f"添加定时任务失败: {str(e)}")
            return None
    
    async def _refresh_group(self, group: str):
        """刷新指定分组的所有账号
        
        Args:
            group: 分组名称
        """
        try:
            self.logger.info(f"开始执行定时刷新任务: 分组 {group}")
            
            # 获取分组内的账号
            accounts = self.account_manager.list_accounts(group=group)
            if not accounts:
                self.logger.warning(f"分组 {group} 中没有可用账号")
                return
            
            # 创建RSS解析器
            parser = RSSParser(if_download=True, max_concurrent=5)
            
            # 记录总数
            total_posts = 0
            
            # 遍历每个账号并解析RSS
            for account in accounts:
                try:
                    # 解析RSS源
                    posts = parser.parse_feed(account.rss_link, account=account)
                    total_posts += len(posts)
                except Exception as e:
                    self.logger.error(f"解析账号 {account.account_name} 的RSS源时出错: {str(e)}")
                    continue
            
            self.logger.info(f"定时刷新任务完成: 分组 {group}, 获取到 {total_posts} 条微博")
            
        except Exception as e:
            self.logger.error(f"执行定时刷新任务时出错: {str(e)}")

# 全局调度器实例
scheduler_service = SchedulerService() 