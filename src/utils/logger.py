"""
日志管理模块

提供统一的日志配置和管理功能，支持：
1. 控制台输出
2. 文件输出
3. 不同级别的日志
4. 自定义格式
"""

import os
import logging
from datetime import datetime
from typing import Optional

from config.settings import LOG_DIR

class Logger:
    """日志管理类
    
    用于统一管理项目中的所有日志输出，支持同时输出到控制台和文件。
    """
    
    def __init__(self, name: str, log_dir: Optional[str] = None):
        """初始化日志管理器
        
        Args:
            name: 日志器名称
            log_dir: 日志文件存储目录，如果不指定则使用配置文件中的 LOG_DIR
        """
        self.name = name
        self.log_dir = log_dir or LOG_DIR
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
            
        # 设置日志格式
        self.formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 添加控制台处理器
        self._add_console_handler()
        
        # 添加文件处理器
        self._add_file_handler()
    
    def _add_console_handler(self):
        """添加控制台处理器"""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)
    
    def _add_file_handler(self):
        """添加文件处理器"""
        # 生成日志文件名
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(self.log_dir, f'{today}.log')
        
        # 创建文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)
    
    def debug(self, message: str):
        """输出 DEBUG 级别日志"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """输出 INFO 级别日志"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """输出 WARNING 级别日志"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """输出 ERROR 级别日志"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """输出 CRITICAL 级别日志"""
        self.logger.critical(message)

# 全局日志实例
_loggers: dict[str, Logger] = {}

def get_logger(name: str, log_dir: Optional[str] = None) -> Logger:
    """获取或创建一个日志实例
    
    Args:
        name: 日志器名称
        log_dir: 日志文件存储目录，如果不指定则使用配置文件中的 LOG_DIR
        
    Returns:
        Logger 实例
    """
    if name not in _loggers:
        _loggers[name] = Logger(name, log_dir)
    return _loggers[name]
