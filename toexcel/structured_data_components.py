from typing import List, Dict, Any
from datetime import datetime
import logging

# 导入重构的组件
from .structured_data_refactored import ExcelDataReader, AIDataProcessor, DataFormatter, RatingCalculator

logger = logging.getLogger(__name__)


class StatisticsCalculator:
    """专门负责统计计算的类"""
    
    def __init__(self):
        from config_manager import get_config
        self.config = get_config()
        self.data_config = self.config.data_processing
        self.task_config = self.data_config.task_config
        # 从任务配置读取接管关键词
        self.takeover_keywords = self.task_config.takeover_keywords
    
    def get_total_rating_statistics(self, formatted_data: List[Dict]) -> List[Dict]:
        """
        统计各评级的数量和比例
        
        Args:
            formatted_data: 格式化后的数据
            
        Returns:
            统计结果列表
        """
        if not formatted_data:
            return []
        
        # 统计各评级数量
        rating_counts = {"pos": 0, "avg": 0, "neg": 0, "bad": 0}
        total_count = len(formatted_data)
        
        for row in formatted_data:
            rating = row.get('评价', 'bad')
            if rating in rating_counts:
                rating_counts[rating] += 1
            else:
                rating_counts['bad'] += 1
        
        # 生成统计列表
        statistics_list = []
        
        for rating_code, count in rating_counts.items():
            percentage = (count / total_count * 100) if total_count > 0 else 0
            statistics_list.append({
                "评级": rating_code,
                "数量": count,
                "比例": f"{percentage:.1f}%"
            })
        
        # 添加总计行
        statistics_list.append({
            "评级": "总计",
            "数量": total_count,
            "比例": "100.0%"
        })
        
        return statistics_list
    
    def get_function_rating_statistics(self, formatted_data: List[Dict]) -> List[Dict]:
        """
        统计不同场景下的评级分布
        
        Args:
            formatted_data: 格式化后的数据
            
        Returns:
            场景评级统计结果
        """
        if not formatted_data:
            return []
        
        function_rating_stats = {}
        all_ratings = {"pos", "avg", "neg", "bad"}
        
        # 按场景分组统计
        for row in formatted_data:
            function = row.get('function', '未知场景').strip()
            if not function:
                function = '未知场景'
            
            rating = row.get('评价', 'bad')
            
            # 初始化场景统计
            if function not in function_rating_stats:
                function_rating_stats[function] = {
                    "pos": 0, "avg": 0, "neg": 0, "bad": 0, "total": 0
                }
            
            # 统计评级数量
            if rating in all_ratings:
                function_rating_stats[function][rating] += 1
            else:
                function_rating_stats[function]["bad"] += 1
            
            function_rating_stats[function]["total"] += 1
        
        # 生成统计结果列表
        statistics_list = []
        
        for function, stats in function_rating_stats.items():
            for rating_code in ["pos", "avg", "neg", "bad"]:
                count = stats[rating_code]
                total = stats["total"]
                percentage = (count / total * 100) if total > 0 else 0
                
                statistics_list.append({
                    "场景": function,
                    "评级": rating_code,
                    "数量": count,
                    "比例": f"{percentage:.1f}%",
                    "场景总数": total
                })
        
        return statistics_list
    
    def get_takeover_statistics(self, formatted_data: List[Dict]) -> List[Dict]:
        """
        统计接管次数和平均时间
        
        Args:
            formatted_data: 格式化后的数据
            
        Returns:
            接管统计结果
        """
        if not formatted_data:
            return [{"接管类型": "无数据", "接管次数": 0, "平均间隔时间(分钟)": 0}]
        
        # 统计各类接管次数
        takeover_counts = {
            "危险接管": 0,
            "车机接管": 0,
            "人为接管": 0,
            "其他接管": 0
        }
        
        # 记录接管时间点
        takeover_times = {
            "危险接管": [],
            "车机接管": [],
            "人为接管": [],
            "其他接管": []
        }
        
        # 遍历数据统计接管
        for row in formatted_data:
            comment = row.get('comment', '').strip()
            time_str = row.get('time', '')
            
            if not comment:
                continue
            
            # 判断接管类型
            takeover_type = self._classify_takeover_type(comment)
            
            if takeover_type:
                takeover_counts[takeover_type] += 1
                takeover_times[takeover_type].append(time_str)
        
        # 计算总时间范围
        total_duration_minutes = self._calculate_total_duration(formatted_data)
        
        # 生成统计结果
        statistics_list = []
        
        for takeover_type, count in takeover_counts.items():
            if count > 0:
                avg_interval = total_duration_minutes / count if count > 0 and total_duration_minutes > 0 else 0
                
                statistics_list.append({
                    "接管类型": takeover_type,
                    "接管次数": count,
                    "平均间隔时间(分钟)": round(avg_interval, 2),
                    "总时长(分钟)": round(total_duration_minutes, 2)
                })
        
        # 如果没有任何接管记录
        if not statistics_list:
            statistics_list.append({
                "接管类型": "无接管记录",
                "接管次数": 0,
                "平均间隔时间(分钟)": 0,
                "总时长(分钟)": round(total_duration_minutes, 2)
            })
        else:
            # 添加总计行
            total_takeovers = sum(takeover_counts.values())
            overall_avg = total_duration_minutes / total_takeovers if total_takeovers > 0 else 0
            
            statistics_list.append({
                "接管类型": "总计",
                "接管次数": total_takeovers,
                "平均间隔时间(分钟)": round(overall_avg, 2),
                "总时长(分钟)": round(total_duration_minutes, 2)
            })
        
        return statistics_list
    
    def _classify_takeover_type(self, comment: str) -> str:
        """根据注释内容分类接管类型"""
        for category, keywords in self.takeover_keywords.items():
            if any(keyword in comment for keyword in keywords):
                return category
        
        # 检查是否包含"接管"关键词
        if "接管" in comment:
            return "其他接管"
        
        return None
    
    def _calculate_total_duration(self, formatted_data: List[Dict]) -> float:
        """计算总时长（分钟）"""
        all_times = [row.get('time', '') for row in formatted_data if row.get('time', '')]
        
        if len(all_times) < 2:
            return 0
        
        try:
            first_time = datetime.strptime(all_times[0], '%Y-%m-%d %H:%M:%S')
            last_time = datetime.strptime(all_times[-1], '%Y-%m-%d %H:%M:%S')
            
            total_duration = last_time - first_time
            return total_duration.total_seconds() / 60
            
        except ValueError as e:
            logger.error(f"时间解析错误: {e}")
            return 0


