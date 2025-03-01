#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WeiboScraper 主入口文件
"""

import sys
from pathlib import Path

# 将src目录添加到Python路径
src_dir = str(Path(__file__).parent.parent)
if src_dir not in sys.path:
    sys.path.append(src_dir)

import argparse
from services.rss_parser import RSSParser
from services.account_manager import AccountManager
from sqlalchemy import create_engine
from config import settings

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='WeiboScraper - 微博 RSS 解析工具')
    
    # 创建子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 添加账号命令
    add_parser = subparsers.add_parser('add', help='添加新账号')
    add_parser.add_argument('account_id', type=str, help='微博账号ID，例如：5130681470')
    add_parser.add_argument('--group', type=str, default='default', help='账号分组，默认为default')
    
    # 删除账号命令
    delete_parser = subparsers.add_parser('delete', help='删除账号')
    delete_parser.add_argument('account_id', type=str, help='微博账号ID，例如：5130681470')
    delete_parser.add_argument('--hard', action='store_true', help='硬删除（从数据库中完全删除），默认为软删除（仅禁用）')
    
    # 列出账号命令
    list_parser = subparsers.add_parser('list', help='列出所有账号')
    list_parser.add_argument('--all', action='store_true', help='包含已禁用的账号')
    list_parser.add_argument('--group', type=str, help='筛选特定分组的账号')
    
    # 列出分组命令
    subparsers.add_parser('list-groups', help='列出所有分组')
    
    # 抓取命令
    fetch_parser = subparsers.add_parser('fetch', help='抓取指定账号的微博')
    fetch_parser.add_argument('account_id', type=str, help='微博账号ID，例如：5130681470')
    fetch_parser.add_argument('--no-download', action='store_true', help='不下载媒体文件')
    
    # 抓取分组命令
    fetch_group_parser = subparsers.add_parser('fetch-group', help='抓取指定分组的所有账号的微博')
    fetch_group_parser.add_argument('group', type=str, help='分组名称')
    fetch_group_parser.add_argument('--no-download', action='store_true', help='不下载媒体文件')
    
    return parser.parse_args()

def init_database():
    """初始化数据库"""
    from database.models import Base
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(engine)

def main():
    """主函数"""
    # 初始化数据库
    init_database()
    
    # 解析命令行参数
    args = parse_args()
    
    # 创建账号管理器
    account_manager = AccountManager()
    
    if args.command == 'add':
        # 添加新账号
        account = account_manager.add_account(args.account_id, args.group)
        if account:
            print(f"成功添加账号：{account.account_name}")
            print(f"账号ID：{account.account_id}")
            print(f"账号简介：{account.account_subtitle}")
            print(f"账号链接：{account.account_link}")
            print(f"RSS链接：{account.rss_link}")
            print(f"分组：{account.group}")
        else:
            print(f"添加账号失败：{args.account_id}")
    
    elif args.command == 'delete':
        # 删除账号
        success = account_manager.delete_account(args.account_id, args.hard)
        if success:
            if args.hard:
                print(f"已硬删除账号：{args.account_id}")
            else:
                print(f"已软删除账号：{args.account_id}（可通过add命令重新启用）")
        else:
            print(f"删除账号失败：{args.account_id}")
            
    elif args.command == 'list':
        # 列出所有账号
        accounts = account_manager.list_accounts(include_disabled=args.all, group=args.group)
        if accounts:
            print(f"共有 {len(accounts)} 个账号：")
            for account in accounts:
                status_text = "正常" if account.status == 1 else "已禁用"
                print(f"\n账号：{account.account_name}")
                print(f"账号ID：{account.account_id}")
                print(f"账号简介：{account.account_subtitle}")
                print(f"账号链接：{account.account_link}")
                print(f"RSS链接：{account.rss_link}")
                print(f"分组：{account.group}")
                print(f"状态：{status_text}")
        else:
            print("暂无账号")
    
    elif args.command == 'list-groups':
        # 列出所有分组
        groups = account_manager.list_groups()
        if groups:
            print(f"共有 {len(groups)} 个分组：")
            for group in groups:
                # 获取该分组下的账号数量
                accounts = account_manager.list_accounts(group=group)
                print(f"- {group}（{len(accounts)}个账号）")
        else:
            print("暂无分组")
            
    elif args.command == 'fetch':
        # 获取账号信息
        account = account_manager.get_account(args.account_id)
        if not account:
            print(f"账号不存在：{args.account_id}")
            return
        
        if account.status == 0:
            print(f"账号已禁用：{args.account_id}")
            return
            
        # 创建RSS解析器
        parser = RSSParser(if_download=not args.no_download)
        
        # 解析RSS源
        posts = parser.parse_feed(account.rss_link, account=account)
        
        # 处理结果
        print(f"共解析 {len(posts)} 条微博")
    
    elif args.command == 'fetch-group':
        # 获取指定分组的所有账号
        accounts = account_manager.list_accounts(group=args.group)
        if not accounts:
            print(f"分组不存在或分组中没有账号：{args.group}")
            return
        
        # 创建RSS解析器
        parser = RSSParser(if_download=not args.no_download)
        
        total_posts = 0
        print(f"开始抓取分组 {args.group} 中的 {len(accounts)} 个账号")
        
        # 遍历每个账号
        for account in accounts:
            print(f"\n开始抓取账号：{account.account_name} (ID: {account.account_id})")
            
            # 解析RSS源
            posts = parser.parse_feed(account.rss_link, account=account)
            
            # 处理结果
            print(f"账号 {account.account_name} 解析了 {len(posts)} 条微博")
            total_posts += len(posts)
        
        print(f"\n所有账号抓取完成，共解析 {total_posts} 条微博")
        
    else:
        print("请指定要执行的命令。使用 -h 查看帮助。")

if __name__ == '__main__':
    main()