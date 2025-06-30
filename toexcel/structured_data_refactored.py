"""
数据处理模块
建立多个专门的类，提高代码的可维护性和可扩展性
"""
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any
import os
import json
import logging

# 导入配置管理和相关模块
from config_manager import get_config
from ai_service.ai_api import ai_process_test_text 
from toexcel.toexcel import export_to_excel, export_to_excel_sheetn

# 获取日志实例
logger = logging.getLogger(__name__)

class ExcelDataReader:
    """专门负责Excel文件读取的类"""
    
    def __init__(self):
        self.config = get_config()
        self.data_config = self.config.data_processing
        self.task_config = self.data_config.task_config
    
    def read_excel_data(self, file_path: str, file_name: str) -> List[Dict]:
        """
        从Excel文件读取数据
        
        Args:
            file_path: Excel文件路径
            file_name: Excel文件名
            
        Returns:
            包含时间和结果数据的字典列表
        """
        try:
            # 构建完整的文件路径
            full_path = os.path.join(file_path, file_name)
            
            # 检查文件是否存在
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"文件不存在: {full_path}")
            
            # 读取Excel文件
            df = pd.read_excel(full_path)
            
            # 验证列名是否存在
            if 'time' not in df.columns or 'result' not in df.columns:
                raise ValueError("Excel文件必须包含'time'和'result'列")
            
            # 清理数据并转换格式
            processed_data = []
            for index, row in df.iterrows():
                try:
                    # 处理时间数据
                    time_value = row['time']
                    if pd.isna(time_value):
                        continue
                    
                    # 如果时间是字符串，尝试解析
                    if isinstance(time_value, str):
                        time_obj = datetime.strptime(time_value, '%Y-%m-%d %H:%M:%S')
                    else:
                        time_obj = time_value
                    
                    # 处理结果数据
                    result_value = row['result']
                    if pd.isna(result_value):
                        result_value = ""
                    else:
                        result_value = str(result_value).strip()
                    
                    # 创建数据记录
                    record = {
                        'time': time_obj,
                        'result': result_value,
                        'row_index': index + 1  # 记录原始行号（从1开始）
                    }
                    
                    processed_data.append(record)
                    
                except Exception as e:
                    logger.warning(f"处理第{index + 1}行数据时出错: {e}")
                    continue
            
            logger.info(f"成功读取{len(processed_data)}条数据")
            return processed_data
            
        except Exception as e:
            logger.error(f"读取Excel文件时出错: {e}")
            return []


class AIDataProcessor:
    """专门负责AI数据处理的类"""
    
    def __init__(self):
        self.config = get_config()
        self.data_config = self.config.data_processing
        # AI处理的启用状态从全局配置读取，而不是任务配置
        self.ai_enabled = self.data_config.ai_processing_enabled
        self.ai_timeout = self.data_config.ai_timeout_per_record
        self.ai_retry = self.data_config.ai_retry_failed_records
    
    def process_with_ai(self, data: List[Dict]) -> List[Dict]:
        """
        使用AI处理数据
        
        Args:
            data: 原始数据列表
            
        Returns:
            经过AI处理的数据列表
        """
        if not self.ai_enabled:
            logger.info("AI处理已禁用，跳过AI处理步骤")
            return self._convert_to_processed_format(data)
        
        logger.info("开始AI文本处理...")
        processed_data = []
        
        for i, record in enumerate(data):
            try:
                logger.info(f"处理第{i+1}/{len(data)}条数据...")
                
                # 调用AI API处理result文本（日志记录在ai_api.py中完成）
                ai_result = ai_process_test_text(record['result'])
                
                # 创建包含AI处理结果的新记录
                processed_record = {
                    'time': record['time'],
                    'original_result': record['result'],
                    'ai_processed_result': ai_result,
                    'row_index': record['row_index'],
                    'processing_status': 'success' if ai_result else 'failed'
                }
                
                processed_data.append(processed_record)
                
            except Exception as e:
                logger.error(f"AI处理第{i+1}条数据时出错: {e}")
                
                # 即使AI处理失败，也保留原始数据
                processed_record = {
                    'time': record['time'],
                    'original_result': record['result'],
                    'ai_processed_result': None,
                    'row_index': record['row_index'],
                    'processing_status': 'error',
                    'error_message': str(e)
                }
                processed_data.append(processed_record)
        
        successful_count = len([r for r in processed_data if r['processing_status'] == 'success'])
        logger.info(f"AI处理完成，成功处理{successful_count}/{len(data)}条数据")
        
        return processed_data
    
    def _convert_to_processed_format(self, data: List[Dict]) -> List[Dict]:
        """将原始数据转换为处理后的格式（不使用AI）"""
        processed_data = []
        for record in data:
            processed_record = {
                'time': record['time'],
                'original_result': record['result'],
                'ai_processed_result': None,
                'row_index': record['row_index'],
                'processing_status': 'skipped'
            }
            processed_data.append(processed_record)
        return processed_data


