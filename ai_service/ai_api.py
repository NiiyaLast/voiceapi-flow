import requests
import json
from typing import Optional
import os
import time
# 添加配置管理导入
from config_manager import get_config
# 添加OpenAI SDK支持
from openai import OpenAI


# 导入AI日志模块
try:
    from .ai_logger import log_ai_process
except ImportError:
    # 如果导入失败，定义一个空的日志函数
    def log_ai_process(*args, **kwargs):
        pass

class CarTestDataProcessor:
    """汽车测试数据处理器 - 支持多种AI模型提供商"""
    
    def __init__(self, model_name: str = None, base_url: str = None, provider: str = None):
        # 获取配置，如果失败则抛出异常
        try:
            config = get_config()
        except Exception as e:
            raise RuntimeError(f"无法加载配置文件，项目必须依赖配置文件才能运行: {e}")
        
        # 检查必要的配置项
        if not hasattr(config, 'ai'):
            raise RuntimeError("配置文件中缺少ai配置段")
        
        # 从配置文件读取参数
        self.provider = provider or config.ai.provider.lower()
        self.model_name = model_name or config.ai.model_name
        self.timeout = config.ai.timeout
        self.max_retries = config.ai.max_retries
        
        # 读取AI推理参数
        if not hasattr(config.ai, 'options'):
            raise RuntimeError("配置文件中缺少ai.options配置，请在config.yaml中添加AI推理参数")
        
        self.ai_options = config.ai.options
        
        # 读取端点配置 - 消除硬编码
        if not hasattr(config.ai, 'endpoints') or not config.ai.endpoints:
            raise RuntimeError("配置文件中缺少ai.endpoints配置，请添加各提供商的端点配置")
        
        self.endpoints_config = config.ai.endpoints
        
        # 验证关键配置项
        if not self.model_name:
            raise RuntimeError("配置文件中缺少model_name")
        if self.provider not in self.endpoints_config:
            raise RuntimeError(f"配置文件中缺少{self.provider}的端点配置")
        
        # 从端点配置中获取API密钥
        provider_config = self.endpoints_config[self.provider]
        self.api_key = provider_config.get('api_key')
        
        # 验证API密钥（仅对需要的提供商）
        if self.provider in ['openai', 'deepseek'] and not self.api_key:
            raise RuntimeError(f"使用{self.provider}时必须在endpoints.{self.provider}.api_key中配置API密钥")
            
        # 初始化OpenAI客户端（用于DeepSeek和OpenAI）
        self.openai_client = None
        if self.provider in ['openai', 'deepseek']:
            if OpenAI is None:
                raise RuntimeError("使用OpenAI或DeepSeek时需要安装openai库: pip install openai")
            
            # 从配置文件读取base_url - 消除硬编码
            provider_config = self.endpoints_config[self.provider]
            api_base = provider_config['base_url']
            
            # 对于OpenAI SDK，确保base_url格式正确（都需要/v1结尾）
            if not api_base.endswith('/v1'):
                api_base = api_base.rstrip('/') + '/v1'
            
            self.openai_client = OpenAI(
                api_key=self.api_key,
                base_url=api_base
            )
            print(f"初始化OpenAI客户端: {self.provider}, base_url: {api_base}")
            
        # 根据提供商设置API端点
        self._setup_api_endpoint()
        
        # 预定义的系统提示词
        self.system_prompt = self._load_system_prompt("system_prompt.txt")

    def _setup_api_endpoint(self):
        """根据提供商设置API端点 """
        provider_config = self.endpoints_config[self.provider]
        base_url = provider_config['base_url']
        chat_endpoint = provider_config['chat_endpoint']
        
        # 构建完整的API URL
        self.api_url = base_url.rstrip('/') + chat_endpoint
        
        # print(f"使用AI提供商: {self.provider}, 模型: {self.model_name}, API端点: {self.api_url}")


    def _load_system_prompt(self, prompt_file: str) -> str:
        """
        从文件读取系统提示词，如果文件不存在则抛出异常
        
        Args:
            prompt_file (str): 提示词文件名
            
        Returns:
            str: 提示词内容
            
        Raises:
            RuntimeError: 如果提示词文件不存在或读取失败
        """
        try:
            # 获取当前文件所在目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_path = os.path.join(current_dir, prompt_file)
            
            # 检查文件是否存在
            if not os.path.exists(prompt_path):
                raise RuntimeError(f"系统提示词文件不存在: {prompt_path}")
            
            # 读取提示词文件
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 检查内容是否为空
            if not content:
                raise RuntimeError(f"系统提示词文件为空: {prompt_path}")
            
            return content
            
        except FileNotFoundError:
            raise RuntimeError(f"系统提示词文件不存在: {prompt_file}")
        except Exception as e:
            raise RuntimeError(f"读取系统提示词文件时出错: {e}")

    def _chat_with_ai(self, prompt: str, stream: bool = False) -> Optional[str]:
        """
        内部方法：调用AI API（支持多种提供商）
        """
        if self.provider == 'ollama':
            return self._chat_with_ollama(prompt, stream)
        elif self.provider in ['openai', 'deepseek']:
            return self._chat_with_openai_sdk(prompt, stream)
        else:
            # 保持兼容性，使用原有的外部API调用方式
            return self._chat_with_external_api(prompt, stream)
    
    def _chat_with_ollama(self, prompt: str, stream: bool = False) -> Optional[str]:
        """
        调用 Ollama API
        """
        data = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "stream": stream,
            "options": self.ai_options,
        }
        
        return self._make_request(data, stream, is_ollama=True)
    
    def _chat_with_openai_sdk(self, prompt: str, stream: bool = False) -> Optional[str]:
        """
        使用 OpenAI SDK 调用 OpenAI 或 DeepSeek API
        """
        if not self.openai_client:
            raise RuntimeError("OpenAI客户端未初始化")
        
        try:
            # 构建消息
            messages = [
                {
                    "role": "system",
                    "content": self.system_prompt
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # 从配置中获取参数
            kwargs = {
                "model": self.model_name,
                "messages": messages,
                "stream": stream,
            }
            
            # 添加AI选项参数
            if hasattr(self.ai_options, 'temperature') and self.ai_options.temperature is not None:
                kwargs["temperature"] = self.ai_options.temperature
            if hasattr(self.ai_options, 'max_tokens') and self.ai_options.max_tokens is not None:
                kwargs["max_tokens"] = self.ai_options.max_tokens
            if hasattr(self.ai_options, 'top_p') and self.ai_options.top_p is not None:
                kwargs["top_p"] = self.ai_options.top_p
            
            print(f"使用OpenAI SDK调用: {self.provider}, 模型: {self.model_name}")
            
            # 调用API
            response = self.openai_client.chat.completions.create(**kwargs)
            
            if stream:
                # 处理流式响应
                result = ""
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        result += chunk.choices[0].delta.content
                return result
            else:
                # 处理非流式响应
                if response.choices and response.choices[0].message:
                    return response.choices[0].message.content
                else:
                    print("警告: API响应中没有找到有效内容")
                    return None
                    
        except Exception as e:
            print(f"OpenAI SDK调用失败: {e}")
            return None
    
    def _chat_with_external_api(self, prompt: str, stream: bool = False) -> Optional[str]:
        """
        调用外部API（OpenAI、DeepSeek等）
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        # 为外部API构建包含system消息的请求
        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "user",
                "content": prompt.replace(f"{self.system_prompt}\n\n", "")  # 移除重复的system prompt
            }
        ]
        
        data = {
            "model": self.model_name,
            "messages": messages,
            "stream": stream,
            "temperature": self.ai_options.get('temperature', 0.0),
            "top_p": self.ai_options.get('top_p', 0.3),
            "max_tokens": self.ai_options.get('max_tokens', self.ai_options.get('num_predict', 256))
        }
        
        return self._make_request(data, stream, headers=headers, is_ollama=False)
    
    def _make_request(self, data: dict, stream: bool = False, headers: dict = None, is_ollama: bool = True) -> Optional[str]:
        """
        统一的请求方法
        """
        try:
            response = requests.post(self.api_url, json=data, timeout=self.timeout, headers=headers)
            response.raise_for_status()
            
            if stream:
                return self._handle_stream_response(response, is_ollama)
            else:
                return self._handle_normal_response(response, is_ollama)
                
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误: {e}")
            return None
    
    def _handle_stream_response(self, response, is_ollama: bool) -> str:
        """处理流式响应"""
        result = ""
        for line in response.iter_lines():
            if line:
                chunk = json.loads(line.decode('utf-8'))
                if is_ollama:
                    if 'message' in chunk and 'content' in chunk['message']:
                        content = chunk['message']['content']
                        result += content
                    if chunk.get('done', False):
                        break
                else:
                    # OpenAI/DeepSeek格式
                    if 'choices' in chunk and len(chunk['choices']) > 0:
                        delta = chunk['choices'][0].get('delta', {})
                        if 'content' in delta:
                            result += delta['content']
                    if chunk.get('choices', [{}])[0].get('finish_reason'):
                        break
        return result
    
    def _handle_normal_response(self, response, is_ollama: bool) -> str:
        """处理普通响应"""
        result = response.json()
        if is_ollama:
            return result['message']['content']
        else:
            # OpenAI/DeepSeek格式
            return result['choices'][0]['message']['content']
    
    def process_text(self, user_input: str) -> Optional[str]:
        """
        公开接口：处理用户输入的文本
        
        Args:
            user_input (str): 用户输入的原始文本
            
        Returns:
            Optional[str]: 处理后的结果，如果失败返回 None
        """
        if not user_input or not user_input.strip():
            return "输入不能为空"
        
        # 记录开始时间
        start_time = time.time()
        
        # 构建完整的提示词
        full_prompt = f"{self.system_prompt}\n\n\"input\": \"{user_input.strip()}\" /no_think"
        
        try:
            # 调用模型处理
            result = self._chat_with_ai(full_prompt)
            
            # 计算处理时间
            processing_time_ms = (time.time() - start_time) * 1000
            
            # 检查结果是否为 None
            if result is None:
                # 记录失败日志
                log_ai_process(
                    original_text=user_input,
                    ai_result=None,
                    model_name=self.model_name,
                    processing_time_ms=processing_time_ms,
                    status="failed",
                    error_message="AI模型返回None"
                )
                return None
                
            # 清理结果 - 移除思考标记和代码块标记
            result = result.strip()
            result = result.replace("<think>", "").replace("</think>", "")
            
            # 清理Markdown代码块标记
            if result.startswith("```json"):
                result = result[7:]  # 移除开头的```json
            if result.startswith("```"):
                result = result[3:]   # 移除开头的```
            if result.endswith("```"):
                result = result[:-3]  # 移除末尾的```
            
            result = result.strip()
            
            # 改进的JSON提取逻辑
            import re
            # 如果结果已经像JSON格式，直接使用
            if result.startswith('{') and result.endswith('}'):
                # 完整的JSON对象
                pass
            elif result.startswith('{'):
                # 可能是不完整的JSON，尝试修复
                print(f"检测到不完整的JSON响应: {result}")
                # 如果没有闭合，尝试找到最后一个有意义的位置
                if not result.endswith('}'):
                    # 简单修复：如果以引号结尾，加上闭合大括号
                    if result.endswith('"'):
                        result += '}'
                    elif result.endswith(','):
                        result = result[:-1] + '}'
                    else:
                        result += '}'
                    print(f"尝试修复为: {result}")
            else:
                # 尝试提取JSON对象
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    result = json_match.group(0)
                else:
                    # 如果没有找到JSON，保留原始结果但给出警告
                    print(f"警告：无法找到JSON格式，保留原始响应: {result}")
            
            result = result.strip()
            
            # 验证JSON格式
            if result:
                try:
                    import json
                    json.loads(result)  # 验证JSON是否有效
                except json.JSONDecodeError as e:
                    print(f"JSON格式无效: {e}, 原始结果: {result}")
                    # 保留原始结果，不返回None
            
            # 记录成功日志
            log_ai_process(
                original_text=user_input,
                ai_result=result,
                model_name=self.model_name,
                processing_time_ms=processing_time_ms,
                status="success"
            )
            
            return result
            
        except Exception as e:
            # 计算处理时间
            processing_time_ms = (time.time() - start_time) * 1000
            
            # 记录错误日志
            log_ai_process(
                original_text=user_input,
                ai_result=None,
                model_name=self.model_name,
                processing_time_ms=processing_time_ms,
                status="error",
                error_message=str(e)
            )
            
            print(f"处理文本时出错: {e}")
            return None
    
    def process_text_batch(self, user_inputs: list) -> list:
        """
        批量处理多个输入
        
        Args:
            user_inputs (list): 用户输入的文本列表
            
        Returns:
            list: 处理结果列表
        """
        results = []
        success_count = 0
        failed_count = 0
        
        for user_input in user_inputs:
            result = self.process_text(user_input)
            results.append({
                "input": user_input,
                "output": result
            })
            
            # 统计成功/失败数量
            if result is not None:
                success_count += 1
            else:
                failed_count += 1
        
        # 记录批量处理摘要
        try:
            from .ai_logger import log_batch_summary
            log_batch_summary(len(user_inputs), success_count, failed_count)
        except ImportError:
            pass
        
        return results
    
    def check_service_status(self) -> bool:
        """
        检查 AI 服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        try:
            if self.provider == 'ollama':
                response = requests.get(f"{self.base_url}/api/tags", timeout=5)
                return response.status_code == 200
            else:
                # 对于外部API，发送一个简单的测试请求
                test_data = {
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 1
                }
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}'
                }
                response = requests.post(self.api_url, json=test_data, headers=headers, timeout=10)
                return response.status_code == 200
        except Exception:
            return False

