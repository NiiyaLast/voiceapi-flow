"""
JSON工具类 - 提供JSON格式验证、修复和解析功能
"""
import json
import re
import logging
from typing import Dict, Any, Optional, Union

logger = logging.getLogger(__name__)


class JSONUtils:
    """JSON处理工具类"""
    
    @staticmethod
    def is_valid_json(text: str) -> bool:
        """
        判断字符串是否是有效的JSON格式
        
        Args:
            text: 待检测的字符串
            
        Returns:
            bool: 是否为有效JSON
        """
        if not text or not text.strip():
            return False
        
        try:
            json.loads(text.strip())
            return True
        except json.JSONDecodeError:
            return False
    
    @staticmethod
    def extract_json_from_text(text: str) -> Optional[str]:
        """
        从文本中提取JSON字符串
        
        Args:
            text: 包含JSON的文本
            
        Returns:
            Optional[str]: 提取的JSON字符串，如果没有找到则返回None
        """
        if not text or not text.strip():
            return None
        
        text = text.strip()
        
        # 查找第一个 { 和最后一个 } 的位置
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1 and start < end:
            return text[start:end+1]
        
        return None
    
    @staticmethod
    def fix_common_json_issues(text: str) -> str:
        """
        修复常见的JSON格式问题
        
        Args:
            text: 需要修复的JSON字符串
            
        Returns:
            str: 修复后的JSON字符串
        """
        if not text or not text.strip():
            return text
        
        # 移除前后空白
        fixed = text.strip()
        
        # 修复常见的引号问题
        # 将 "; 替换为 ",
        fixed = fixed.replace('";', '",')
        # 将 '; 替换为 ',
        fixed = fixed.replace("';", "',")
        
        # 修复键名缺少引号的问题
        fixed = re.sub(r'(\w+):', r'"\1":', fixed)
        
        # 移除多余的逗号（JSON对象或数组末尾的逗号）
        fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
        
        return fixed
    
    @staticmethod
    def safe_parse_json(text: str, fix_errors: bool = True) -> Optional[Dict[str, Any]]:
        """
        安全解析JSON字符串
        
        Args:
            text: JSON字符串
            fix_errors: 是否尝试修复错误
            
        Returns:
            Optional[Dict[str, Any]]: 解析后的字典，失败返回None
        """
        if not text or not text.strip():
            logger.warning("JSON字符串为空")
            return None
        
        # 首先尝试直接解析
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            logger.debug(f"直接解析JSON失败: {e}")
            
            if not fix_errors:
                return None
        
        # 尝试提取JSON部分
        extracted = JSONUtils.extract_json_from_text(text)
        if extracted:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                logger.debug("提取的JSON部分解析失败，尝试修复")
                
                # 尝试修复常见问题
                fixed = JSONUtils.fix_common_json_issues(extracted)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError as e:
                    logger.warning(f"修复后仍无法解析JSON: {e}")
        
        logger.warning(f"无法解析JSON，原始内容: {text[:100]}...")
        return None
    
    @staticmethod
    def parse_json_with_fallback(text: str, fallback_value: Union[Dict, str, None] = None) -> Union[Dict[str, Any], Any]:
        """
        解析JSON，失败时返回备用值
        
        Args:
            text: JSON字符串
            fallback_value: 解析失败时的备用值
            
        Returns:
            解析后的字典或备用值
        """
        result = JSONUtils.safe_parse_json(text)
        return result if result is not None else fallback_value
    
    @staticmethod
    def format_json(data: Union[Dict, str], indent: int = 2) -> str:
        """
        格式化JSON数据
        
        Args:
            data: 字典数据或JSON字符串
            indent: 缩进空格数
            
        Returns:
            str: 格式化后的JSON字符串
        """
        try:
            if isinstance(data, str):
                data = json.loads(data)
            return json.dumps(data, ensure_ascii=False, indent=indent)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"格式化JSON失败: {e}")
            return str(data)
    
    @staticmethod
    def validate_json_structure(data: Dict[str, Any], required_keys: list = None) -> bool:
        """
        验证JSON数据结构
        
        Args:
            data: 待验证的字典
            required_keys: 必需的键列表
            
        Returns:
            bool: 是否符合要求的结构
        """
        if not isinstance(data, dict):
            return False
        
        if required_keys:
            for key in required_keys:
                if key not in data:
                    logger.warning(f"JSON数据缺少必需的键: {key}")
                    return False
        
        return True


# 便捷函数
def is_json(text: str) -> bool:
    """判断字符串是否是有效JSON"""
    return JSONUtils.is_valid_json(text)


def parse_json(text: str, fix_errors: bool = True) -> Optional[Dict[str, Any]]:
    """安全解析JSON字符串"""
    return JSONUtils.safe_parse_json(text, fix_errors)


def fix_json(text: str) -> str:
    """修复常见JSON格式问题"""
    return JSONUtils.fix_common_json_issues(text)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("=== JSON工具类测试 ===")
    
    # 测试用例
    test_cases = [
        '{"name": "test", "value": 123}',  # 正常JSON
        '{"name": "test", "value": 123,}',  # 末尾多余逗号
        '{name: "test", value: 123}',  # 键名缺少引号
        '{"name": "test"; "value": 123}',  # 分号问题
        'Some text {"name": "test"} more text',  # 混合文本
        '{"name": "test"',  # 不完整JSON
        '',  # 空字符串
        'not json at all',  # 非JSON
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}: {test_case}")
        print(f"  是否有效JSON: {is_json(test_case)}")
        
        result = parse_json(test_case)
        if result:
            print(f"  解析结果: {result}")
        else:
            print("  解析失败")
