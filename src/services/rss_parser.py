import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import re
from bs4 import BeautifulSoup
import feedparser
from urllib.parse import urlparse, parse_qs, unquote, quote

from utils.logger import get_logger
from database.models import Post

class Post:
    """微博帖子数据类"""
    def __init__(self, 
                 title: str,
                 content: str,
                 original_content: str,
                 link: str,
                 published_at: datetime,
                 media_files: List[Dict[str, Any]] = None):
        self.title = title
        self.content = content
        self.original_content = original_content
        self.link = link
        self.published_at = published_at
        self.media_files = media_files or []

class RSSParser:
    """RSS解析器"""
    
    def __init__(self):
        """初始化RSS解析器"""
        self.logger = get_logger("rss_parser")
    
    def _extract_media_files(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """提取媒体文件信息
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            包含媒体文件信息的列表
        """
        media_files = []
        
        # 1. 处理图片
        # 1.1 处理"查看图片"链接
        for link in soup.find_all('a'):
            if not link.find('span', class_='surl-text'):
                continue
            
            text = link.get_text()
            if '查看图片' not in text:
                continue
                
            href = link.get('href', '')
            if not href:
                continue
                
            # 从链接中提取图片URL
            parsed = urlparse(href)
            if parsed.query:
                query_params = parse_qs(parsed.query)
                if 'u' in query_params:
                    image_url = unquote(query_params['u'][0])
                    
                    # 如果不是以 image.baidu.com 开头，加上前缀
                    if not image_url.startswith('https://image.baidu.com/search/down?url='):
                        image_url = f'https://image.baidu.com/search/down?url={quote(image_url)}'
                    
                    # 生成图片ID
                    image_id = self._generate_image_id(image_url)
                    
                    media_files.append({
                        'type': 'image',
                        'element': link,
                        'image_id': image_id,
                        'original_url': image_url,
                        'thumbnail_url': image_url.replace('large', 'orj360')
                    })
        
        # 1.2 处理 img 标签
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if not src:
                continue
                
            # 获取原图链接
            original_url = src
            if 'orj360' in src:
                original_url = src.replace('orj360', 'large')
            
            # 生成图片ID
            image_id = self._generate_image_id(original_url)
            
            media_files.append({
                'type': 'image',
                'element': img.parent if img.parent.name == 'a' else img,
                'image_id': image_id,
                'original_url': original_url,
                'thumbnail_url': src
            })
            
        # 1.3 处理其他可能的图片链接
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if 'sinaimg.cn' in href or 'wx' in href or 'image.baidu.com' in href:
                link.replace_with('{image}')
        
        # 2. 处理视频
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if not href or 'video.weibo.com' not in href:
                continue
                
            # 从链接中提取视频ID
            parsed = urlparse(href)
            if parsed.query:
                query_params = parse_qs(parsed.query)
                if 'fid' in query_params:
                    video_id = query_params['fid'][0]
                    media_files.append({
                        'type': 'video',
                        'element': link,
                        'video_id': video_id,
                        'video_url': href
                    })
        
        return media_files
    
    def _generate_image_id(self, url: str) -> str:
        """从URL中提取图片ID"""
        # 处理百度图片链接
        if 'image.baidu.com/search/down' in url:
            parsed = urlparse(url)
            if parsed.query:
                query_params = parse_qs(parsed.query)
                if 'url' in query_params:
                    url = unquote(query_params['url'][0])
        
        # 处理新浪微博链接
        if 'sinaimg.cn' in url:
            # 提取文件名部分
            filename = url.split('/')[-1]
            # 如果是完整的URL，保留文件名部分
            if '.' in filename:
                return f"weibo_image_{filename}"
        
        # 如果都不匹配，使用URL的最后一部分作为ID
        return f"weibo_image_{url.split('/')[-1]}"
    
    def _process_content(self, content: str) -> str:
        """处理微博内容，清理HTML标签，保留社交媒体元素
        
        保留的元素：
        - @用户名
        - #话题#
        - 转发标记 //
        
        Args:
            content: 原始HTML内容
            
        Returns:
            处理后的纯文本内容
        """
        # 创建BeautifulSoup对象
        soup = BeautifulSoup(content, 'html.parser')
        
        # 1. 处理图片
        # 1.1 处理"查看图片"链接
        for link in soup.find_all('a'):
            if not link.find('span', class_='surl-text'):
                continue
            
            text = link.get_text()
            if '查看图片' not in text:
                continue
                
            link.replace_with('{image}')
            
        # 1.2 处理 img 标签
        for img in soup.find_all('img'):
            # 找到最外层的 a 标签（如果存在）
            parent_a = img.find_parent('a')
            if parent_a:
                parent_a.replace_with('{image}')
            else:
                img.replace_with('{image}')
            
        # 1.3 处理其他可能的图片链接
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if 'sinaimg.cn' in href or 'wx' in href or 'image.baidu.com' in href:
                link.replace_with('{image}')
        
        # 2. 处理视频
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if not href or 'video.weibo.com' not in href:
                continue
                
            link.replace_with('{video}')
            
        # 3. 处理换行标签
        for br in soup.find_all('br'):
            br.replace_with('\n')

        # 4. 处理话题链接和超话链接
        for link in soup.find_all('a'):
            span = link.find('span', class_='surl-text')
            if not span:
                continue
                
            text = span.get_text()
            # 处理带#号的话题
            if text.startswith('#') and text.endswith('#'):
                # 保留话题文本
                link.replace_with(text)
            # 处理超话链接（通过链接判断）
            elif 'containerid=1008' in link.get('href', ''):
                # 将超话文本用【】包裹
                link.replace_with(f'【{text}超话】')
        
            
        # 5. 处理转发微博的div
        for div in soup.find_all('div', style=lambda x: x and 'border-left' in x):
            # 获取div的内容
            content = div.get_text(strip=True)
            # 如果内容以"转发"开头，移除这个词
            if content.startswith('转发'):
                content = content[2:].strip()
            # 如果内容以@开头，添加 //
            if content.startswith('@'):
                content = '//' + content
            # 替换div，不添加前导空格
            div.replace_with(content)
            
        # 6. 处理@用户名链接
        for link in soup.find_all('a'):
            href = link.get('href', '')
            text = link.get_text()
            # 如果是@用户名的链接
            if text.startswith('@') or (href and ('weibo.com' in href or 'yangqihang.space' in href)):
                link.replace_with(text)
        
        # 7. 移除多余的换行和空格
        text = str(soup)
        # 将连续的换行替换为单个换行
        text = re.sub(r'\n\s*\n', '\n', text)
        # 在图片和视频标记之间添加空格
        text = re.sub(r'}(\s*){', '} {', text)
        # 在文字和图片/视频标记之间添加空格
        text = re.sub(r'([^\s}]){(image|video)}', r'\1 {\2}', text)
        text = re.sub(r'}{(image|video)}([^\s{])', r'} {\1} \2', text)
        # 将连续的空格替换为单个空格
        text = re.sub(r' +', ' ', text)
        # 清理开头和结尾的空白字符
        text = text.strip()
        
        return text
    
    def parse_entry(self, entry: feedparser.FeedParserDict) -> Post:
        """解析单个RSS条目
        
        Args:
            entry: RSS条目
            
        Returns:
            Post对象
        """
        # 解析发布时间
        try:
            published_at = datetime.strptime(entry.published, '%a, %d %b %Y %H:%M:%S %z')
        except ValueError:
            # 如果带有GMT时区标识，需要特殊处理
            if 'GMT' in entry.published:
                published_str = entry.published.replace('GMT', '+0000')
                published_at = datetime.strptime(published_str, '%a, %d %b %Y %H:%M:%S %z')
            else:
                raise
        
        # 创建BeautifulSoup对象解析内容
        soup = BeautifulSoup(entry.description, 'html.parser')
        
        # 提取媒体文件
        media_files = self._extract_media_files(soup)
        
        # 处理内容
        processed_content = self._process_content(entry.description)
        
        # 创建Post对象
        post = Post(
            title=entry.title,
            content=processed_content,  # 使用处理后的内容
            original_content=entry.description,
            link=entry.link,
            published_at=published_at,
            media_files=media_files
        )
        
        return post
    
    def parse_feed(self, feed_url: str) -> List[Post]:
        """解析RSS源
        
        Args:
            feed_url: RSS源URL
            
        Returns:
            Post对象列表
        """
        import feedparser
        
        self.logger.info(f"开始解析RSS源: {feed_url}")
        
        # 解析RSS源
        feed = feedparser.parse(feed_url)
        
        # 检查是否成功获取到条目
        if not feed.entries:
            self.logger.warning(f"未从RSS源获取到任何条目: {feed_url}")
            return []
        
        self.logger.info(f"获取到 {len(feed.entries)} 条微博")
        
        # 解析每个条目
        posts = []
        for entry in feed.entries:
            try:
                post = self.parse_entry(entry)
                posts.append(post)
                
                # 记录每条微博的详细信息
                self.logger.info(f"第 {len(posts)} 条微博:")
                self.logger.info(f"链接: {post.link}")
                self.logger.info(f"标题: {post.title}")
                self.logger.info(f"内容: {post.content}")
                if post.media_files:
                    self.logger.info(f"图片数量: {len(post.media_files)}")
                    for i, media in enumerate(post.media_files, 1):
                        if media['type'] == 'image':
                            self.logger.info(f"  图片 {i}:")
                            self.logger.info(f"    原图: {media['original_url']}")
                            self.logger.info(f"    缩略图: {media['thumbnail_url']}")
                            self.logger.info(f"    ID: {media['image_id']}")
                        else:
                            self.logger.info(f"  视频 {i}:")
                            self.logger.info(f"    ID: {media['video_id']}")
                            self.logger.info(f"    链接: {media['video_url']}")
                self.logger.info(f"发布时间: {post.published_at}")
                self.logger.info("")
                
            except Exception as e:
                self.logger.error(f"解析条目时出错: {str(e)}")
                continue
        
        return posts

if __name__ == "__main__":
    # 创建RSS解析器
    parser = RSSParser()
    
    # 解析RSS源
    posts = parser.parse_feed("http://yangqihang.space:8001/rss/user/3232506545")
    
    # # 打印微博信息
    # for post in posts:
    #     print(f"第 {posts.index(post) + 1} 条微博:")
    #     print(f"链接: {post.link}")
    #     print(f"标题: {post.title}")
    #     print(f"内容: {post.content}")
    #     if post.media_files:
    #         print(f"图片数量: {len(post.media_files)}")
    #         for i, media in enumerate(post.media_files, 1):
    #             if media['type'] == 'image':
    #                 print(f"  图片 {i}:")
    #                 print(f"    原图: {media['original_url']}")
    #                 print(f"    缩略图: {media['thumbnail_url']}")
    #                 print(f"    ID: {media['image_id']}")
    #             else:
    #                 print(f"  视频 {i}:")
    #                 print(f"    ID: {media['video_id']}")
    #                 print(f"    链接: {media['video_url']}")
    #     print(f"发布时间: {post.published_at}")
    #     print()
