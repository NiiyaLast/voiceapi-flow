SELECT 
    id, timestamp, original_text, comment, function_type, 
    mental_load as 压力性, 
    predictability as 可预测性, 
    timely_response as 响应性, 
    comfort as 舒适性, 
    efficiency as 效率性, 
    features as 功能性, 
    safety as 安全性, 
    rating as 评价, 
    ROUND((mental_load + predictability + timely_response + comfort + efficiency + features + safety) / 7.0, 2) as 平均,
    is_clipped as 是否剪辑
FROM processed_records 

UNION ALL

SELECT 
    '' as id,
    '' as timestamp,
    '' as original_text,
    '' as comment,
    '平均分' as function_type,
    ROUND(AVG(mental_load), 2) as 压力性, 
    ROUND(AVG(predictability), 2) as 可预测性, 
    ROUND(AVG(timely_response), 2) as 响应性, 
    ROUND(AVG(comfort), 2) as 舒适性, 
    ROUND(AVG(efficiency), 2) as 效率性, 
    ROUND(AVG(features), 2) as 功能性,
    ROUND(AVG(safety), 2) as 安全性,
    '' as 评价,
    ROUND(AVG((mental_load + predictability + timely_response + comfort + efficiency + features + safety) / 7.0), 2) as 平均,
    '' as 是否剪辑
FROM processed_records

ORDER BY id;