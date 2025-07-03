"""
统计查询类 - 用于数据统计和分析的SQL查询
"""

class StatisticsQueries:
    """统计分析相关的SQL查询"""
    
    # 基础统计信息
    GET_BASIC_STATISTICS = """
    SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT function_type) as unique_functions,
        MIN(timestamp) as earliest_record,
        MAX(timestamp) as latest_record,
        AVG(mental_load) as avg_mental_load,
        AVG(predictability) as avg_predictability,
        AVG(timely_response) as avg_timely_response,
        AVG(comfort) as avg_comfort,
        AVG(efficiency) as avg_efficiency,
        AVG(features) as avg_features,
        AVG(safety) as avg_safety
    FROM processed_records
    """
    
    # 评级分布统计
    GET_RATING_DISTRIBUTION = """
    SELECT 
        rating,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM processed_records), 2) as percentage
    FROM processed_records
    GROUP BY rating
    ORDER BY count DESC
    """
    
    # 功能类型分布统计
    GET_FUNCTION_TYPE_DISTRIBUTION = """
    SELECT 
        function_type,
        COUNT(*) as count,
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM processed_records), 2) as percentage,
        AVG(mental_load) as avg_mental_load,
        AVG(predictability) as avg_predictability,
        AVG(timely_response) as avg_timely_response,
        AVG(comfort) as avg_comfort,
        AVG(efficiency) as avg_efficiency,
        AVG(features) as avg_features,
        AVG(safety) as avg_safety
    FROM processed_records
    WHERE function_type IS NOT NULL AND function_type != ''
    GROUP BY function_type
    ORDER BY count DESC
    """
    
    # 按日期的记录统计
    GET_DAILY_STATISTICS = """
    SELECT 
        DATE(timestamp) as date,
        COUNT(*) as record_count,
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
    GROUP BY DATE(timestamp)
    ORDER BY date DESC
    """
    
    # 按月份的记录统计
    GET_MONTHLY_STATISTICS = """
    SELECT 
        strftime('%Y-%m', timestamp) as month,
        COUNT(*) as record_count,
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
    GROUP BY strftime('%Y-%m', timestamp)
    ORDER BY month DESC
    """
    
    # 高分记录统计
    GET_HIGH_SCORE_STATISTICS = """
    SELECT 
        COUNT(*) as high_score_count,
        AVG(mental_load) as avg_mental_load,
        AVG(predictability) as avg_predictability,
        AVG(timely_response) as avg_timely_response,
        AVG(comfort) as avg_comfort,
        AVG(efficiency) as avg_efficiency,
        AVG(features) as avg_features,
        AVG(safety) as avg_safety,
        function_type,
        COUNT(*) as function_count
    FROM processed_records
    WHERE (mental_load + predictability + timely_response + comfort + efficiency + features + safety) / 7.0 >= ?
    GROUP BY function_type
    ORDER BY function_count DESC
    """
    
    # 低分记录统计
    GET_LOW_SCORE_STATISTICS = """
    SELECT 
        COUNT(*) as low_score_count,
        AVG(mental_load) as avg_mental_load,
        AVG(predictability) as avg_predictability,
        AVG(timely_response) as avg_timely_response,
        AVG(comfort) as avg_comfort,
        AVG(efficiency) as avg_efficiency,
        AVG(features) as avg_features,
        AVG(safety) as avg_safety,
        function_type,
        COUNT(*) as function_count
    FROM processed_records
    WHERE (mental_load + predictability + timely_response + comfort + efficiency + features + safety) / 7.0 <= ?
    GROUP BY function_type
    ORDER BY function_count DESC
    """
    
    # 评分维度相关性分析
    GET_SCORE_CORRELATION = """
    SELECT 
        AVG(mental_load) as avg_mental_load,
        AVG(predictability) as avg_predictability,
        AVG(timely_response) as avg_timely_response,
        AVG(comfort) as avg_comfort,
        AVG(efficiency) as avg_efficiency,
        AVG(features) as avg_features,
        AVG(safety) as avg_safety,
        STDEV(mental_load) as std_mental_load,
        STDEV(predictability) as std_predictability,
        STDEV(timely_response) as std_timely_response,
        STDEV(comfort) as std_comfort,
        STDEV(efficiency) as std_efficiency,
        STDEV(features) as std_features,
        STDEV(safety) as std_safety
    FROM processed_records
    WHERE rating = ?
    """
    
    @staticmethod
    def get_time_range_statistics(start_date=None, end_date=None):
        """
        获取指定时间范围的统计查询
        
        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            (query, params) 查询和参数元组
        """
        base_query = """
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
        
        where_conditions = []
        params = []
        
        if start_date:
            where_conditions.append("DATE(timestamp) >= ?")
            params.append(start_date)
        
        if end_date:
            where_conditions.append("DATE(timestamp) <= ?")
            params.append(end_date)
        
        if where_conditions:
            query = base_query + " WHERE " + " AND ".join(where_conditions)
        else:
            query = base_query
        
        return query, params
