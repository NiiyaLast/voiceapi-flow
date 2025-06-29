import requests
import json
from typing import Optional
import os
import time
# 添加配置管理导入
try:
    from config_manager import get_config
    config = get_config()
except ImportError:
    config = None

# 导入AI日志模块
try:
    from .ai_logger import log_ai_process
except ImportError:
    # 如果导入失败，定义一个空的日志函数
    def log_ai_process(*args, **kwargs):
        pass

class CarTestDataProcessor:
    """汽车测试数据处理器"""
    
    def __init__(self, model_name: str = None, base_url: str = None):
        # 优先使用配置文件的设置，然后是传入参数，最后是默认值
        if config:
            self.model_name = model_name or config.ai.model_name
            self.base_url = base_url or config.ai.api_url
            self.timeout = config.ai.timeout
            self.max_retries = config.ai.max_retries
        # else:
        #     self.model_name = model_name or "qwen3:8b"
        #     self.base_url = base_url or "http://localhost:11434"
        #     self.timeout = 30
        #     self.max_retries = 3
            
        self.api_url = f"{self.base_url}/api/chat"
        
        # 预定义的系统提示词
        self.system_prompt = self._load_system_prompt("system_prompt.txt")


    def _load_system_prompt(self, prompt_file: str) -> str:
        """
        从文件读取系统提示词
        
        Args:
            prompt_file (str): 提示词文件名
            
        Returns:
            str: 提示词内容
        """
        try:
            # 获取当前文件所在目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_path = os.path.join(current_dir, prompt_file)
            
            # 读取提示词文件
            with open(prompt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # print(f"成功加载提示词文件: {prompt_path}")
            return content
            
        except FileNotFoundError:
            print(f"提示词文件 {prompt_file} 不存在，使用默认提示词")
            return self._get_default_prompt()
        except Exception as e:
            print(f"读取提示词文件时出错: {e}，使用默认提示词")
            return self._get_default_prompt()

    def _chat_with_ollama(self, prompt: str, stream: bool = False) -> Optional[str]:
        """
        内部方法：调用 Ollama API
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
            "options": {
                "temperature": 0.1,  # 降低随机性，提高一致性
                "top_p": 0.7,  # 使用 nucleus sampling
                "top_k": 40, # 限制采样范围
                "num_predict": 512,  # 限制输出长度
            },
            
        }
        
        try:
            response = requests.post(self.api_url, json=data, timeout=self.timeout)
            response.raise_for_status()
            
            if stream:
                # 流式响应处理
                result = ""
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line.decode('utf-8'))
                        if 'message' in chunk and 'content' in chunk['message']:
                            content = chunk['message']['content']
                            result += content
                        if chunk.get('done', False):
                            break
                return result
            else:
                # 非流式响应
                result = response.json()
                return result['message']['content']
                
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误: {e}")
            return None
    
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
        full_prompt = f"{self.system_prompt}\n\n用户输入：\n{user_input.strip()}/no_think"
        
        try:
            # 调用模型处理
            result = self._chat_with_ollama(full_prompt)
            
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
                
            # 清理结果
            result = result.strip().replace("<think>", "").replace("</think>", "")
            
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
        检查 Ollama 服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

# 便捷函数接口
def ai_process_test_text(user_input: str, model_name: str = None) -> Optional[str]:
    """
    便捷函数：处理汽车测试文本数据
    
    Args:
        user_input (str): 用户输入的文本
        model_name (str): 使用的模型名称，如果为None则使用配置文件中的模型
        
    Returns:
        Optional[str]: 处理结果
    """
    processor = CarTestDataProcessor(model_name=model_name)
    return processor.process_text(user_input)

# 使用示例
if __name__ == "__main__":
    # 方式1: 使用类接口
    processor = CarTestDataProcessor()
    
    # 检查服务状态
    if not processor.check_service_status():
        print("Ollama 服务不可用，请确保 Ollama 正在运行")
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