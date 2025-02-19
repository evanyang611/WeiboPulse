#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WeiboScraper 主入口文件
"""

import sys
from pathlib import Path

# 将src目录添加到Python路径
src_dir = str(Path(__file__))
if src_dir not in sys.path:
    sys.path.append(src_dir)

import argparse
from services.rss_parser import RSSParser

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='WeiboScraper - 微博 RSS 解析工具')
    parser.add_argument('--url', type=str, default='http://yangqihang.space:8001/rss/user/5130681470', help='RSS源URL，例如：http://example.com/rss/user/123456')
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    # 创建RSS解析器
    parser = RSSParser()
    
    # 解析RSS源
    posts = parser.parse_feed(args.url)
    
    # 处理结果
    print(f"共解析 {len(posts)} 条微博")

if __name__ == '__main__':
    main()