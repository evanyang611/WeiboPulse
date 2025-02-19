import re
import logging
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from src.database import Post, Image, Video
from src.database.config import get_db
from urllib.parse import urlparse, parse_qs, unquote

class RSSParser:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db = next(get_db())

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

    def _extract_media_files(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """提取媒体文件"""
        media_files = []
        
        # 1. 处理图片
        # 1.1 处理 img 标签
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
            
        # 1.2 处理"查看图片"链接
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
                    
                    # 生成图片ID
                    image_id = self._generate_image_id(image_url)
                    
                    media_files.append({
                        'type': 'image',
                        'element': link,
                        'image_id': image_id,
                        'original_url': image_url,
                        'thumbnail_url': image_url.replace('large', 'orj360')
                    })
        
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

    def _process_content(self, content: str) -> str:
        """处理微博内容，清理HTML标签，处理转发内容格式"""
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(content, 'html.parser')
        
        # 处理转发的内容
        repost_div = soup.find('div', style='border-left: 3px solid gray; padding-left: 1em;')
        if repost_div:
            # 获取转发内容的文本
            repost_text = repost_div.get_text(strip=True)
            # 移除原始的转发div
            repost_div.decompose()
            # 将转发内容添加到主内容后面
            content = str(soup) + ' // ' + repost_text
            # 重新解析处理后的内容
            soup = BeautifulSoup(content, 'html.parser')
        
        # 处理用户链接
        for user_link in soup.find_all('a', href=re.compile(r'/n/')):
            username = user_link.get_text()
            user_link.replace_with(f"@{username}")
        
        # 获取文本内容
        content = soup.get_text()
        
        # 清理用户名格式
        content = re.sub(r'@([^:：\s]+)[：:]\s*', r'@\1: ', content)
        
        # 清理最终的多余空格
        content = re.sub(r'\s+', ' ', content).strip()
        
        # 处理转发标记
        content = re.sub(r'(?<!\S)//@', r' //@', content)  # 确保 //@ 前有空格
        content = re.sub(r'(?<=[^/\s])@', r' //@', content)  # 将普通 @ 转换为 //@
        content = re.sub(r'(?<=[^/])/(?=[^/])', r'//', content)  # 确保是双斜杠
        content = re.sub(r'\s+//', r' //', content)  # 清理双斜杠前的多余空格
        content = re.sub(r'//\s+', r'// ', content)  # 清理双斜杠后的多余空格
        content = re.sub(r'\s+', ' ', content).strip()  # 最终清理多余空格
        
        return content

    def _process_content_with_media(self, content: str, media_files: List[Dict[str, Any]]) -> str:
        """处理内容，将媒体文件替换为标记"""
        soup = BeautifulSoup(content, 'html.parser')
        
        # 替换媒体文件为标记
        for media in media_files:
            if media['type'] == 'image':
                media['element'].replace_with(f"{{image:{media['image_id']}}}")
            elif media['type'] == 'video':
                media['element'].replace_with(f"{{video:{media['video_id']}}}")
        
        # 获取处理后的文本
        processed_content = soup.get_text()
        
        # 清理用户链接
        processed_content = re.sub(r'@([^:：\s]+)[：:]\s*', r'@\1: ', processed_content)
        
        # 处理转发标记
        processed_content = re.sub(r'(?<!\S)//@', r' //@', processed_content)  # 确保 //@ 前有空格
        processed_content = re.sub(r'(?<=[^/\s])@', r' //@', processed_content)  # 将普通 @ 转换为 //@
        processed_content = re.sub(r'(?<=[^/])/(?=[^/])', r'//', processed_content)  # 确保是双斜杠
        processed_content = re.sub(r'\s+//', r' //', processed_content)  # 清理双斜杠前的多余空格
        processed_content = re.sub(r'//\s+', r'// ', processed_content)  # 清理双斜杠后的多余空格
        
        # 清理多余空白字符
        processed_content = re.sub(r'\s+', ' ', processed_content)
        processed_content = processed_content.strip()
        
        return processed_content

    def parse_entry(self, entry: feedparser.FeedParserDict) -> Post:
        """解析单个 RSS 条目并保存到数据库"""
        try:
            # 1. 从 link 中提取微博 ID
            # 从 https://weibo.com/3232506545/PeV8K5tHr 提取 3232506545/PeV8K5tHr
            user_id, post_id = re.search(r'weibo\.com/(\d+)/(\w+)(?:\?|$)', entry.link).groups()
            weibo_id = f"{user_id}/{post_id}"
            
            # 2. 检查是否已经存在
            existing_post = self.db.query(Post).filter(
                Post.source == 'weibo',
                Post.source_id == weibo_id
            ).first()
            
            if existing_post:
                self.logger.info(f"微博 {weibo_id} 已存在，跳过")
                return existing_post
            
            # 3. 提取媒体文件
            media_files = self._extract_media_files(BeautifulSoup(entry.summary, 'html.parser'))
            
            # 4. 创建 Post 对象
            post = Post(
                source='weibo',
                source_id=weibo_id,  # 使用微博的短 ID
                title=entry.title,
                original_content=entry.summary,  # 使用 summary 而不是 content
                link=entry.link,
                published_at=datetime(*entry.published_parsed[:6])  # 使用 published_parsed
            )
            
            # 5. 保存 Post 以获取 ID
            self.db.add(post)
            self.db.flush()
            
            # 6. 保存媒体文件，使用集合去重
            saved_image_ids = set()
            saved_video_ids = set()
            
            for media in media_files:
                if media['type'] == 'image':
                    # 如果图片已经保存过，跳过
                    if media['image_id'] in saved_image_ids:
                        continue
                    saved_image_ids.add(media['image_id'])
                    
                    image = Image(
                        image_id=media['image_id'],
                        original_url=media['original_url'],
                        thumbnail_url=media['thumbnail_url'],
                        post_id=post.id
                    )
                    self.db.add(image)
                elif media['type'] == 'video':
                    # 如果视频已经保存过，跳过
                    if media['video_id'] in saved_video_ids:
                        continue
                    saved_video_ids.add(media['video_id'])
                    
                    video = Video(
                        video_id=media['video_id'],
                        video_url=media['video_url'],
                        post_id=post.id
                    )
                    self.db.add(video)
            
            # 7. 处理内容
            post.content = self._process_content_with_media(
                entry.summary,  # 使用 summary 而不是 content
                media_files
            )
            
            # 8. 提交事务
            self.db.commit()
            
            return post
            
        except Exception as e:
            self.db.rollback()
            self.logger.error(f"解析微博失败: {str(e)}")
            raise

    def get_user_posts(self, user_id: str) -> List[Post]:
        """获取用户的微博列表"""
        try:
            rss_url = f'http://yangqihang.space:8001/rss/user/{user_id}'
            self.logger.info(f"正在获取用户 {user_id} 的 RSS: {rss_url}")
            
            response = requests.get(rss_url)
            response.raise_for_status()
            self.logger.info(f"RSS 内容获取成功，状态码: {response.status_code}")
            self.logger.info(f"RSS 内容预览: {response.text[:500]}")
            
            feed = feedparser.parse(response.text)
            self.logger.info(f"RSS Feed 标题: {feed.feed.title}")
            
            entries = feed.entries
            self.logger.info(f"发现 {len(entries)} 条微博")
            
            posts = []
            for entry in entries:
                post = self.parse_entry(entry)
                posts.append(post)
            
            self.logger.info(f"成功解析 {len(posts)} 条微博")
            return posts
            
        except Exception as e:
            self.logger.error(f"获取用户微博失败: {str(e)}")
            raise

def test_parser():
    """测试解析器"""
    parser = RSSParser()
    user_id = "3232506545"
    posts = parser.get_user_posts(user_id)
    
    print(f"\n获取到 {len(posts)} 条微博:")
    for i, post in enumerate(posts[1:2], 2):
        print(f"\n第 {i} 条微博:")
        print(f"标题: {post.title}")
        print(f"内容: {post.content}")
        
        # 获取所有媒体文件
        images = [image for image in post.images]
        videos = [video for video in post.videos]
        
        # 输出图片信息
        if images:
            print(f"图片数量: {len(images)}")
            for j, img in enumerate(images, 1):
                print(f"  图片 {j}:")
                print(f"    原图: {img.original_url}")
                print(f"    缩略图: {img.thumbnail_url}")
                print(f"    ID: {img.image_id}")
        
        # 输出视频信息
        if videos:
            print(f"视频数量: {len(videos)}")
            for j, video in enumerate(videos, 1):
                print(f"  视频 {j}:")
                print(f"    链接: {video.video_url}")
                print(f"    ID: {video.video_id}")
            
        print(f"链接: {post.link}")
        print(f"发布时间: {post.published_at}")
        
        # 打印原始内容用于调试
        print("\n原始内容:")
        print(post.original_content)

if __name__ == '__main__':
    test_parser()
