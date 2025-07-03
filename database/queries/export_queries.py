"""
导出查询类 - 用于Excel导出的SQL查询
"""

class ExportQueries:
    """导出相关的SQL查询"""
    
    # 导出所有记录 - 基础版本
    SELECT_ALL_RECORDS = """
    SELECT 
        id,
        timestamp,
        original_text,
        comment,
        function_type,
        mental_load,
        predictability,
        timely_response,
        comfort,
        efficiency,
        features,
        safety,
        rating,
        created_at
    FROM processed_records 
    ORDER BY timestamp DESC
    """
    
    # 导出指定时间范围的记录
    SELECT_RECORDS_BY_DATE_RANGE = """
    SELECT 
        id,
        timestamp,
        original_text,
        comment,
        function_type,
        mental_load,
        predictability,
        timely_response,
        comfort,
        efficiency,
        features,
        safety,
        rating,
        created_at
    FROM processed_records 
    WHERE DATE(timestamp) BETWEEN ? AND ?
    ORDER BY timestamp DESC
    """
    
    # 导出指定评级的记录
    SELECT_RECORDS_BY_RATING = """
    SELECT 
        id,
        timestamp,
        original_text,
        comment,
        function_type,
        mental_load,
        predictability,
        timely_response,
        comfort,
        efficiency,
        features,
        safety,
        rating,
        created_at
    FROM processed_records 
    WHERE rating IN ({rating_list})
    ORDER BY timestamp DESC
    """
    
    # 导出指定功能类型的记录
    SELECT_RECORDS_BY_FUNCTION = """
    SELECT 
        id,
        timestamp,
        original_text,
        comment,
        function_type,
        mental_load,
        predictability,
        timely_response,
        comfort,
        efficiency,
        features,
        safety,
        rating,
        created_at
    FROM processed_records 
    WHERE function_type IN ({function_list})
    ORDER BY timestamp DESC
    """
    
    # 导出高质量记录（评分高于阈值）
    SELECT_HIGH_QUALITY_RECORDS = """
    SELECT 
        id,
        timestamp,
        original_text,
        comment,
        function_type,
        mental_load,
        predictability,
        timely_response,
        comfort,
        efficiency,
        features,
        safety,
        rating,
        created_at,
        (mental_load + predictability + timely_response + comfort + efficiency + features + safety) / 7.0 as avg_score
    FROM processed_records 
    WHERE (mental_load + predictability + timely_response + comfort + efficiency + features + safety) / 7.0 >= ?
    ORDER BY avg_score DESC, timestamp DESC
    """
    
    # 导出摘要信息
    SELECT_SUMMARY_INFO = """
    SELECT 
        COUNT(*) as total_records,
        AVG(mental_load) as avg_mental_load,
        AVG(predictability) as avg_predictability,
        AVG(timely_response) as avg_timely_response,
        AVG(comfort) as avg_comfort,
        AVG(efficiency) as avg_efficiency,
        AVG(features) as avg_features,
        AVG(safety) as avg_safety,
        COUNT(CASE WHEN rating = 'pos' THEN 1 END) as positive_count,
        COUNT(CASE WHEN rating = 'avg' THEN 1 END) as average_count,
        COUNT(CASE WHEN rating = 'neg' THEN 1 END) as negative_count,
        COUNT(CASE WHEN rating = 'bad' THEN 1 END) as bad_count
    FROM processed_records
    """
    
    @staticmethod
    def format_in_clause(items):
        """
        格式化IN子句的占位符
        
        Args:
            items: 需要格式化的项目列表
            
        Returns:
            格式化后的占位符字符串
        """
        return ','.join(['?' for _ in items])
    
    @staticmethod
    def get_export_query_with_filters(filters=None):
        """
        根据过滤条件构建导出查询
        
        Args:
            filters: 过滤条件字典
            
        Returns:
            (query, params) 查询和参数元组
        """
        base_query = """
        SELECT 
            id,
            timestamp,
            original_text,
            comment,
            function_type,
            mental_load,
            predictability,
            timely_response,
            comfort,
            efficiency,
            features,
            safety,
            rating,
            created_at
        FROM processed_records 
        WHERE 1=1
        """
        
        where_conditions = []
        params = []
        
        if filters:
            # 时间范围过滤
            if filters.get('start_date'):
                where_conditions.append("DATE(timestamp) >= ?")
                params.append(filters['start_date'])
            
            if filters.get('end_date'):
                where_conditions.append("DATE(timestamp) <= ?")
                params.append(filters['end_date'])
            
            # 评级过滤
            if filters.get('ratings'):
                rating_placeholders = ExportQueries.format_in_clause(filters['ratings'])
                where_conditions.append(f"rating IN ({rating_placeholders})")
                params.extend(filters['ratings'])
            
            # 功能类型过滤
            if filters.get('function_types'):
                func_placeholders = ExportQueries.format_in_clause(filters['function_types'])
                where_conditions.append(f"function_type IN ({func_placeholders})")
                params.extend(filters['function_types'])
            
            # 评分阈值过滤
            if filters.get('min_score'):
                where_conditions.append(
                    "(mental_load + predictability + timely_response + comfort + efficiency + features + safety) / 7.0 >= ?"
                )
                params.append(filters['min_score'])
        
        # 构建完整查询
        if where_conditions:
            query = base_query + " AND " + " AND ".join(where_conditions)
        else:
            query = base_query
        
        query += " ORDER BY timestamp DESC"
        
        return query, params
