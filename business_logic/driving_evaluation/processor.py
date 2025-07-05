"""
driving_evaluation任务的具体业务流程执行程序
实现完整的驾驶评估任务流程
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径，确保可以导入项目模块
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
import json
from datetime import datetime
from typing import Dict, List, Any

from database.data_service import DataService

# 根据运行方式选择不同的导入方式
try:
    # 当作为模块导入时使用相对导入
    from .score_dimension_expander import create_expander_from_config
except ImportError:
    # 当直接运行时使用绝对导入
    from score_dimension_expander import create_expander_from_config

logger = logging.getLogger(__name__)

class DrivingEvaluationProcessor:
    """
    驾驶评估任务处理器
    
    实现driving_evaluation任务的完整流程：
    1. 调用excel_ai_processor.py处理Excel
    2. 调用score_dimension_expander展开评分维度
    3. 调用数据服务层存储数据
    4. 执行SQL查询获取导出数据
    5. 调用toexcel.py生成Excel文件
    """
    
    def __init__(self, config, task_config):
        """初始化驾驶评估处理器"""
        self.config = config
        self.task_config = task_config
        self.data_service = DataService()
        self.score_expander = create_expander_from_config(config)
        
        # 业务流程数据（类变量）
        self.ai_results = []
        self.expanded_results = []
        self.stored_ids = []
        self.export_data = []
        self.export_file = None
        
        logger.info("驾驶评估处理器初始化完成")
    
    def execute_task_flow(self) -> Dict[str, Any]:
        """
        执行完整的驾驶评估任务流程
        
            
        Returns:
            处理结果字典
        """
        logger.info("开始执行驾驶评估任务流程...")
        
        # 重置流程数据
        self.ai_results = []
        self.expanded_results = []
        self.stored_ids = []
        self.export_data = []
        self.export_file = None
        
        result = {
            'success': False,
            'task_name': 'driving_evaluation',
            'steps_completed': [],
            'records_processed': 0,
            'records_stored': 0,
            'export_file': None,
            'error': None,
            'execution_time': None
        }
        
        start_time = datetime.now()
        
        try:
            print("*" * 50)
            # 步骤1: Excel AI处理
            logger.info("步骤1: 调用AI处理excel...")
            self._step1_excel_ai_processing()
            result['steps_completed'].append('excel_ai_processing')
            result['records_processed'] = len(self.ai_results)
            logger.info(f"AI处理完成，处理了{len(self.ai_results)}条记录")
            
            # 步骤2: 评分维度展开
            logger.info("步骤2: 开始评分维度展开...")
            self._step2_score_dimension_expansion()
            result['steps_completed'].append('score_dimension_expansion')
            logger.info(f"评分维度展开完成，展开了{len(self.expanded_results)}条记录")
            
            # 步骤3: 数据库存储
            logger.info("步骤3: 开始数据库存储...")
            self._step3_database_storage()
            result['steps_completed'].append('database_storage')
            result['records_stored'] = len(self.stored_ids)
            logger.info(f"数据库存储完成，存储了{len(self.stored_ids)}条记录")
            
            # 步骤4: SQL查询获取导出数据
            logger.info("步骤4: SQL查询获取导出数据...")
            self._step4_sql_query_for_export()
            result['steps_completed'].append('sql_query_for_export')
            logger.info(f"SQL查询完成，获取了{len(self.export_data)}条导出记录")
            
            # 步骤5: Excel文件生成
            logger.info("步骤5: 生成Excel文件...")
            self._step5_excel_generation()
            result['steps_completed'].append('excel_generation')
            result['export_file'] = self.export_file
            logger.info(f"Excel文件生成完成: {self.export_file}")
            
            # 步骤6: 删除表中所有数据
            logger.info("步骤6: 删除所有数据...")
            self._step6_delete_all_data()

            # 计算执行时间
            end_time = datetime.now()
            result['execution_time'] = str(end_time - start_time)
            result['success'] = True
            
            logger.info("驾驶评估任务流程完成")
            
        except Exception as e:
            logger.error(f"驾驶评估任务流程失败: {e}")
            result['error'] = str(e)
            import traceback
            traceback.print_exc()
        
        return result
    
    def _step1_excel_ai_processing(self) -> None:
        """步骤1: 调用excel_ai_processor.py处理Excel"""
        try:
            # 导入excel_ai_processor
            try:
                # 当作为模块导入时使用相对导入
                from .excel_ai_processor import process_excel_file
            except ImportError:
                # 当直接运行时使用绝对导入
                from excel_ai_processor import process_excel_file
            
            # 调用AI处理
            self.ai_results = process_excel_file()
            
            if not self.ai_results:
                logger.warning("excel_ai_processor未返回数据")
                self.ai_results = []
            
            logger.debug(f"excel_ai_processor返回了{len(self.ai_results)}条结果")
            
        except Exception as e:
            logger.error(f"Excel AI处理失败: {e}")
            raise
    
    def _step2_score_dimension_expansion(self) -> None:
        """步骤2: 调用score_dimension_expander展开评分维度"""
        try:
            self.expanded_results = []
            
            for ai_result in self.ai_results:
                try:
                    # 检查AI处理状态
                    if ai_result.get('ai_processing_status') != 'success':
                        self.expanded_results.append(ai_result)
                        continue
                    
                    # 获取AI处理的JSON数据
                    ai_json_str = ai_result.get('ai_processed_result', '{}')
                    if not ai_json_str or ai_json_str.strip() == '{}':
                        self.expanded_results.append(ai_result)
                        continue
                    
                    # 解析JSON
                    try:
                        ai_data = json.loads(ai_json_str)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {e}")
                        self.expanded_results.append(ai_result)
                        continue
                    
                    # 0. 检查status字段，如果不为空则存储到活动状态表
                    if ai_data.get('status'):
                        logger.debug(f"检测到status字段: {ai_data['status']}，存储到活动状态表")
                        self._store_activity_status(ai_result, ai_data)
                        continue
                    # 调用score_dimension_expander进行评分维度展开
                    expanded_scores = self.score_expander.expand_scores(ai_data)
                    
                    # 将展开的分数添加到ai_data中
                    ai_data.update(expanded_scores)
                    
                    # 更新AI结果
                    ai_result['ai_processed_result'] = json.dumps(ai_data, ensure_ascii=False)
                    self.expanded_results.append(ai_result)
                    
                    logger.debug(f"评分维度展开完成: 记录{ai_result.get('row_index', 'unknown')}")
                    
                except Exception as e:
                    logger.error(f"评分维度展开失败（记录{ai_result.get('row_index', 'unknown')}）: {e}")
                    self.expanded_results.append(ai_result)
                    continue
            logger.info("评分维度展开完成")
        except Exception as e:
            logger.error(f"评分维度展开步骤失败: {e}")
            raise
    
    def _step3_database_storage(self) -> None:
        """步骤3: 调用数据服务层存储数据"""
        try:
            self.stored_ids = []
            
            for ai_result in self.expanded_results:
                try:
                    # 检查AI处理状态
                    if ai_result.get('ai_processing_status') != 'success':
                        continue
                    
                    # 获取AI处理的JSON数据
                    ai_json_str = ai_result.get('ai_processed_result', '{}')
                    if not ai_json_str or ai_json_str.strip() == '{}':
                        continue
                    
                    # 解析JSON
                    try:
                        ai_data = json.loads(ai_json_str)
                    except json.JSONDecodeError:
                        continue
                    
                    if ai_data.get('status','') == "start" or ai_data.get('status','') == "end":
                        continue
                    
                    record_data = {
                        'timestamp': ai_result.get('time', datetime.now()).isoformat(),
                        'original_text': ai_result.get('original_result', ''),
                        'comment': ai_data.get('comment', ''),
                        'function_type': ai_data.get('function', ''),
                        'rating': self._determine_rating(ai_data),
                        'mental_load': ai_data.get('Mental_Load', 0.0),
                        'predictability': ai_data.get('Predictable', 0.0),
                        'timely_response': ai_data.get('Timely_Response', 0.0),
                        'comfort': ai_data.get('Comfort', 0.0),
                        'efficiency': ai_data.get('Efficiency', 0.0),
                        'features': ai_data.get('Features', 0.0),
                        'safety': ai_data.get('Safety', 0.0),
                        'is_clipped': ai_data.get('是否剪辑', '否')
                    }
                    
                    # 调用数据服务层存储到数据库
                    sql, params = self._build_insert_sql(record_data)
                    record_id = self.data_service.execute_insert_sql(sql, params)
                    self.stored_ids.append(record_id)
                    logger.debug(f"存储记录成功: ID={record_id}")
                    
                except Exception as e:
                    logger.error(f"存储记录失败（记录{ai_result.get('row_index', 'unknown')}）: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"数据库存储步骤失败: {e}")
            raise
    
    def _get_main_data(self):
        """获取主数据"""
        try:
            # 读取main.sql文件
            sql_file_path = Path(__file__).parent / 'main.sql'
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql = f.read().strip()
            
            # 执行SQL查询
            data = self.data_service.execute_select_sql(sql)

            return {"data": data, "name": "main_data"}
        except Exception as e:
            logger.error(f"获取主数据失败: {e}")
            return {"data": [], "error": str(e)}

    def _get_rating_statistics(self):
        """获取评级统计"""
        try:
            # 读取rating_statistics.sql文件
            sql_file_path = Path(__file__).parent / 'rating_statistics.sql'
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql = f.read().strip()
            
            # 执行SQL查询
            data = self.data_service.execute_select_sql(sql)
            return {"data": data, "name": "rating_statistics"}
        except Exception as e:
            logger.error(f"获取评级统计失败: {e}")
            return {"data": [], "error": str(e)}

    def _get_scene_rating_statistics(self):
        """获取各场景的评级统计"""
        try:

            # 读取rating_statistics.sql文件
            sql_file_path = Path(__file__).parent / 'scene_rating_statistics.sql'
            with open(sql_file_path, 'r', encoding='utf-8') as f:
                sql = f.read().strip()
            data = self.data_service.execute_select_sql(sql)
            return {"data": data, "name": "scene_rating_statistics"}
        except Exception as e:
            logger.error(f"获取场景评级统计失败: {e}")
            return {"data": [], "error": str(e)}

    def _get_takeover_statistics(self):
        """获取接管统计"""
        try:
            if self.data_service.is_table_empty("activity_sessions"):
                logger.info("活动表为空，使用简化的接管统计查询")
                
                # 使用简化的SQL查询（基于主表时间范围）
                sql_file_path = Path(__file__).parent / 'takeover_statistics_simple.sql'
                with open(sql_file_path, 'r', encoding='utf-8') as f:
                    sql = f.read().strip()
                
                # 执行SQL查询
                data = self.data_service.execute_select_sql(sql)
                logger.debug(f"简化接管统计查询返回{len(data)}条记录")
                return {"data": data, "name": "takeover_statistics"}
            else:
                logger.info("活动表不为空，使用完整的接管统计查询")
                
                # 读取完整的takeover_statistics.sql文件
                sql_file_path = Path(__file__).parent / 'takeover_statistics.sql'
                with open(sql_file_path, 'r', encoding='utf-8') as f:
                    sql = f.read().strip()
                
                # 执行SQL查询
                data = self.data_service.execute_select_sql(sql)
                logger.debug(f"完整接管统计查询返回{len(data)}条记录")
                return {"data": data, "name": "takeover_statistics"}
                
        except Exception as e:
            logger.error(f"获取接管统计失败: {e}")
            return {"data": [], "error": str(e)}

    def _step4_sql_query_for_export(self) -> None:
        """步骤4: 执行SQL查询获取导出数据"""
        try:
            export_data = []
            export_data.append(self._get_main_data())
            export_data.append(self._get_rating_statistics())
            export_data.append(self._get_scene_rating_statistics())
            self.data_service.delete_all_data_from_table("activity_sessions")
            export_data.append(self._get_takeover_statistics())
            self.export_data = export_data
            logger.debug(f"SQL查询获取了{len(self.export_data)}个导出对象")
        except Exception as e:
            logger.error(f"SQL查询获取导出数据失败: {e}")
            raise
    
    def _step5_excel_generation(self) -> None:
        """步骤5: 调用toexcel.py生成Excel文件"""
        try:
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename_template = self.task_config.get('default_filename_template', 'ai_result_{timestamp}.xlsx')
            filename = filename_template.format(timestamp=timestamp)
            
            # 确保下载目录存在 - 使用绝对路径
            download_dir = Path(project_root) / 'download'
            download_dir.mkdir(exist_ok=True)
            output_path = download_dir / filename
            
            # 格式化数据以适配toexcel
            # formatted_data = self._format_main_data_for_excel(self.export_data)
            
            # 调用toexcel.py生成Excel
            from toexcel.toexcel import export_to_excel
            # export_to_excel(formatted_data, str(output_path))
            export_to_excel(self.export_data, str(output_path))
            
            self.export_file = str(output_path)
            logger.info(f"Excel文件生成成功: {self.export_file}")
            
        except Exception as e:
            logger.error(f"Excel文件生成失败: {e}")
            raise
    
    def _step6_delete_all_data(self) -> None:
        """步骤6: 删除表中所有数据"""
        try:
            # 调用数据服务层删除所有记录
            self.data_service.drop_table("processed_records")
            self.data_service.drop_table("activity_sessions")
            logger.info("所有数据已成功删除")
        except Exception as e:
            logger.error(f"删除所有数据失败: {e}")
            raise
    def _format_main_data_for_excel(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """格式化主数据以适配Excel导出"""
        try:
            formatted_data = []
            
            for record in data:
                formatted_record = {
                    # 'ID': record.get('id', ''),
                    '时间戳': record.get('timestamp', '').format('%Y-%m-%d %H:%M:%S'),
                    '原始文本': record.get('original_text', ''),
                    '评论': record.get('comment', ''),
                    '功能类型': record.get('function_type', ''),
                    '压力性': record.get('mental_load', 0),
                    '可预测性': record.get('predictability', 0),
                    '响应性': record.get('timely_response', 0),
                    '舒适性': record.get('comfort', 0),
                    '效率性': record.get('efficiency', 0),
                    '功能性': record.get('features', 0),
                    '安全性': record.get('safety', 0),
                    '评级': record.get('rating', 'bad'),
                    '是否剪辑': record.get('is_clipped', '否')
                }
                formatted_data.append(formatted_record)
            
            return formatted_data
            
        except Exception as e:
            logger.error(f"数据格式化失败: {e}")
            raise
    
    def _determine_rating(self, ai_data: Dict[str, Any]) -> str:
        """确定评级"""
        # 尝试从多个字段获取评级
        rating_fields = ['rating', '评级', '等级', 'level']
        
        for field in rating_fields:
            if field in ai_data and ai_data[field]:
                rating = str(ai_data[field]).lower()
                # 标准化评级
                if rating in ['pos', 'good', '好', '优秀']:
                    return 'pos'
                elif rating in ['avg', 'average', '中', '一般']:
                    return 'avg'
                elif rating in ['neg', 'poor', '差']:
                    return 'neg'
                elif rating in ['bad', 'very_poor', '很差', '极差']:
                    return 'bad'
        
        # 如果没有找到评级，根据分数判断
        score_fields = ['score', '总分', '评分']
        for field in score_fields:
            if field in ai_data and ai_data[field] is not None:
                try:
                    score = float(ai_data[field])
                    if score >= 8:
                        return 'pos'
                    elif score >= 6:
                        return 'avg'
                    elif score >= 4:
                        return 'neg'
                    else:
                        return 'bad'
                except (ValueError, TypeError):
                    continue
        
        # 默认评级
        return 'bad'
    
    # def export_data(self, filters: Dict[str, Any] = None) -> str:
    #     """
    #     导出数据（独立的导出功能）
        
    #     Args:
    #         filters: 过滤条件
            
    #     Returns:
    #         导出文件路径
    #     """
    #     try:
    #         logger.info("开始独立导出数据...")
            
    #         # 根据过滤条件获取数据
    #         if filters:
    #             self.export_data = self.data_service.get_records_by_multiple_fields(filters)
    #         else:
    #             self.export_data = self.data_service.get_all_records()
            
    #         # 生成Excel文件
    #         self._step5_excel_generation()
            
    #         logger.info(f"独立导出完成: {self.export_file}")
    #         return self.export_file
            
    #     except Exception as e:
    #         logger.error(f"独立导出失败: {e}")
    #         raise
    
    def _build_insert_sql(self, record_data: Dict[str, Any]) -> tuple:
        """
        构建插入SQL语句和参数
        
        Args:
            record_data: 记录数据字典
            
        Returns:
            tuple: (sql语句, 参数元组)
        """
        sql = """
        INSERT INTO processed_records (
            timestamp, original_text, comment, function_type, rating,
            mental_load, predictability, timely_response, comfort,
            efficiency, features, safety, is_clipped
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            record_data.get('timestamp'),
            record_data.get('original_text', ''),
            record_data.get('comment', ''),
            record_data.get('function_type', ''),
            record_data.get('rating', 'bad'),
            record_data.get('mental_load', 0.0),
            record_data.get('predictability', 0.0),
            record_data.get('timely_response', 0.0),
            record_data.get('comfort', 0.0),
            record_data.get('efficiency', 0.0),
            record_data.get('features', 0.0),
            record_data.get('safety', 0.0),
            record_data.get('is_clipped', ''),
        )
        
        return sql, params

    def _store_activity_status(self, ai_result: Dict[str, Any], ai_data: Dict[str, Any]) -> None:
        """存储活动状态到数据库"""
        try:
            status_data = {
                'timestamp': ai_result.get('time', datetime.now()).isoformat(),
                'original_text': ai_result.get('original_result', ''),
                'status': ai_data.get('status', ''),
                'comment': ai_data.get('comment', '')
            }
            
            # 构建插入活动状态的SQL
            sql = """
            INSERT INTO activity_sessions (timestamp, original_text, status, comment)
            VALUES (?, ?, ?, ?)
            """
            
            params = (
                status_data['timestamp'],
                status_data['original_text'],
                status_data['status'],
                status_data['comment']
            )
            
            # 执行插入
            record_id = self.data_service.execute_insert_sql(sql, params)
            logger.debug(f"活动状态存储成功: ID={record_id}, status={status_data['status']}")
            
        except Exception as e:
            logger.error(f"存储活动状态失败: {e}")
            raise

if __name__ == "__main__":
    # 测试驾驶评估处理器
    from config_manager import get_config
    
    config = get_config()
    task_config = config.get('task', {})
    
    processor = DrivingEvaluationProcessor(config, task_config)
    print("驾驶评估处理器初始化完成")
    
    # 执行任务流程
    print("开始执行任务流程...")
    result = processor.execute_task_flow()
    print(f"任务流程执行完成，结果: {result}")
