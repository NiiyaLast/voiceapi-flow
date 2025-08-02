"""
评分工具类
功能：接口处获取分数，根据分数返回评分等级
"""

import logging


class ScoreEvaluator:
    """
    评分工具类
    
    评分标准：
    - 7分以上为pos
    - 7分为avg  
    - 6-7分为neg
    - 6分以下为bad
    
    分数范围：0-9分，超出范围会进行边界处理并打印警告
    """
    
    # 评分常量
    RATING_POS = "pos"
    RATING_AVG = "avg"
    RATING_NEG = "neg"
    RATING_BAD = "bad"
    
    # 分数边界
    MIN_SCORE = 0
    MAX_SCORE = 9
    
    def __init__(self):
        """初始化评分器"""
        self.logger = logging.getLogger(__name__)
        
    def evaluate_score(self, score: float) -> str:
        """
        根据分数返回评分等级
        
        Args:
            score (float): 输入分数
            
        Returns:
            str: 评分等级字符串 (pos/avg/neg/bad)
        """
        # 处理边界情况
        normalized_score = self._normalize_score(score)
        
        # 根据评分标准返回等级
        if normalized_score > 7:
            return self.RATING_POS
        elif normalized_score == 7:
            return self.RATING_AVG
        elif 6 < normalized_score < 7:
            return self.RATING_NEG
        else:  # normalized_score <= 6
            return self.RATING_BAD
    
    def _normalize_score(self, score: float) -> float:
        """
        标准化分数到有效范围内
        
        Args:
            score (float): 原始分数
            
        Returns:
            float: 标准化后的分数
        """
        original_score = score
        
        # 处理上边界
        if score > self.MAX_SCORE:
            score = self.MAX_SCORE
            print(f"警告：分数越界 - 原始分数 {original_score} 超过最大值 {self.MAX_SCORE}，已调整为 {self.MAX_SCORE}")
            self.logger.warning(f"Score out of bounds: {original_score} > {self.MAX_SCORE}, normalized to {self.MAX_SCORE}")
        
        # 处理下边界
        elif score < self.MIN_SCORE:
            score = self.MIN_SCORE
            print(f"警告：分数越界 - 原始分数 {original_score} 低于最小值 {self.MIN_SCORE}，已调整为 {self.MIN_SCORE}")
            self.logger.warning(f"Score out of bounds: {original_score} < {self.MIN_SCORE}, normalized to {self.MIN_SCORE}")
        
        return score
    
    def get_rating_description(self, rating: str) -> str:
        """
        获取评分等级的描述信息
        
        Args:
            rating (str): 评分等级
            
        Returns:
            str: 评分描述
        """
        descriptions = {
            self.RATING_POS: "优秀 (7分以上)",
            self.RATING_AVG: "良好 (7分)",
            self.RATING_NEG: "一般 (6-7分)",
            self.RATING_BAD: "较差 (6分以下)"
        }
        return descriptions.get(rating, "未知评级")
    
    def batch_evaluate(self, scores: list) -> list:
        """
        批量评估分数
        
        Args:
            scores (list): 分数列表
            
        Returns:
            list: 评分结果列表，包含分数和对应评级
        """
        results = []
        for score in scores:
            rating = self.evaluate_score(score)
            results.append({
                'score': score,
                'normalized_score': self._normalize_score(score),
                'rating': rating,
                'description': self.get_rating_description(rating)
            })
        return results


# 便捷函数
def evaluate_score(score: float) -> str:
    """
    便捷函数：直接评估单个分数
    
    Args:
        score (float): 分数
        
    Returns:
        str: 评分等级
    """
    evaluator = ScoreEvaluator()
    return evaluator.evaluate_score(score)


if __name__ == "__main__":
    # 示例用法
    evaluator = ScoreEvaluator()
    
    # 测试各种分数
    test_scores = [8.5, 7.0, 6.5, 5.0, 10.0, -1.0, 9.5]
    
    print("评分测试结果：")
    print("-" * 50)
    
    for score in test_scores:
        rating = evaluator.evaluate_score(score)
        description = evaluator.get_rating_description(rating)
        print(f"分数: {score:4.1f} -> 评级: {rating:3s} ({description})")
    
    print("\n批量评估结果：")
    print("-" * 50)
    batch_results = evaluator.batch_evaluate(test_scores)
    for result in batch_results:
        print(f"原始分数: {result['score']:4.1f}, "
              f"标准化分数: {result['normalized_score']:4.1f}, "
              f"评级: {result['rating']:3s}, "
              f"描述: {result['description']}")
