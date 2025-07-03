"""
基础查询类 - 简单的SQL查询
包含常用的数据库操作查询
"""

class BaseQueries:
    """基础查询类 - 包含常用的数据库操作"""
    
    # 表信息查询
    GET_TABLE_INFO = "PRAGMA table_info({table_name})"
    
    GET_TABLE_COUNT = "SELECT COUNT(*) as count FROM {table_name}"
    
    # 记录存在性检查
    RECORD_EXISTS = """
    SELECT COUNT(*) as count 
    FROM processed_records 
    WHERE timestamp = ? AND original_text = ?
    """
    
    # 获取最新记录
    GET_LATEST_RECORDS = """
    SELECT * FROM processed_records 
    ORDER BY timestamp DESC 
    LIMIT ?
    """
    
    # 按ID获取记录
    GET_RECORD_BY_ID = """
    SELECT * FROM processed_records 
    WHERE id = ?
    """
    
    # 按时间范围获取记录
    GET_RECORDS_BY_TIME_RANGE = """
    SELECT * FROM processed_records 
    WHERE timestamp BETWEEN ? AND ?
    ORDER BY timestamp DESC
    """
    
    # 按评级获取记录
    GET_RECORDS_BY_RATING = """
    SELECT * FROM processed_records 
    WHERE rating = ?
    ORDER BY timestamp DESC
    """
    
    # 按功能类型获取记录
    GET_RECORDS_BY_FUNCTION = """
    SELECT * FROM processed_records 
    WHERE function_type = ?
    ORDER BY timestamp DESC
    """
    
    # 删除记录
    DELETE_RECORD = """
    DELETE FROM processed_records 
    WHERE id = ?
    """
    
    # 更新记录
    UPDATE_RECORD = """
    UPDATE processed_records 
    SET comment = ?, function_type = ?, rating = ?,
        mental_load = ?, predictability = ?, timely_response = ?,
        comfort = ?, efficiency = ?, features = ?, safety = ?
    WHERE id = ?
    """
    
    # 插入记录
    INSERT_RECORD = """
    INSERT INTO processed_records 
    (timestamp, original_text, comment, function_type, 
     mental_load, predictability, timely_response, comfort, 
     efficiency, features, safety, rating)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    @staticmethod
    def get_formatted_query(query_template: str, **kwargs) -> str:
        """
        格式化查询模板
        
        Args:
            query_template: 查询模板字符串
            **kwargs: 格式化参数
            
        Returns:
            格式化后的SQL查询
        """
        return query_template.format(**kwargs)
