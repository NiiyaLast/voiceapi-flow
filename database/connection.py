"""
数据库连接管理
提供单例模式的数据库连接和基础操作
"""
import sqlite3
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
from contextlib import contextmanager

from .models import DatabaseSchema

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器 - 单例模式"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: str = None):
        if hasattr(self, '_initialized'):
            return
            
        self.db_path = db_path or './data/voiceapi_flow.db'
        self._initialized = True
        self._ensure_db_directory()
        self.init_database()
    
    def _ensure_db_directory(self):
        """确保数据库目录存在"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"数据库目录: {db_dir}")
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """初始化数据库表结构"""
        try:
            with self.get_connection() as conn:
                # 创建表
                conn.execute(DatabaseSchema.PROCESSED_RECORDS_TABLE)
                conn.execute(DatabaseSchema.ACTIVITY_SESSIONS_TABLE)
                
                # 创建索引
                for index_sql in DatabaseSchema.INDEXES:
                    conn.execute(index_sql)
                
                conn.commit()
                logger.info(f"数据库初始化完成: {self.db_path}")
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询并返回结果"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or ())
            return [dict(row) for row in cursor.fetchall()]
    
    def execute_insert(self, query: str, params: tuple = None) -> int:
        """执行插入操作并返回新记录的ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or ())
            conn.commit()
            return cursor.lastrowid
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新操作并返回影响的行数"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params or ())
            conn.commit()
            return cursor.rowcount
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表结构信息"""
        return self.execute_query(f"PRAGMA table_info({table_name})")
    
    def get_table_count(self, table_name: str) -> int:
        """获取表记录数"""
        result = self.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
        return result[0]['count'] if result else 0

# 全局数据库管理器实例
def get_db_manager(db_path: str = None) -> DatabaseManager:
    """获取数据库管理器实例"""
    return DatabaseManager(db_path)
