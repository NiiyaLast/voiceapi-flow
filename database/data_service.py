"""
数据服务层 - 提供统一的数据访问接口
独立通用的数据操作层，不包含任务特定逻辑
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from pathlib import Path

# 导入数据库相关模块
from .connection import get_db_manager
from .models import ProcessedRecord, DatabaseSchema
from .queries import BaseQueries, ExportQueries, StatisticsQueries
from .sql_loader import load_sql, get_sql_loader

logger = logging.getLogger(__name__)

class DataServiceError(Exception):
    """数据服务异常"""
    pass

class DataService:
    """
    数据服务 - 独立通用的数据操作层
    
    职责：
    - 数据库连接管理
    - 基础CRUD操作
    - SQL查询执行
    - 数据验证和类型转换
    - 事务管理
    
    不包含：
    - 任务特定的业务逻辑
    - 数据格式转换
    - 评分维度展开
    - 导出逻辑
    """
    
    def __init__(self, db_path: str = None):
        """初始化数据服务"""
        self.db_manager = get_db_manager(db_path)
        self.queries = BaseQueries()
        self.export_queries = ExportQueries()
        self.statistics_queries = StatisticsQueries()
        logger.info("数据服务初始化完成")
    
    
    def execute_insert_sql(self, sql: str, params: Tuple = None) -> int:
        """
        直接执行SQL插入语句
        
        Args:
            sql: SQL插入语句
            params: SQL参数元组
            
        Returns:
            新记录的ID
            
        Raises:
            DataServiceError: SQL执行失败
        """
        try:
            if params:
                record_id = self.db_manager.execute_insert(sql, params)
            else:
                record_id = self.db_manager.execute_insert(sql)
            
            logger.debug(f"成功执行SQL插入，记录ID: {record_id}")
            return record_id
            
        except Exception as e:
            logger.error(f"执行SQL插入失败: {e}")
            raise DataServiceError(f"执行SQL插入失败: {e}")
    
    def execute_select_sql(self, sql: str, params: Tuple = None) -> List[Dict[str, Any]]:
        """
        直接执行SQL查询语句
        
        Args:
            sql: SQL查询语句
            params: SQL参数元组
            
        Returns:
            查询结果列表
            
        Raises:
            DataServiceError: SQL执行失败
        """
        try:
            if params:
                results = self.db_manager.execute_query(sql, params)
            else:
                results = self.db_manager.execute_query(sql)
            
            logger.debug(f"成功执行SQL查询，返回{len(results)}条记录")
            return results
            
        except Exception as e:
            logger.error(f"执行SQL查询失败: {e}")
            raise DataServiceError(f"执行SQL查询失败: {e}")
    
    def execute_update_sql(self, sql: str, params: Tuple = None) -> int:
        """
        直接执行SQL更新/删除语句
        
        Args:
            sql: SQL更新/删除语句
            params: SQL参数元组
            
        Returns:
            影响的行数
            
        Raises:
            DataServiceError: SQL执行失败
        """
        try:
            if params:
                affected_rows = self.db_manager.execute_update(sql, params)
            else:
                affected_rows = self.db_manager.execute_update(sql)
            
            logger.debug(f"成功执行SQL更新，影响{affected_rows}行")
            return affected_rows
            
        except Exception as e:
            logger.error(f"执行SQL更新失败: {e}")
            raise DataServiceError(f"执行SQL更新失败: {e}")
    
    def batch_create_records(self, records_data: List[Dict[str, Any]]) -> List[int]:
        """
        批量创建记录
        
        Args:
            records_data: 记录数据列表
            
        Returns:
            成功创建的记录ID列表
        """
        record_ids = []
        
        for record_data in records_data:
            try:
                record_id = self.create_record(record_data)
                record_ids.append(record_id)
            except DataServiceError as e:
                logger.error(f"批量创建中跳过失败记录: {e}")
                continue
        
        logger.info(f"批量创建完成，成功创建 {len(record_ids)}/{len(records_data)} 条记录")
        return record_ids
    
    def delete_all_data_from_table(self, table_name: str) -> bool:
        """
        删除指定表中的所有数据
        
        Args:
            table_name: 表名
            
        Returns:
            删除是否成功
        """
        try:
            
            query = f"DELETE FROM {table_name}"
            affected_rows = self.db_manager.execute_update(query)
            
            if affected_rows > 0:
                logger.info(f"成功删除表 {table_name} 中的所有数据，共删除 {affected_rows} 条记录")
                return True
            else:
                logger.info(f"表 {table_name} 中没有数据需要删除")
                return True
                
        except Exception as e:
            logger.error(f"删除表 {table_name} 中的所有数据失败: {e}")
        return False
    
    def drop_table(self, table_name: str) -> bool:
        """
        删除指定表中的所有数据
        
        Args:
            table_name: 表名

        Returns:
            删除是否成功
        """
        try:
            query = f"DROP TABLE {table_name}"
            affected_rows = self.db_manager.execute_update(query)

            if affected_rows > 0:
                logger.info(f"成功删除表 {table_name}")
                return True
            else:
                logger.info(f"未找到表 {table_name}")
                return False

        except Exception as e:
            logger.error(f"删除表 {table_name} 失败: {e}")
            return False
    
    def is_table_empty(self, table_name: str) -> bool:
        """
        检查指定表是否为空
        
        Args:
            table_name: 表名
            
        Returns:
            True表示表为空，False表示表不为空
        """
        try:
            query = f"SELECT COUNT(*) as count FROM {table_name}"
            result = self.db_manager.execute_query(query)
            
            if result and len(result) > 0:
                count = result[0]['count']
                is_empty = count == 0
                logger.info(f"表 {table_name} 中有 {count} 条记录，{'为空' if is_empty else '不为空'}")
                return is_empty
            else:
                logger.warning(f"无法获取表 {table_name} 的记录数量")
                return True
                
        except Exception as e:
            logger.error(f"检查表 {table_name} 是否为空失败: {e}")
            return True  # 发生异常时假设表为空
    
    def get_all_records(self, table_name: str) -> List[Dict[str, Any]]:
        """
        获取指定表的所有数据
        
        Args:
            table_name: 数据表名称
            
        Returns:
            记录列表
        """
        query = f"SELECT * FROM {table_name}"
        return self.db_manager.execute_query(query)
    
    
    
    # ========== 事务管理 ==========
    
    def begin_transaction(self):
        """开始事务"""
        self.db_manager.begin_transaction()
    
    def commit_transaction(self):
        """提交事务"""
        self.db_manager.commit_transaction()
    
    def rollback_transaction(self):
        """回滚事务"""
        self.db_manager.rollback_transaction()
    
    def execute_in_transaction(self, operations: List[Tuple[str, Tuple]]) -> bool:
        """
        在事务中执行多个操作
        
        Args:
            operations: 操作列表，每个操作为(query, params)元组
            
        Returns:
            是否全部成功
        """
        try:
            self.begin_transaction()
            
            for query, params in operations:
                self.db_manager.execute_update(query, params)
            
            self.commit_transaction()
            return True
            
        except Exception as e:
            self.rollback_transaction()
            logger.error(f"事务执行失败: {e}")
            return False
    
    
    # ========== 工具方法 ==========
    
    def get_db_info(self) -> Dict[str, Any]:
        """
        获取数据库信息
        
        Returns:
            数据库信息字典
        """
        return {
            'db_path': self.db_manager.db_path,
            'total_records': self.count_records(),
            'table_schema': self._get_table_schema(),
            'db_size': self._get_db_size()
        }
    
    
    def _get_db_size(self) -> int:
        """获取数据库文件大小（字节）"""
        try:
            db_path = Path(self.db_manager.db_path)
            return db_path.stat().st_size if db_path.exists() else 0
        except Exception:
            return 0
    
    def close(self):
        """关闭数据库连接"""
        if hasattr(self.db_manager, 'close'):
            self.db_manager.close()
        logger.info("数据服务已关闭")
