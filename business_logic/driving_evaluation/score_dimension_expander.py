"""
评分维度展开器 - 将AI结果标准化为完整的评分维度
单独实现，供 structured_data.py 调用
"""
import logging
from typing import Dict, Any, List, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class ScoreDimensionExpander:
    """评分维度展开器"""
    
    def __init__(self, score_mapping: Dict[str, str]):
        """
        初始化展开器
        
        Args:
            score_mapping: 中文维度名到英文字段名的映射
                如: {"压力性": "Mental_Load", "效率性": "Efficiency", ...}
        """
        self.score_mapping = score_mapping
        self.dimension_names = list(score_mapping.keys())  # 中文维度名列表
        self.field_names = list(score_mapping.values())    # 英文字段名列表
        
        # 预定义的基准分数字段（总分字段）
        self.base_score_fields = ['score', '总分', '评分', 'rating']
        
        logger.info(f"评分维度展开器初始化完成，支持{len(self.score_mapping)}个维度")
    
    def expand_scores(self, ai_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        展开评分维度
        
        Args:
            ai_result: AI处理结果，包含原始JSON数据
            
        Returns:
            包含完整评分维度的字典
        """
        try:
            
            # 1. 获取基准分数
            base_score = self._get_base_score(ai_result)
            
            # 2. 初始化所有维度为基准分数
            expanded_scores = {}
            for field_name in self.field_names:
                expanded_scores[field_name] = base_score
            
            # 3. 提取特定维度分数并覆盖
            specific_scores = self._extract_specific_scores(ai_result)
            expanded_scores.update(specific_scores)
            
            # 4. 添加调试信息
            logger.debug(f"评分维度展开: 基准分数={base_score}, 特定维度={len(specific_scores)}, "
                        f"最终维度={len(expanded_scores)}")
            
            return expanded_scores
            
        except Exception as e:
            logger.error(f"评分维度展开失败: {e}")
            # 返回默认分数
            return dict.fromkeys(self.field_names, 0.0)
    
    def _get_base_score(self, ai_result: Dict[str, Any]) -> float:
        """获取基准分数（总分）"""
        for field in self.base_score_fields:
            if field in ai_result:
                value = ai_result[field]
                if self._is_valid_score(value):
                    return self._convert_to_number(value)
        
        # 如果没有找到基准分数，返回0
        logger.warning("未找到有效的基准分数，使用默认值0")
        return 0.0
    
    def _extract_specific_scores(self, ai_result: Dict[str, Any]) -> Dict[str, float]:
        """提取特定维度的分数"""
        specific_scores = {}
        
        for chinese_name, english_name in self.score_mapping.items():
            if chinese_name in ai_result:
                value = ai_result[chinese_name]
                if self._is_valid_score(value):
                    specific_scores[english_name] = self._convert_to_number(value)
                    logger.debug(f"提取特定维度: {chinese_name}({english_name}) = {value}")
        
        return specific_scores
    
    def _is_valid_score(self, value: Any) -> bool:
        """验证分数值是否有效"""
        if value is None or value == '':
            return False
        
        try:
            # 尝试转换为数字
            num_value = self._convert_to_number(value)
            # 检查范围（假设评分范围是0-10）
            return 0 <= num_value <= 10
        except (ValueError, TypeError):
            return False
    
    def _convert_to_number(self, value: Any) -> float:
        """将值转换为数字"""
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # 移除可能的文字后缀（如"7分"）
            cleaned = value.replace('分', '').replace('分数', '').strip()
            return float(cleaned)
        
        raise ValueError(f"无法转换为数字: {value}")
    
    def get_summary(self) -> Dict[str, Any]:
        """获取展开器配置摘要"""
        return {
            'supported_dimensions': len(self.score_mapping),
            'dimension_mapping': self.score_mapping.copy(),
            'base_score_fields': self.base_score_fields.copy()
        }

# 工厂函数
def create_expander_from_config(config_manager) -> ScoreDimensionExpander:
    """从配置管理器创建展开器"""
    try:
        # 从config.yaml获取task.score_mapping
        score_mapping = config_manager.get('task.score_mapping', {})
        
        if not score_mapping:
            logger.warning("配置中未找到task.score_mapping，使用默认映射")
            # 使用默认映射
            score_mapping = {
                "压力性": "Mental_Load",
                "可预测性": "Predictable", 
                "响应性": "Timely_Response",
                "舒适性": "Comfort",
                "效率性": "Efficiency",
                "功能性": "Features",
                "安全性": "Safety"
            }
        
        return ScoreDimensionExpander(score_mapping)
        
    except Exception as e:
        logger.error(f"创建评分维度展开器失败: {e}")
        raise
