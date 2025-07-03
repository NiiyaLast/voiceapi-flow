SELECT 
    rating as 评级,
    COUNT(*) as 数量,
    ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM processed_records)), 1) || '%' as 比例
FROM processed_records 
GROUP BY rating
UNION ALL
SELECT 
    '总计' as 评级,
    COUNT(*) as 数量,
    '100.0%' as 比例
FROM processed_records;
