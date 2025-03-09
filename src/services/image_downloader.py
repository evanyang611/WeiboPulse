import os
import aiohttp
import asyncio
from pathlib import Path
from typing import Dict, Any, List
import logging
import time
from urllib.parse import urlparse, unquote, quote

from config import settings
from utils.logger import get_logger

class ImageDownloader:
    """图片下载器"""
    
    def __init__(self, max_retries: int = 5, retry_delay: float = 2.0, max_concurrent: int = 5):
        """初始化下载器，创建必要的目录
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
            max_concurrent: 最大并发下载数
        """
        # 确保目录存在
        os.makedirs(settings.ORIGINAL_IMAGES_DIR, exist_ok=True)
        os.makedirs(settings.THUMBNAIL_IMAGES_DIR, exist_ok=True)
        
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = get_logger("image_downloader")
        
    async def _download_with_retry(self, session: aiohttp.ClientSession, url: str, save_path: str) -> bool:
        """带重试机制的下载函数
        
        Args:
            session: aiohttp会话
            url: 下载URL
            save_path: 保存路径
            
        Returns:
            bool: 下载是否成功
        """
        # 处理URL中的特殊字符
        url = self._clean_url(url)
        
        for attempt in range(self.max_retries):
            try:
                # 使用更长的超时时间
                timeout = aiohttp.ClientTimeout(total=60)  # 60秒超时
                async with session.get(url, timeout=timeout) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        # 确保目录存在
                        os.makedirs(os.path.dirname(save_path), exist_ok=True)
                        with open(save_path, 'wb') as f:
                            f.write(content)
                        return True
                    else:
                        self.logger.warning(f"下载失败 (尝试 {attempt + 1}/{self.max_retries}): {url}, 状态码: {resp.status}")
            except asyncio.TimeoutError:
                self.logger.warning(f"下载超时 (尝试 {attempt + 1}/{self.max_retries}): {url}")
            except aiohttp.ClientError as e:
                self.logger.warning(f"客户端错误 (尝试 {attempt + 1}/{self.max_retries}): {url}, 错误: {str(e)}")
            except Exception as e:
                self.logger.warning(f"下载出错 (尝试 {attempt + 1}/{self.max_retries}): {url}, 错误: {str(e)}")
            
            # 最后一次尝试失败，不需要等待
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay)
                
        return False
    
    def _clean_url(self, url: str) -> str:
        """清理URL，处理特殊字符和编码问题
        
        Args:
            url: 原始URL
            
        Returns:
            str: 处理后的URL
        """
        # 处理百度图片链接
        if 'image.baidu.com/search/down' in url:
            parsed = urlparse(url)
            if parsed.query:
                # 从查询参数中提取实际URL
                from urllib.parse import parse_qs
                query_params = parse_qs(parsed.query)
                if 'url' in query_params:
                    actual_url = unquote(query_params['url'][0])
                    return actual_url
        
        # 处理URL中的空格和其他特殊字符
        return url.replace(' ', '%20')
    
    async def _download_with_semaphore(self, image_info: Dict[str, Any]) -> bool:
        """使用信号量限制并发的下载方法
        
        Args:
            image_info: 图片信息字典
            
        Returns:
            bool: 下载是否成功
        """
        async with self.semaphore:
            return await self.download_image_internal(image_info)
            
    async def download_image(self, image_info: Dict[str, Any]) -> bool:
        """下载单张图片（外部接口）
        
        Args:
            image_info: 图片信息字典，包含 image_id, original_url, thumbnail_url
            
        Returns:
            bool: 下载是否成功
        """
        # 使用信号量限制并发
        return await self._download_with_semaphore(image_info)
            
    async def download_image_internal(self, image_info: Dict[str, Any]) -> bool:
        """下载单张图片的内部实现
        
        Args:
            image_info: 图片信息字典，包含 image_id, original_url, thumbnail_url
            
        Returns:
            bool: 下载是否成功
        """
        image_id = image_info['image_id']
        original_url = image_info['original_url']
        thumbnail_url = image_info['thumbnail_url']
        
        # 构建文件路径
        original_path = os.path.join(settings.ORIGINAL_IMAGES_DIR, image_id)
        thumbnail_path = os.path.join(settings.THUMBNAIL_IMAGES_DIR, image_id)
        
        # 如果文件已存在，跳过下载
        if os.path.exists(original_path) and os.path.exists(thumbnail_path):
            self.logger.info(f"图片已存在，跳过下载: {image_id}")
            return True
            
        try:
            # 使用自定义的超时设置
            timeout = aiohttp.ClientTimeout(total=60)
            connector = aiohttp.TCPConnector(ssl=False)  # 禁用SSL验证，解决某些HTTPS问题
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                # 下载原图
                if not os.path.exists(original_path):
                    self.logger.info(f"开始下载原图: {image_id}")
                    if await self._download_with_retry(session, original_url, original_path):
                        self.logger.info(f"原图下载成功: {image_id}")
                    else:
                        self.logger.error(f"原图下载失败: {image_id}")
                        return False
                
                # 下载缩略图
                if not os.path.exists(thumbnail_path):
                    self.logger.info(f"开始下载缩略图: {image_id}")
                    if await self._download_with_retry(session, thumbnail_url, thumbnail_path):
                        self.logger.info(f"缩略图下载成功: {image_id}")
                    else:
                        self.logger.error(f"缩略图下载失败: {image_id}")
                        return False
                            
            return True
            
        except Exception as e:
            self.logger.error(f"下载图片出错: {image_id}, 错误: {str(e)}")
            return False
            
    async def download_images(self, media_files: List[Dict[str, Any]]) -> None:
        """批量下载图片
        
        Args:
            media_files: 媒体文件列表
        """
        # 过滤出图片文件
        image_files = [f for f in media_files if f['type'] == 'image']
        
        if not image_files:
            return
            
        self.logger.info(f"开始下载图片，共 {len(image_files)} 张，最大并发数: {self.max_concurrent}")
            
        # 创建下载任务
        tasks = [self._download_with_semaphore(image) for image in image_files]
        
        # 并发下载
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        success = len([r for r in results if r is True])
        failed = len([r for r in results if r is False])
        errors = len([r for r in results if isinstance(r, Exception)])
        
        if failed or errors:
            self.logger.warning(f"图片下载完成: 成功 {success} 张, 失败 {failed} 张, 错误 {errors} 张")
        else:
            self.logger.info(f"图片下载完成: 成功 {success} 张")
