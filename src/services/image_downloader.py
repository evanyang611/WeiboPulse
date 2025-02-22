import os
import aiohttp
import asyncio
from pathlib import Path
from typing import Dict, Any
import logging
import time

from config import settings

logger = logging.getLogger(__name__)

class ImageDownloader:
    """图片下载器"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """初始化下载器，创建必要的目录
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
        """
        # 确保目录存在
        os.makedirs(settings.ORIGINAL_IMAGES_DIR, exist_ok=True)
        os.makedirs(settings.THUMBNAIL_IMAGES_DIR, exist_ok=True)
        
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
    async def _download_with_retry(self, session: aiohttp.ClientSession, url: str, save_path: str) -> bool:
        """带重试机制的下载函数
        
        Args:
            session: aiohttp会话
            url: 下载URL
            save_path: 保存路径
            
        Returns:
            bool: 下载是否成功
        """
        for attempt in range(self.max_retries):
            try:
                async with session.get(url, timeout=settings.DOWNLOAD_TIMEOUT) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        with open(save_path, 'wb') as f:
                            f.write(content)
                        return True
                    else:
                        logger.warning(f"下载失败 (尝试 {attempt + 1}/{self.max_retries}): {url}, 状态码: {resp.status}")
            except Exception as e:
                logger.warning(f"下载出错 (尝试 {attempt + 1}/{self.max_retries}): {url}, 错误: {str(e)}")
            
            # 最后一次尝试失败，不需要等待
            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay)
                
        return False
            
    async def download_image(self, image_info: Dict[str, Any]) -> bool:
        """下载单张图片
        
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
            logger.info(f"图片已存在，跳过下载: {image_id}")
            return True
            
        try:
            async with aiohttp.ClientSession() as session:
                # 下载原图
                if not os.path.exists(original_path):
                    logger.info(f"开始下载原图: {image_id}")
                    if await self._download_with_retry(session, original_url, original_path):
                        logger.info(f"原图下载成功: {image_id}")
                    else:
                        logger.error(f"原图下载失败: {image_id}")
                        return False
                
                # 下载缩略图
                if not os.path.exists(thumbnail_path):
                    logger.info(f"开始下载缩略图: {image_id}")
                    if await self._download_with_retry(session, thumbnail_url, thumbnail_path):
                        logger.info(f"缩略图下载成功: {image_id}")
                    else:
                        logger.error(f"缩略图下载失败: {image_id}")
                        return False
                            
            return True
            
        except Exception as e:
            logger.error(f"下载图片出错: {image_id}, 错误: {str(e)}")
            return False
            
    async def download_images(self, media_files: list[Dict[str, Any]]) -> None:
        """批量下载图片
        
        Args:
            media_files: 媒体文件列表
        """
        # 过滤出图片文件
        image_files = [f for f in media_files if f['type'] == 'image']
        
        if not image_files:
            return
            
        # 创建下载任务
        tasks = [self.download_image(image) for image in image_files]
        
        # 并发下载
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        success = len([r for r in results if r is True])
        failed = len([r for r in results if r is False])
        errors = len([r for r in results if isinstance(r, Exception)])
        
        if failed or errors:
            logger.warning(f"图片下载完成: 成功 {success} 张, 失败 {failed} 张, 错误 {errors} 张")
        else:
            logger.info(f"图片下载完成: 成功 {success} 张")
