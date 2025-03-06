#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
设置管理器
"""

from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from database.models import Settings
from utils.logger import get_logger
from config import settings as app_settings

class SettingsManager:
    """设置管理器"""
    
    def __init__(self):
        """初始化设置管理器"""
        self.logger = get_logger("settings_manager")
        self.engine = create_engine(app_settings.DATABASE_URL)
    
    def get_setting(self, key: str) -> Optional[Settings]:
        """获取单个设置
        
        Args:
            key: 设置键名
            
        Returns:
            Settings: 设置对象，如果不存在则返回 None
        """
        try:
            with Session(self.engine) as session:
                setting = session.query(Settings).filter_by(key=key).first()
                return setting
        except Exception as e:
            self.logger.error(f"获取设置时出错: {str(e)}")
            return None
    
    def get_setting_value(self, key: str, default: str = "") -> str:
        """获取设置值
        
        Args:
            key: 设置键名
            default: 默认值，如果设置不存在则返回此值
            
        Returns:
            str: 设置值
        """
        setting = self.get_setting(key)
        if setting:
            return setting.value
        return default
    
    def set_setting(self, key: str, value: str, description: str = "") -> Optional[Settings]:
        """设置或更新设置
        
        Args:
            key: 设置键名
            value: 设置值
            description: 设置描述
            
        Returns:
            Settings: 设置对象，如果操作失败则返回 None
        """
        try:
            with Session(self.engine) as session:
                # 检查设置是否已存在
                setting = session.query(Settings).filter_by(key=key).first()
                
                if setting:
                    # 更新现有设置
                    setting.value = value
                    if description:
                        setting.description = description
                else:
                    # 创建新设置
                    setting = Settings(
                        key=key,
                        value=value,
                        description=description
                    )
                    session.add(setting)
                
                session.commit()
                self.logger.info(f"成功设置: {key} = {value}")
                return setting
                
        except Exception as e:
            self.logger.error(f"设置值时出错: {str(e)}")
            return None
    
    def delete_setting(self, key: str) -> bool:
        """删除设置
        
        Args:
            key: 设置键名
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with Session(self.engine) as session:
                setting = session.query(Settings).filter_by(key=key).first()
                if not setting:
                    self.logger.warning(f"设置不存在: {key}")
                    return False
                
                session.delete(setting)
                session.commit()
                self.logger.info(f"已删除设置: {key}")
                return True
                
        except Exception as e:
            self.logger.error(f"删除设置时出错: {str(e)}")
            return False
    
    def list_settings(self, prefix: str = "") -> List[Settings]:
        """获取所有设置列表
        
        Args:
            prefix: 设置键名前缀，用于筛选特定类型的设置
            
        Returns:
            List[Settings]: 设置列表
        """
        try:
            with Session(self.engine) as session:
                query = session.query(Settings)
                
                # 如果指定了前缀，筛选匹配的设置
                if prefix:
                    query = query.filter(Settings.key.like(f"{prefix}%"))
                
                return query.all()
        except Exception as e:
            self.logger.error(f"获取设置列表时出错: {str(e)}")
            return []
    
    def get_schedule_settings(self) -> List[Tuple[str, str]]:
        """获取所有定时任务设置
        
        Returns:
            List[Tuple[str, str]]: 分组名称和时间设置的元组列表
        """
        settings = self.list_settings(prefix="schedule_group_")
        result = []
        
        for setting in settings:
            group = setting.key.replace("schedule_group_", "")
            result.append((group, setting.value))
        
        return result 