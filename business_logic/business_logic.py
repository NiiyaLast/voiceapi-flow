"""
业务逻辑层通用接口
仅负责根据配置文件的task.name路由到对应的业务流程实现
"""
import logging
from typing import Dict, Any

from config_manager import get_config

logger = logging.getLogger(__name__)

class BusinessLogicRouter:
    """
    业务逻辑路由器
    
    职责：
    - 读取配置文件中的任务名称
    - 根据任务名称路由到对应的业务流程实现
    - 仅提供路由功能，不包含具体业务逻辑
    """
    
    def __init__(self):
        """初始化业务逻辑路由器"""
        self.config = get_config()
        self.task_config = self._load_task_config()
        self.task_name = self.task_config.get('name')
        
        logger.info(f"业务逻辑路由器初始化完成，当前任务: {self.task_name}")
    
    def _load_task_config(self) -> Dict[str, Any]:
        """从配置文件加载任务配置"""
        try:
            # 直接使用config_manager的task属性
            task_config = self.config.task
            
            task_name = task_config.get('name')
            if not task_name:
                raise ValueError("任务配置中缺少name字段")
            
            logger.info(f"加载任务配置: {task_name}")
            return task_config
            
        except Exception as e:
            logger.error(f"加载任务配置失败: {e}")
            raise
    
    def route_to_processor(self):
        """根据任务名称路由到对应的处理器"""
        if self.task_name == "driving_evaluation":
            from .driving_evaluation import DrivingEvaluationProcessor
            return DrivingEvaluationProcessor(self.config, self.task_config)
        else:
            raise ValueError(f"不支持的任务类型: {self.task_name}")
    
    def get_task_name(self) -> str:
        """获取当前任务名称"""
        return self.task_name
    
    def get_task_config(self) -> Dict[str, Any]:
        """获取任务配置"""
        return self.task_config


if __name__ == "__main__":
    # 测试业务逻辑路由器
    router = BusinessLogicRouter()
    print(f"任务名称: {router.get_task_name()}")
    print(f"任务配置: {router.get_task_config()}")
    processor = router.route_to_processor()
    print(f"路由到的处理器: {type(processor).__name__}")
