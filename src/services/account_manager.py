import feedparser
from typing import Optional, Dict, Any, List
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
            
    def add_account(self, account_id: str, group: str = 'default') -> Optional[Account]:
        """添加新账号
        
        Args:
            account_id: 微博账号ID
            group: 账号分组，默认为'default'
            
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
                    # 如果账号存在但状态为0，则更新状态为1
                    if existing.status == 0:
                        existing.status = 1
                        existing.group = group
                        session.commit()
                        self.logger.info(f"已重新启用账号: {existing.account_name} (ID: {existing.account_id})")
                    # 如果分组不同，更新分组
                    elif existing.group != group:
                        existing.group = group
                        session.commit()
                        self.logger.info(f"已更新账号分组: {existing.account_name} (ID: {existing.account_id}) -> {group}")
                    return existing
                
                # 创建新账号
                account = Account(
                    source='weibo',
                    account_id=account_info['account_id'],
                    account_name=account_info['account_name'],
                    account_subtitle=account_info['account_subtitle'],
                    account_link=account_info['account_link'],
                    rss_link=account_info['rss_link'],
                    status=1,
                    group=group
                )
                
                # 保存到数据库
                session.add(account)
                session.commit()
                
                self.logger.info(f"成功添加账号: {account.account_name} (ID: {account.account_id}) 到分组: {group}")
                return account
                
        except Exception as e:
            self.logger.error(f"添加账号时出错: {str(e)}")
            return None
    
    def delete_account(self, account_id: str, hard_delete: bool = False) -> bool:
        """删除账号
        
        Args:
            account_id: 微博账号ID
            hard_delete: 是否硬删除，默认为False（软删除，仅将状态设为0）
            
        Returns:
            bool: 删除是否成功
        """
        try:
            with Session(self.engine) as session:
                account = session.query(Account).filter_by(account_id=account_id).first()
                if not account:
                    self.logger.warning(f"账号不存在: {account_id}")
                    return False
                
                if hard_delete:
                    # 硬删除：从数据库中删除记录
                    session.delete(account)
                    self.logger.info(f"已硬删除账号: {account.account_name} (ID: {account.account_id})")
                else:
                    # 软删除：将状态设为0
                    account.status = 0
                    self.logger.info(f"已软删除账号: {account.account_name} (ID: {account.account_id})")
                
                session.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"删除账号时出错: {str(e)}")
            return False
            
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
    
    def list_accounts(self, include_disabled: bool = False, group: Optional[str] = None) -> List[Account]:
        """获取所有账号列表
        
        Args:
            include_disabled: 是否包含已禁用的账号，默认为False
            group: 筛选特定分组的账号，默认为None（不筛选）
            
        Returns:
            List[Account]: 账号列表
        """
        try:
            with Session(self.engine) as session:
                query = session.query(Account)
                
                # 是否包含已禁用账号
                if not include_disabled:
                    query = query.filter(Account.status == 1)
                
                # 是否筛选特定分组
                if group:
                    query = query.filter(Account.group == group)
                
                return query.all()
        except Exception as e:
            self.logger.error(f"获取账号列表时出错: {str(e)}")
            return []
    
    def list_groups(self) -> List[str]:
        """获取所有分组列表
        
        Returns:
            List[str]: 分组名称列表
        """
        try:
            with Session(self.engine) as session:
                # 查询所有不同的分组名称
                groups = session.query(Account.group).distinct().all()
                # 将结果转换为字符串列表
                return [g[0] for g in groups]
        except Exception as e:
            self.logger.error(f"获取分组列表时出错: {str(e)}")
            return []
