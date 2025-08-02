-- 按function_type统计各项评分的平均值
-- 根据main.sql反推的数据表结构：processed_records
-- 输出字段不包含：id, timestamp, original_text, comment, is_clipped

SELECT 
    function_type as 功能类型,
    ROUND(AVG(mental_load), 2) as 压力性, 
    ROUND(AVG(predictability), 2) as 可预测性, 
    ROUND(AVG(timely_response), 2) as 响应性, 
    ROUND(AVG(comfort), 2) as 舒适性, 
    ROUND(AVG(efficiency), 2) as 效率性, 
    ROUND(AVG(features), 2) as 功能性,
    ROUND(AVG(safety), 2) as 安全性,
    ROUND(AVG((mental_load + predictability + timely_response + comfort + efficiency + features + safety) / 7.0), 2) as 总体平均分,
    COUNT(*) as 记录数量
FROM processed_records 
WHERE function_type IS NOT NULL 
    AND function_type != ''
GROUP BY function_type