class DataExporter:
    """专门负责数据导出的类"""
    
    def __init__(self):
        from config_manager import get_config
        self.config = get_config()
        self.data_config = self.config.data_processing
        self.task_config = self.data_config.task_config
        # 从任务配置读取导出配置
        self.export_config = self.task_config.excel_export
    
    def export_results(self, formatted_data: List[Dict], statistics: Dict[str, List[Dict]]) -> str:
        """
        导出结果到Excel文件
        
        Args:
            formatted_data: 格式化后的数据
            statistics: 统计结果字典
            
        Returns:
            导出文件名
        """
        if not self.export_config.get('enabled', True):
            logger.info("Excel导出已禁用")
            return ""
        
        # 生成文件名
        filename = f"ai_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        try:
            # 导出主要数据
            from toexcel.toexcel import export_to_excel, export_to_excel_sheetn
            export_to_excel(formatted_data, filename)
            logger.info(f"主要数据导出完成: {filename}")
            
            # 导出统计结果（如果启用）
            if self.export_config.get('include_statistics', True):
                if 'rating_total' in statistics:
                    export_to_excel_sheetn(statistics['rating_total'], filename, sheet_name="统计总结果")
                
                if 'rating_function' in statistics:
                    export_to_excel_sheetn(statistics['rating_function'], filename, sheet_name="统计各个场景评价")
                
                if 'takeover' in statistics:
                    export_to_excel_sheetn(statistics['takeover'], filename, sheet_name="接管统计")
                
                logger.info(f"统计结果导出完成")
            
            return filename
            
        except Exception as e:
            logger.error(f"导出Excel文件时出错: {e}")
            return ""


# 导入必要的类（为了向后兼容）
from .structured_data_refactored import ExcelDataReader, AIDataProcessor, DataFormatter, RatingCalculator