class DataFormatter:
    """专门负责数据格式化的类"""
    
    def __init__(self):
        self.config = get_config()
        self.data_config = self.config.data_processing
        self.task_config = self.data_config.task_config
        # 从任务配置读取
        self.score_mapping = self.task_config.score_mapping
        self.excel_config = self.task_config.excel_export
    
    def format_data(self, processed_data: List[Dict]) -> List[Dict]:
        """
        将AI处理后的数据格式化为Excel格式
        
        Args:
            processed_data: 经过AI处理的数据列表
            
        Returns:
            格式化后的数据列表
        """
        if not processed_data:
            logger.warning("没有数据可格式化")
            return []
        
        formatted_data = []
        
        for record in processed_data:
            try:
                # 处理时间格式
                time_value = record['time']
                formatted_time = time_value.strftime('%Y-%m-%d %H:%M:%S')
                
                # 初始化Excel行数据
                excel_row = self._create_default_excel_row(formatted_time)
                
                # 如果AI处理成功且有结果
                if record['processing_status'] == 'success' and record['ai_processed_result']:
                    self._parse_ai_result(excel_row, record)
                else:
                    # AI处理失败或无结果时，使用原始数据
                    excel_row['comment'] = record.get('original_result', '')[:100]
                    if 'error_message' in record:
                        excel_row['function'] = f"处理错误: {record['error_message']}"
                
                formatted_data.append(excel_row)
                
            except Exception as e:
                logger.error(f"格式化数据时出错: {e}")
                # 即使出错也要保留基本的时间信息
                error_row = self._create_error_row(record, str(e))
                formatted_data.append(error_row)
        
        logger.info(f"成功格式化{len(formatted_data)}条数据")
        return formatted_data
    
    def _create_default_excel_row(self, formatted_time: str) -> Dict[str, Any]:
        """创建默认的Excel行数据"""
        excel_row = {
            'time': formatted_time,
            'comment': '',
            'function': '',
            '是否剪辑': '否'  # 默认值
        }
        
        # 添加评分列
        for chinese_name, english_name in self.score_mapping.items():
            excel_row[english_name] = ''
        
        return excel_row
    
    def _parse_ai_result(self, excel_row: Dict[str, Any], record: Dict[str, Any]) -> None:
        """解析AI结果并填充到Excel行中"""
        try:
            # 清理AI返回的数据
            ai_result = record['ai_processed_result'].strip()
            
            # 如果不是标准JSON格式，尝试修复
            if not ai_result.startswith('{'):
                start = ai_result.find('{')
                end = ai_result.rfind('}')
                if start != -1 and end != -1:
                    ai_result = ai_result[start:end+1]
            
            # 替换可能的格式问题
            ai_result = ai_result.replace('";', '",').replace("';", "',")
            
            ai_data = json.loads(ai_result)
            
            # 提取基本信息
            excel_row['comment'] = ai_data.get('comment', '')
            excel_row['function'] = ai_data.get('function', '')
            
            # 获取总分
            total_score = ai_data.get('score', '')
            
            # 初始化所有分数维度为总分
            for english_name in self.score_mapping.values():
                excel_row[english_name] = total_score
            
            # 处理具体的中文维度分数
            for ai_key, ai_value in ai_data.items():
                if ai_key in self.score_mapping:
                    english_col = self.score_mapping[ai_key]
                    if english_col in excel_row:
                        excel_row[english_col] = ai_value
            
            # 处理"是否剪辑"字段
            if '是否剪辑' in ai_data:
                excel_row['是否剪辑'] = ai_data['是否剪辑']
                
        except json.JSONDecodeError as e:
            logger.error(f"解析AI结果JSON失败: {e}")
            logger.debug(f"原始AI结果: {record['ai_processed_result']}")
            excel_row['comment'] = record.get('original_result', '')[:100]
            
        except Exception as e:
            logger.error(f"处理AI结果时出错: {e}")
            excel_row['comment'] = record.get('original_result', '')[:100]
    
    def _create_error_row(self, record: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """创建错误行数据"""
        error_row = {
            'time': record.get('time', ''),
            'comment': f"格式化错误: {error_msg}",
            'function': '',
            '是否剪辑': '否'
        }
        
        # 添加空的评分列
        for english_name in self.score_mapping.values():
            error_row[english_name] = ''
        
        return error_row


class RatingCalculator:
    """专门负责评级计算的类"""
    
    def __init__(self):
        self.config = get_config()
        self.data_config = self.config.data_processing
        self.task_config = self.data_config.task_config
        # 从任务配置读取
        self.rating_thresholds = self.task_config.rating_thresholds
        self.score_mapping = self.task_config.score_mapping
    
    def calculate_ratings(self, formatted_data: List[Dict]) -> List[Dict]:
        """
        计算平均分和评级
        
        Args:
            formatted_data: 格式化后的数据
            
        Returns:
            添加了平均分和评级的数据
        """
        score_columns = list(self.score_mapping.values())
        
        for row in formatted_data:
            try:
                # 收集有效分数
                valid_scores = []
                
                for col in score_columns:
                    score_value = row.get(col, '')
                    
                    if score_value and str(score_value).strip():
                        try:
                            score = float(str(score_value).strip())
                            if 0 <= score <= 10:
                                valid_scores.append(score)
                            else:
                                logger.warning(f"分数超出范围 {col}={score}")
                        except (ValueError, TypeError):
                            logger.warning(f"无法解析分数 {col}={score_value}")
                            continue
                
                # 计算平均分
                if valid_scores:
                    avg_score = sum(valid_scores) / len(valid_scores)
                    avg_score = round(avg_score, 1)
                else:
                    avg_score = 0
                    logger.warning("该行没有有效分数数据")
                
                # 根据配置的阈值进行评级
                rating = self._calculate_rating(avg_score)
                
                # 添加新列
                row['平均'] = avg_score
                row['评价'] = rating
                
                logger.debug(f"时间: {row.get('time', '')}, 平均分: {avg_score}, 评级: {rating}")
                
            except Exception as e:
                logger.error(f"计算平均分时出错: {e}")
                row['平均'] = 0
                row['评价'] = "bad"
        
        return formatted_data
    
    def _calculate_rating(self, avg_score: float) -> str:
        """根据配置的阈值计算评级"""
        thresholds = self.rating_thresholds
        
        if avg_score >= thresholds.get('excellent', 8.0):
            return "pos"
        elif avg_score >= thresholds.get('good', 7.0):
            return "avg"
        elif avg_score >= thresholds.get('fair', 5.0):
            return "neg"
        else:
            return "bad"


# 继续在下一个文件中...
