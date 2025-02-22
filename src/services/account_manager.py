import feedparser
from typing import Optional, Dict, Any
import logging
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from urllib.parse import urljoin

from config import settings
from database.models import Account
from utils.logger import get_logger

class AccountManager:
    """账号管理器"""
    
    def __init__(self):
        """初始化账号管理器"""
        self.logger = get_logger("account_manager")
        self.engine = create_engine(settings.DATABASE_URL)
        
    def _get_account_info(self, account_id: str) -> Optional[Dict[str, Any]]:
        """从RSS源获取账号信息
        
        Args:
            account_id: 微博账号ID
            
        Returns:
            Dict: 包含账号信息的字典，如果获取失败则返回 None
        """
        # 构建RSS链接
        rss_link = urljoin(settings.RSS_BASE_URL, account_id)
        
        try:
            # 解析RSS源
            feed = feedparser.parse(rss_link)
            
            # 检查是否成功获取到feed
            if not feed.feed:
                self.logger.error(f"未能获取到RSS源信息: {rss_link}")
                return None
                
            # 提取账号信息
            feed_info = feed.feed
            account_name = feed_info.get('title', '').replace('的微博', '')  # 移除"的微博"后缀
            
            return {
                'account_id': account_id,
                'account_name': account_name,
                'account_subtitle': feed_info.get('subtitle', ''),
                'account_link': feed_info.get('link', ''),
                'rss_link': rss_link
            }
            
        except Exception as e:
            self.logger.error(f"获取RSS源信息出错: {str(e)}")
            return None
            
    def add_account(self, account_id: str) -> Optional[Account]:
        """添加新账号
        
        Args:
            account_id: 微博账号ID
            
        Returns:
            Account: 创建的账号对象，如果创建失败则返回 None
        """
        # 获取账号信息
        account_info = self._get_account_info(account_id)
        if not account_info:
            return None
            
        try:
            # 创建数据库会话
            with Session(self.engine) as session:
                # 检查账号是否已存在
                existing = session.query(Account).filter_by(account_id=account_id).first()
                if existing:
                    self.logger.warning(f"账号已存在: {account_id}")
                    return existing
                
                # 创建新账号
                account = Account(
                    source='weibo',
                    account_id=account_info['account_id'],
                    account_name=account_info['account_name'],
                    account_subtitle=account_info['account_subtitle'],
                    account_link=account_info['account_link'],
                    rss_link=account_info['rss_link']
                )
                
                # 保存到数据库
                session.add(account)
                session.commit()
                
                self.logger.info(f"成功添加账号: {account.account_name} (ID: {account.account_id})")
                return account
                
        except Exception as e:
            self.logger.error(f"添加账号时出错: {str(e)}")
            return None
            
    def get_account(self, account_id: str) -> Optional[Account]:
        """获取账号信息
        
        Args:
            account_id: 微博账号ID
            
        Returns:
            Account: 账号对象，如果不存在则返回 None
        """
        try:
            with Session(self.engine) as session:
                return session.query(Account).filter_by(account_id=account_id).first()
        except Exception as e:
            self.logger.error(f"获取账号信息时出错: {str(e)}")
            return None
            
    def list_accounts(self) -> list[Account]:
        """获取所有账号列表
        
        Returns:
            List[Account]: 账号列表
        """
        try:
            with Session(self.engine) as session:
                return session.query(Account).all()
        except Exception as e:
            self.logger.error(f"获取账号列表时出错: {str(e)}")
            return []