# 便捷函数接口
def ai_process_test_text(user_input: str, model_name: str = None, provider: str = None) -> Optional[str]:
    """
    便捷函数：处理汽车测试文本数据
    
    Args:
        user_input (str): 用户输入的文本
        model_name (str): 使用的模型名称，如果为None则使用配置文件中的模型
        provider (str): AI提供商，如果为None则使用配置文件中的提供商
        
    Returns:
        Optional[str]: 处理结果
    """
    processor = CarTestDataProcessor(model_name=model_name, provider=provider)
    return processor.process_text(user_input)

# 使用示例
if __name__ == "__main__":
    # 方式1: 使用类接口
    processor = CarTestDataProcessor()
    
    # 检查服务状态
    if not processor.check_service_status():
        print(f"{processor.provider.upper()} 服务不可用，请确保服务正在运行并且配置正确")
        exit(1)
    
    # 单个文本处理
    user_input = "第11条，左转复杂路口犹豫总分六分小分效率性五分剪辑"
    result = processor.process_text(user_input)
    
    print("=== 文本处理结果 ===")
    print(f"输入: {user_input}")
    print(f"输出: {result}")
    
    # 批量处理示例
    batch_inputs = [
        "第12条，右转信号灯超车变道总分八分小分安全性七分",
        "第13条，直行加速有问题总分五分剪辑",
        "第14条，倒车入库犹豫总分六分小分操控性四分"
    ]
    
    batch_results = processor.process_text_batch(batch_inputs)
    
    print("\n=== 批量处理结果 ===")
    for i, item in enumerate(batch_results, 1):
        print(f"{i}. 输入: {item['input']}")
        print(f"   输出: {item['output']}")
        print()
    
    # 方式2: 使用便捷函数
    print("\n=== 便捷函数示例 ===")
    simple_result = ai_process_test_text("第15条，并线超车飞道总分七分小分效率性六分")
    print(f"便捷函数结果: {simple_result}")