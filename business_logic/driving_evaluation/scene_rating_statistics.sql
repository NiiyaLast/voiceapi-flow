SELECT 
    function_type,
    ROUND(
        (COUNT(CASE WHEN rating = 'pos' THEN 1 END) * 100.0 / COUNT(*)), 2
    ) || '%' as pos,
    ROUND(
        (COUNT(CASE WHEN rating = 'avg' THEN 1 END) * 100.0 / COUNT(*)), 2
    ) || '%' as avg,
    ROUND(
        (COUNT(CASE WHEN rating = 'neg' THEN 1 END) * 100.0 / COUNT(*)), 2
    ) || '%' as neg,
    ROUND(
        (COUNT(CASE WHEN rating = 'bad' THEN 1 END) * 100.0 / COUNT(*)), 2
    ) || '%' as bad,
    COUNT(*) as 场景总数
FROM processed_records 
GROUP BY function_type 
ORDER BY function_type;
