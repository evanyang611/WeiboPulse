#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM服务
负责管理与大语言模型相关的定时任务，如话题总结
"""

from typing import Dict, Any, Optional, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.job import Job
from datetime import datetime, timedelta
import json
import os
import asyncio
from dotenv import load_dotenv

from services.account_manager import AccountManager
from services.settings_manager import SettingsManager
from database.config import get_db
from database.models import Post, Account, LLMResult
from utils.logger import get_logger
from utils.qwen_client import QwenClient
from config.prompts import PROMPT_DAILY_TOPIC_SUMMARY

# 加载.env文件（如果存在）
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path)

class LLMService:
    """LLM服务类，负责管理与大语言模型相关的定时任务"""
    
    def __init__(self):
        """初始化LLM服务"""
        self.scheduler = AsyncIOScheduler()
        self.logger = get_logger("llm_service")
        self.account_manager = AccountManager()
        self.settings_manager = SettingsManager()
        self._jobs: Dict[str, Job] = {}  # 存储任务ID到任务对象的映射
        
    async def start(self):
        """启动调度器并加载所有定时任务"""
        if not self.scheduler.running:
            self.scheduler.start()
            await self.reload_all_jobs()
            self.logger.info("LLM服务调度器已启动")
    
    async def stop(self):
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.logger.info("LLM服务调度器已停止")
    
    async def reload_all_jobs(self):
        """重新加载所有定时任务"""
        # 清除所有现有任务
        self._remove_all_jobs()
        
        # 获取话题总结设置
        topic_summary_setting = self.settings_manager.get_setting("topic_summary")
        if topic_summary_setting:
            try:
                setting_value = json.loads(topic_summary_setting.value)
                if isinstance(setting_value, dict) and "interval" in setting_value:
                    await self.add_topic_summary_job(setting_value)
                else:
                    self.logger.warning("话题总结设置格式无效")
            except json.JSONDecodeError:
                self.logger.error(f"无法解析话题总结设置: {topic_summary_setting.value}")
        else:
            self.logger.info("未找到话题总结设置，跳过添加定时任务")
    
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
    
    async def add_topic_summary_job(self, settings: Dict[str, Any]) -> Optional[str]:
        """添加话题总结定时任务
        
        Args:
            settings: 话题总结设置，包含interval、group和topics
            
        Returns:
            str: 任务ID，如果添加失败则返回None
        """
        try:
            # 解析调度设置
            interval = settings.get("interval", "24 hours")
            value, unit = interval.split()
            value = int(value)
            
            # 转换单位到秒
            seconds = {
                'seconds': 1,
                'minutes': 60,
                'hours': 3600
            }.get(unit, 3600) * value
            
            # 生成任务ID
            job_id = "topic_summary"
            
            # 如果任务已存在，先移除
            if job_id in self._jobs:
                self.remove_job(job_id)
            
            # 创建新任务
            job = self.scheduler.add_job(
                self._run_topic_summary,
                trigger=IntervalTrigger(seconds=seconds),
                id=job_id,
                name="话题总结",
                replace_existing=True
            )
            
            self._jobs[job_id] = job
            self.logger.info(f"已添加话题总结定时任务，间隔: {value} {unit}")
            
            # 不再每次都更新设置中的上次更新时间，只在实际执行总结任务时更新
            
            return job_id
            
        except Exception as e:
            self.logger.error(f"添加话题总结定时任务失败: {str(e)}")
            return None
    
    async def _run_topic_summary(self):
        """执行话题总结任务"""
        try:
            self.logger.info("开始执行话题总结任务")
            
            # 获取话题总结设置
            setting = self.settings_manager.get_setting("topic_summary")
            if not setting:
                self.logger.warning("未找到话题总结设置，无法执行任务")
                return
                
            try:
                # 解析设置
                setting_value = json.loads(setting.value)
                
                # 验证设置
                if not isinstance(setting_value, dict):
                    self.logger.error("话题总结设置不是有效的JSON对象")
                    return
                    
                # 检查必要字段
                required_fields = ["interval", "group", "topics"]
                for field in required_fields:
                    if field not in setting_value:
                        self.logger.error(f"话题总结设置缺少必要字段: {field}")
                        return
                
                # 获取设置值
                group = setting_value["group"]
                topics = setting_value["topics"]
                interval_str = setting_value["interval"]
                
                # 解析时间间隔
                hours = self._parse_interval_to_hours(interval_str)
                
                # 获取最近的帖子
                posts = await self._get_recent_posts_by_group(group, hours)
                
                if not posts:
                    self.logger.warning(f"分组 '{group}' 在过去 {hours} 小时内没有微博，跳过总结")
                    return
                
                # 生成总结
                # 使用导入的提示词模板
                prompt_template = PROMPT_DAILY_TOPIC_SUMMARY
                
                # 替换模板中的占位符
                topics_str = json.dumps(topics, ensure_ascii=False)
                posts_str = json.dumps(posts, ensure_ascii=False)
                
                message = prompt_template.replace("【关心话题】", topics_str).replace("【微博内容】", posts_str)
                
                summary = await self._generate_topic_summary(message)
                model_name = os.getenv("TEXT_MODEL") # 仅文字模型
                
                if summary:
                    # 保存结果
                    await self._save_llm_result("daily_topic_summary", model_name, message, summary)
                    
                    # 更新设置中的上次更新时间
                    setting_value["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    self.settings_manager.set_setting(
                        key="topic_summary",
                        value=json.dumps(setting_value, ensure_ascii=False),
                        description="话题总结设置"
                    )
                    
                    self.logger.info("话题总结任务完成")
                else:
                    self.logger.warning("生成总结失败")
                
            except json.JSONDecodeError:
                self.logger.error(f"无法解析话题总结设置: {setting.value}")
                return
                
        except Exception as e:
            self.logger.error(f"执行话题总结任务时出错: {str(e)}")
    
    def _parse_interval_to_hours(self, interval_str: str) -> float:
        """解析时间间隔字符串，转换为小时数
        
        Args:
            interval_str: 时间间隔字符串，格式为"{value} {unit}"，例如"30 minutes"
            
        Returns:
            float: 转换后的小时数
        """
        try:
            value, unit = interval_str.split()
            value = int(value)
            
            # 转换单位到小时
            if unit == 'seconds':
                return value / 3600  # 秒转小时
            elif unit == 'minutes':
                return value / 60  # 分钟转小时
            elif unit == 'hours':
                return value  # 小时
            else:
                self.logger.warning(f"不支持的时间单位: {unit}，使用默认值24小时")
                return 24
        except Exception as e:
            self.logger.error(f"无效的时间间隔格式: {interval_str}, {str(e)}")
            return 24  # 默认24小时
    
    async def _get_recent_posts_by_group(self, group: str, hours: float) -> List[Dict[str, Any]]:
        """获取指定分组过去几小时的微博帖子
        
        Args:
            group: 分组名称
            hours: 过去几小时
            
        Returns:
            查询结果列表
        """
        # 获取数据库会话
        db = next(get_db())
        
        try:
            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)
            
            self.logger.info(f"查询分组 '{group}' 在 {start_time} 到 {end_time} 之间的微博")
            
            # 获取分组内的账号ID列表
            accounts = self.account_manager.list_accounts(group=group)
            
            if not accounts:
                self.logger.warning(f"分组 '{group}' 中没有账号")
                return []
                
            account_ids = [account.id for account in accounts]
            
            # 构建查询
            query = db.query(Post).join(Account).filter(
                Post.published_at >= start_time,
                Post.published_at <= end_time,
                Post.account_id.in_(account_ids)
            )
            
            # 添加排序
            query = query.order_by(Post.published_at.desc())
            
            # 执行查询
            posts = []
            for post in query.all():
                post_dict = {
                    "published_at": post.published_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "id": post.id,
                    "account_name": post.account.account_name,
                    "content": post.content
                }
                posts.append(post_dict)
                
            self.logger.info(f"查询到 {len(posts)} 条微博")
            return posts
        finally:
            db.close()
    
    async def _generate_topic_summary(self, message: str) -> Optional[str]:
        """生成话题总结
        
        Args:
            topics: 关心的话题列表
            posts: 微博帖子列表
            
        Returns:
            生成的总结内容，如果生成失败则返回None
        """
        
        self.logger.info(f"准备调用大模型，提示词长度: {len(message)}")
        
        # 调用大模型
        try:
            qwen = QwenClient()            
            # 调用API
            response = qwen.chat(
                message=message,
                temperature=0.0,
                stream=False
            )
            
            return response
                
        except Exception as e:
            self.logger.error(f"调用大模型生成总结时出错: {str(e)}")
            return None
    
    async def _save_llm_result(self, objective: str, model: str, input_content: Any, output_content: str) -> Optional[int]:
        """保存大模型调用结果到数据库
        
        Args:
            objective: 调用目的
            model: 使用的模型名称
            input_content: 输入内容
            output_content: 输出内容
            
        Returns:
            新创建记录的ID，如果保存失败则返回None
        """
        # 获取数据库会话
        db = next(get_db())
        
        try:
            # 如果输入内容不是字符串，转换为JSON字符串
            if not isinstance(input_content, str):
                input_content = json.dumps(input_content, ensure_ascii=False)
            
            # 创建新记录
            llm_result = LLMResult(
                time=datetime.now(),
                objective=objective,
                model=model,
                input=input_content,
                output=output_content
            )
            
            # 添加到数据库
            db.add(llm_result)
            db.commit()
            
            # 刷新以获取ID
            db.refresh(llm_result)
            
            self.logger.info(f"已保存大模型调用结果，ID: {llm_result.id}, 目的: {objective}")
            return llm_result.id
            
        except Exception as e:
            db.rollback()
            self.logger.error(f"保存大模型调用结果失败: {str(e)}")
            return None
        finally:
            db.close()
    
    async def run_topic_summary_now(self) -> bool:
        """立即执行话题总结任务
        
        Returns:
            bool: 是否成功启动任务
        """
        try:
            self.logger.info("手动触发话题总结任务")
            
            # 创建异步任务
            asyncio.create_task(self._run_topic_summary())
            
            return True
        except Exception as e:
            self.logger.error(f"手动触发话题总结任务失败: {str(e)}")
            return False

# 全局LLM服务实例
llm_service = LLMService() 