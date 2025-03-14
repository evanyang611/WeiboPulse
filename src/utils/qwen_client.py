import os
from openai import OpenAI
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional, Callable
import time
import functools
from openai.types.chat import ChatCompletion
from pathlib import Path
import sys

# 确保src目录在sys.path中
src_path = str(Path(__file__).resolve().parent.parent)
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 使用绝对导入
from utils.logger import get_logger

# 加载.env文件（如果存在）
env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# 获取日志记录器
logger = get_logger("qwen_client")

def retry(max_retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0):
    """重试装饰器
    
    Args:
        max_retries: 最大重试次数
        initial_delay: 初始延迟时间（秒）
        backoff_factor: 退避因子，每次重试延迟时间会乘以这个因子
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for retry_count in range(max_retries + 1):
                try:
                    if retry_count > 0:
                        logger.warning(f"第 {retry_count} 次重试 {func.__name__}...")
                    
                    result = func(*args, **kwargs)
                    
                    # 检查结果是否有效
                    if result is not None:
                        return result
                    
                    raise ValueError("API返回结果为空")
                    
                except Exception as e:
                    last_exception = e
                    logger.error(f"调用 {func.__name__} 失败: {str(e)}")
                    
                    if retry_count < max_retries:
                        logger.info(f"等待 {delay:.2f} 秒后重试...")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"已达到最大重试次数 {max_retries}，放弃重试")
            
            # 所有重试都失败，抛出最后一个异常
            raise last_exception
        
        return wrapper
    
    return decorator

class QwenClient:
    """通义千问大模型客户端
    
    封装了对阿里云通义千问大模型的调用方法
    """
    
    def __init__(self, api_key: Optional[str] = None, max_retries: int = 3):
        """初始化通义千问客户端
        
        Args:
            api_key: API密钥，如果为None则从环境变量ALIYUN_API_KEY中获取
            model: 使用的模型名称，默认为qwen-max-latest
            max_retries: 最大重试次数
        """
        self.api_key = api_key or os.getenv("ALIYUN_API_KEY")
        if not self.api_key:
            raise ValueError("API密钥未提供，请设置ALIYUN_API_KEY环境变量或在初始化时提供api_key参数")
            
        self.max_retries = max_retries
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        
        # 获取日志记录器
        self.logger = get_logger("qwen_client")
    
    @retry(max_retries=3)
    def chat(self, message: str, image_url_list: Optional[List[str]] = None, temperature: float = 0.0, stream: bool = True, **kwargs) -> Any:
        """发送聊天请求并获取回复
        
        Args:
            message: 消息内容
            image_url_list: 图片URL列表，如果有图片则使用多模态模型
            temperature: 温度参数，控制输出的随机性，默认为0.0
            stream: 是否使用流式输出，默认为False
            **kwargs: 其他参数，将直接传递给OpenAI API
            
        Returns:
            如果stream=False，返回完整的回复内容字符串
            如果stream=True，返回一个生成器，可以逐步获取回复内容
            
        Raises:
            Exception: 如果API调用失败或返回结果无效
        """
        try:
            # 记录请求信息
            self.logger.debug(f"发送请求，消息长度: {len(message)}, 图片数量: {len(image_url_list) if image_url_list else 0}")

            if image_url_list:
                # 如果有图片
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": message},
                        ]
                    }
                ]
                for img_url in image_url_list:
                    messages[0]['content'].append({"type": "image_url", "image_url": {"url": img_url}})

                model_name = os.getenv('MULTIMODAL_MODEL')
            else:
                # 纯文本
                messages = [
                    {
                        "role": "user",
                        "content": message
                    }
                ]
                model_name = os.getenv('TEXT_MODEL', "qwen-max-latest")

            self.logger.info(f"调用模型: {model_name}, 流式输出: {stream}")

            # 调用API
            completion = self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                stream=stream,
                **kwargs
            )

            # 处理流式输出
            if stream:
                def response_generator():
                    full_response = ""
                    for chunk in completion:
                        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                            content_chunk = chunk.choices[0].delta.content
                            full_response += content_chunk
                            # yield {
                            #     "content": content_chunk,
                            #     "full_response": full_response,
                            #     "finished": False
                            # }
                    
                    # 返回完整的最终响应
                    # yield {
                    #     "content": "",
                    #     "full_response": full_response,
                    #     "finished": True
                    # }

                    return full_response
                
                return response_generator()
            
            # 处理非流式输出
            else:
                # 验证返回结果
                self._validate_completion(completion)
                
                # 提取回复内容
                content = completion.choices[0].message.content
                
                # 对内容进行后处理
                content = self._post_process_response(content)
                
                # 检查内容是否为空
                if not content or not content.strip():
                    raise ValueError("模型返回的内容为空")
                    
                self.logger.debug(f"成功获取回复，内容长度: {len(content)}")
                return content
                
        except Exception as e:
            self.logger.error(f"调用模型API失败: {str(e)}")
            raise
    
    def _validate_completion(self, completion: ChatCompletion) -> None:
        """验证API返回的结果是否有效
        
        Args:
            completion: API返回的结果对象
            
        Raises:
            ValueError: 如果结果无效
        """
        if not completion:
            raise ValueError("API返回结果为空")
            
        if not hasattr(completion, 'choices') or not completion.choices:
            raise ValueError("API返回结果中没有choices字段")
            
        if not hasattr(completion.choices[0], 'message'):
            raise ValueError("API返回结果中没有message字段")
            
        if not hasattr(completion.choices[0].message, 'content'):
            raise ValueError("API返回结果中没有content字段")

    def _post_process_response(self, response: str) -> str:
        """对模型返回的内容进行后处理
        
        Args:
            response: 模型返回的内容
        """
        if response.startswith('```json'):
            response = response.strip('```json').strip('```')

        if response.startswith('```markdown'):
            response = response.strip('```markdown').strip('```')

        return response
 


# 示例用法
if __name__ == "__main__":
    # 创建客户端实例
    qwen = QwenClient()
    
    # 简单对话示例
    try:
        # 非流式输出示例
        # print("\n=== 非流式输出示例 ===")
        # response = qwen.chat("你好，请介绍一下自己", stream=True)
        # print(response)
        
        # 流式输出示例
        # print("\n=== 流式输出示例 ===")
        # for chunk in qwen.chat("请写一首关于春天的诗", stream=True):
        #     print(chunk, end="", flush=True)
            # if not chunk["finished"]:
            #     print(chunk["content"], end="", flush=True)
            # else:
            #     print("\n--- 生成完成 ---")
        
        # 多模态示例
        print("\n=== 多模态示例 ===")

        message = '介绍一下以下图片中讲述了一个什么故事'
        image_url_list = ['https://image.baidu.com/search/down?url=https%3A%2F%2Fwx4.sinaimg.cn%2Flarge%2Fe17e66f5gy1hzaia1p8lsj20l80tztnb.jpg', 'https://image.baidu.com/search/down?url=https%3A%2F%2Fwx2.sinaimg.cn%2Flarge%2Fe17e66f5gy1hzaia28uxyj20l80tz7h3.jpg', 'https://image.baidu.com/search/down?url=https%3A%2F%2Fwx2.sinaimg.cn%2Flarge%2Fe17e66f5gy1hzaia2nuzdj20l80tzgvi.jpg', 'https://image.baidu.com/search/down?url=https%3A%2F%2Fwx4.sinaimg.cn%2Flarge%2Fe17e66f5gy1hzaia33oaij20l80tzn8d.jpg', 'https://image.baidu.com/search/down?url=https%3A%2F%2Fwx1.sinaimg.cn%2Flarge%2Fe17e66f5gy1hzaia3k3ysj20l80tzwn2.jpg', 'https://image.baidu.com/search/down?url=https%3A%2F%2Fwx2.sinaimg.cn%2Flarge%2Fe17e66f5gy1hzaia42clrj20l80tzdra.jpg', 'https://image.baidu.com/search/down?url=https%3A%2F%2Fwx2.sinaimg.cn%2Flarge%2Fe17e66f5gy1hzaia13z77j20l80tzqeg.jpg', 'https://image.baidu.com/search/down?url=https%3A%2F%2Fwx1.sinaimg.cn%2Flarge%2Fe17e66f5gy1hzaia4rfkrj20l80tzk38.jpg', 'https://image.baidu.com/search/down?url=https%3A%2F%2Fwx4.sinaimg.cn%2Flarge%2Fe17e66f5gy1hzaia56r2yj20l80tzqbt.jpg']
        # response = qwen.chat(message, image_url_list=image_url_list, stream=True)
        response = qwen.chat('你好')
        print(response)

        
    except Exception as e:
        print(f"调用失败: {str(e)}")