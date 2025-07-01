"""
数据处理模块 - 兼容性封装
保持原有接口不变，内部使用重构后的组件实现
"""
import logging
from typing import List, Dict
from .data_pipeline import DataPipeline

logger = logging.getLogger(__name__)

class ExcelDataReader:
    """
    Excel数据读取器 - 兼容性封装类
    内部使用重构后的DataPipeline实现，保持原有接口不变
    """
    
    def __init__(self, enable_ai_processing: bool = True):
        self.enable_ai_processing = enable_ai_processing
        self.pipeline = DataPipeline(enable_ai_processing=enable_ai_processing)
        
        # 兼容性属性
        self.data = []
        self.processed_data = []
        self.formatted_data = []
    
    def read_excel_data(self, file_path: str, file_name: str) -> List[Dict]:
        """
        从Excel文件读取数据并进行完整处理
        
        Args:
            file_path: Excel文件路径
            file_name: Excel文件名
            
        Returns:
            包含时间和结果数据的字典列表
        """
        try:
            # 使用新的数据管道处理
            self.formatted_data = self.pipeline.process_excel_file(file_path, file_name)
            
            # 更新兼容性属性
            self.data = self.pipeline.get_data()
            self.processed_data = self.pipeline.get_processed_data()
            
            logger.info(f"数据处理完成，共处理{len(self.data)}条数据")
            return self.data
            
        except Exception as e:
            logger.error(f"处理Excel文件时出错: {e}")
            return []
    
    def _process_with_ai(self):
        """
        兼容性方法 - 已在新管道中集成
        """
        logger.info("AI处理已集成到主流程中")
    
    def format_data(self):
        """
        兼容性方法 - 已在新管道中集成
        """
        logger.info("数据格式化已集成到主流程中")
    
    def calculate_average_and_rating(self):
        """
        兼容性方法 - 已在新管道中集成
        """
        logger.info("评级计算已集成到主流程中")
    
    def get_total_rating_statistics(self) -> List[Dict]:
        """
        统计各评级的数量和比例
        
        Returns:
            统计结果列表
        """
        return self.pipeline.statistics_calculator.get_total_rating_statistics(self.formatted_data)
    
    def get_function_rating_statistics(self) -> List[Dict]:
        """
        统计不同场景下的各个评级数量
        
        Returns:
            统计结果列表
        """
        return self.pipeline.statistics_calculator.get_function_rating_statistics(self.formatted_data)
    
    def get_takeover_statistics(self) -> List[Dict]:
        """
        统计接管次数以及平均时间
        
        Returns:
            接管统计结果列表
        """
        return self.pipeline.statistics_calculator.get_takeover_statistics(self.formatted_data)
    
    def get_data(self) -> List[Dict]:
        """获取原始读取的数据"""
        return self.pipeline.get_data()
    
    def get_processed_data(self) -> List[Dict]:
        """获取经过AI处理的数据"""
        return self.pipeline.get_processed_data()
    
    def get_data_count(self) -> int:
        """获取数据条数"""
        return self.pipeline.get_data_count()
    
    def get_successful_processed_count(self) -> int:
        """获取成功处理的数据条数"""
        return self.pipeline.get_successful_processed_count()


# 保持原有的开放接口函数
def process_excel_with_ai(file_path: str, file_name: str, enable_ai_processing: bool = True) -> ExcelDataReader:
    """
    开放接口：从指定位置读取Excel文件数据并进行AI处理
    
    Args:
        file_path: Excel文件所在路径
        file_name: Excel文件名
        enable_ai_processing: 是否启用AI处理
        
    Returns:
        ExcelDataReader实例，包含读取和处理的数据
    """
    reader = ExcelDataReader(enable_ai_processing=enable_ai_processing)
    reader.read_excel_data(file_path, file_name)
    return reader


# 使用示例
if __name__ == "__main__":
    # 示例用法
    file_path = r"C:\niiya\tools\AI\voiceapi\voiceapi\download"
    file_name = "asr_results_2025-06-23_18-09-33.xlsx"
    
    # 使用开放接口读取数据并进行AI处理
    reader = process_excel_with_ai(file_path, file_name, enable_ai_processing=True)
    
    logger.info(f"共读取到{reader.get_data_count()}条数据")
    logger.info(f"成功处理{reader.get_successful_processed_count()}条数据")