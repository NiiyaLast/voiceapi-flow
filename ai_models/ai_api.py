import requests
import json
from typing import Optional
import os

class CarTestDataProcessor:
    """汽车测试数据处理器"""
    
    def __init__(self, model_name: str = "qwen3:8b", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        self.api_url = f"{base_url}/api/chat"
        
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
            response = requests.post(self.api_url, json=data)
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
        
        # 构建完整的提示词
        full_prompt = f"{self.system_prompt}\n\n用户输入：\n{user_input.strip()}/no_think"
        
        # 调用模型处理
        result = self._chat_with_ollama(full_prompt)
        result = result.strip().replace("<think>", "").replace("</think>", "")
        return result
    
    def process_text_batch(self, user_inputs: list) -> list:
        """
        批量处理多个输入
        
        Args:
            user_inputs (list): 用户输入的文本列表
            
        Returns:
            list: 处理结果列表
        """
        results = []
        for user_input in user_inputs:
            result = self.process_text(user_input)
            results.append({
                "input": user_input,
                "output": result
            })
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
        except:
            return False

# 便捷函数接口
def ai_process_test_text(user_input: str, model_name: str = "qwen3:8b") -> Optional[str]:
    """
    便捷函数：处理汽车测试文本数据
    
    Args:
        user_input (str): 用户输入的文本
        model_name (str): 使用的模型名称
        
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