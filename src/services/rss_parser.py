import logging
import re
from typing import Dict, List, Optional
from datetime import datetime
import feedparser
import requests
from bs4 import BeautifulSoup as bs

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RSSParser:
    """微博 RSS 解析器"""

    def __init__(self):
        """初始化解析器"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def _extract_media_files(self, content: str) -> List[Dict]:
        """从内容中提取媒体文件信息"""
        media_files = []
        soup = bs(content, 'html.parser')
        
        # 处理所有链接
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # 处理跳转链接
            if 'sinaurl?u=' in href:
                href = re.search(r'u=(.*?)(?:&|$)', href).group(1)
                href = requests.utils.unquote(href)
            
            # 处理视频链接
            if 'video.weibo.com/show?fid=' in href:
                video_id = re.search(r'fid=(\d+:\d+)', href).group(1)
                media_files.append({
                    'type': 'video',
                    'url': f'https://weibo.com/tv/show/{video_id}',
                    'video_id': video_id
                })
                continue
            
            # 处理图片链接
            if 'image.baidu.com/search/down?' in href:
                media_files.append({
                    'type': 'image',
                    'original_url': href,
                    'thumbnail_url': href.replace('large', 'orj360')
                })
            elif re.search(r'https?://wx\d+\.sinaimg\.cn/large/', href):
                thumbnail_url = href.replace('large', 'orj360')
                media_files.append({
                    'type': 'image',
                    'original_url': f'https://image.baidu.com/search/down?url={requests.utils.quote(href)}',
                    'thumbnail_url': f'https://image.baidu.com/search/down?url={requests.utils.quote(thumbnail_url)}'
                })

        return media_files

    def _process_content(self, entry) -> str:
        """处理微博内容，提取正文、转发内容等"""
        content = entry['summary']
        
        # 处理文本内容
        soup = bs(content, 'html.parser')
        
        # 处理@用户标签
        for user_link in soup.find_all('a', href=re.compile(r'^/n/')):
            user_link.replace_with(f'@{user_link.text}')
        
        # 处理转发的@用户标签
        for user_link in soup.find_all('a', href=re.compile(r'^https://weibo.com/\d+')):
            if user_link.text.startswith('@'):
                user_link.replace_with(user_link.text)
        
        # 替换<br>标签为换行符
        for br in soup.find_all('br'):
            br.replace_with('\n')
        
        # 获取文本内容
        text = soup.get_text()
        
        # 处理转发内容格式
        text = re.sub(r'转发\s*@([^:：]+)[:：]', r'//@\1：', text)
        
        # 清理多余的空白字符，但保留单个换行
        text = re.sub(r'\n\s*\n', '\n\n', text)  # 将多个连续空行减少为两个
        text = re.sub(r' +', ' ', text)  # 清理多余空格
        text = text.strip()
        
        # 修复可能的多余@符号
        text = text.replace('//@', ' //@')  # 确保转发标记前有空格
        text = re.sub(r'//\s*@+', '//@', text)  # 修复多余的@
        
        return text

    def _extract_post_id(self, url: str) -> Optional[str]:
        """从链接中提取微博ID"""
        match = re.search(r'/(\d+)/(\w+)$', url)
        return match.group(2) if match else None

    def parse_entry(self, entry: Dict) -> Optional[Dict]:
        """解析单条微博"""
        try:
            # 处理内容
            content_data = self._process_content(entry)
            
            # 提取媒体文件
            media_files = self._extract_media_files(entry['summary'])
            
            # 提取基本信息
            result = {
                'title': entry.get('title', 'No title'),
                'content': content_data,
                'media_files': media_files,
                'link': entry['link'],
                'published': datetime.strptime(entry['published'], '%a, %d %b %Y %H:%M:%S %Z').strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 返回解析结果
            return result
        except Exception as e:
            logger.error(f"解析条目失败: {str(e)}")
            return None

    def get_user_posts(self, user_id: str) -> List[Dict]:
        """从用户ID获取并解析所有微博内容"""
        rss_url = f"http://yangqihang.space:8001/rss/user/{user_id}"
        try:
            logger.info(f"正在获取用户 {user_id} 的 RSS: {rss_url}")
            
            # 获取 RSS 内容
            response = requests.get(rss_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            logger.info(f"RSS 内容获取成功，状态码: {response.status_code}")
            logger.info(f"RSS 内容预览: {response.text[:500]}")  # 显示前500个字符
            
            # 解析 RSS Feed
            feed = feedparser.parse(response.text)
            
            if hasattr(feed, 'bozo_exception'):
                logger.error(f"RSS 解析错误: {feed.bozo_exception}")
                return []
            
            logger.info(f"RSS Feed 标题: {feed.feed.get('title', 'Unknown')}")
            logger.info(f"发现 {len(feed.entries)} 条微博")
            
            # 解析每个条目
            posts = []
            for entry in feed.entries:
                post = self.parse_entry(entry)
                if post:
                    posts.append(post)
            
            logger.info(f"成功解析 {len(posts)} 条微博")
            return posts
            
        except requests.exceptions.RequestException as e:
            logger.error(f"RSS 请求失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"获取用户微博失败: {str(e)}")
            return []

def test_parser():
    """测试解析器"""
    parser = RSSParser()
    user_id = "3232506545"
    posts = parser.get_user_posts(user_id)
    
    print(f"\n获取到 {len(posts)} 条微博:")
    for i, post in enumerate(posts, 1):
        print(f"\n第 {i} 条微博:")
        print(f"标题: {post.get('title', '')}")
        print(f"内容: {post.get('content', '')}")
        
        # 获取所有媒体文件
        media_files = post.get('media_files', [])
        images = [m for m in media_files if m['type'] == 'image']
        videos = [m for m in media_files if m['type'] == 'video']
        
        # 输出图片信息
        if images:
            print(f"图片数量: {len(images)}")
            for j, img in enumerate(images, 1):
                print(f"  图片 {j}:")
                print(f"    原图: {img['original_url']}")
                print(f"    缩略图: {img['thumbnail_url']}")
        
        # 输出视频信息
        if videos:
            print(f"视频数量: {len(videos)}")
            for j, video in enumerate(videos, 1):
                print(f"  视频 {j}:")
                print(f"    链接: {video['url']}")
                print(f"    ID: {video['video_id']}")
            
        print(f"链接: {post.get('link', '')}")
        print(f"发布时间: {post.get('published', '')}")

if __name__ == '__main__':
    test_parser()
