from typing import List, Dict, Any
from datetime import datetime
import logging

# 导入所需的组件
from .structured_data_refactored import ExcelDataReader, AIDataProcessor, DataFormatter, RatingCalculator
from .structured_data_components import StatisticsCalculator, DataExporter

logger = logging.getLogger(__name__)


class DataPipeline:
    """数据处理管道，协调整个数据处理流程"""
    
    def __init__(self, enable_ai_processing: bool = True):
        from config_manager import get_config
        self.config = get_config()
        self.enable_ai_processing = enable_ai_processing
        
        # 初始化各个组件
        self.reader = ExcelDataReader()
        self.ai_processor = AIDataProcessor()
        self.formatter = DataFormatter()
        self.rating_calculator = RatingCalculator()
        self.statistics_calculator = StatisticsCalculator()
        self.exporter = DataExporter()
        
        # 数据容器
        self.raw_data = []
        self.processed_data = []
        self.formatted_data = []
    
    def process_excel_file(self, file_path: str, file_name: str) -> List[Dict]:
        """
        处理Excel文件的主要流程
        
        Args:
            file_path: Excel文件路径
            file_name: Excel文件名
            
        Returns:
            格式化后的数据
        """
        try:
            logger.info(f"开始处理Excel文件: {file_path}/{file_name}")
            
            # 步骤1: 读取Excel数据
            self.raw_data = self.reader.read_excel_data(file_path, file_name)
            if not self.raw_data:
                logger.error("没有读取到有效数据")
                return []
            
            # 步骤2: AI处理（如果启用）
            if self.enable_ai_processing and self.config.data_processing.ai_processing_enabled:
                self.processed_data = self.ai_processor.process_with_ai(self.raw_data)
            else:
                logger.info("跳过AI处理步骤")
                self.processed_data = self.ai_processor._convert_to_processed_format(self.raw_data)
            
            # 步骤3: 数据格式化
            self.formatted_data = self.formatter.format_data(self.processed_data)
            
            # 步骤4: 评级计算
            self.formatted_data = self.rating_calculator.calculate_ratings(self.formatted_data)
            
            # 步骤5: 统计计算
            statistics = self._calculate_statistics()
            
            # 步骤6: 导出结果
            exported_file = self.exporter.export_results(self.formatted_data, statistics)
            if exported_file:
                logger.info(f"处理完成，结果已导出到: {exported_file}")
            
            return self.formatted_data
            
        except Exception as e:
            logger.error(f"处理Excel文件时出错: {e}")
            return []
    
    def _calculate_statistics(self) -> Dict[str, List[Dict]]:
        """计算所有统计信息"""
        return {
            'rating_total': self.statistics_calculator.get_total_rating_statistics(self.formatted_data),
            'rating_function': self.statistics_calculator.get_function_rating_statistics(self.formatted_data),
            'takeover': self.statistics_calculator.get_takeover_statistics(self.formatted_data)
        }
    
    # 兼容性方法 - 保持与原接口一致
    def get_data(self) -> List[Dict]:
        """获取原始数据"""
        return self.raw_data
    
    def get_processed_data(self) -> List[Dict]:
        """获取处理后的数据"""
        return self.processed_data if self.enable_ai_processing else self.raw_data
    
    def get_data_count(self) -> int:
        """获取数据条数"""
        return len(self.raw_data)
    
    def get_successful_processed_count(self) -> int:
        """获取成功处理的数据条数"""
        if not self.enable_ai_processing:
            return 0
        return len([r for r in self.processed_data if r['processing_status'] == 'success'])
