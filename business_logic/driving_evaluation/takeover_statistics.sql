-- 接管统计查询 - 按接管类型分别统计
-- 计算每种接管类型的次数、平均间隔和总时长

WITH activity_periods AS (
    -- 计算活动时段
    SELECT 
        start_session.timestamp as start_time,
        end_session.timestamp as end_time,
        ROUND(
            (julianday(end_session.timestamp) - julianday(start_session.timestamp)) * 24 * 60, 2
        ) as duration_minutes
    FROM activity_sessions start_session
    JOIN activity_sessions end_session ON 
        start_session.status = 'start' 
        AND end_session.status = 'end'
        AND end_session.timestamp > start_session.timestamp
        AND end_session.id = (
            SELECT MIN(id) 
            FROM activity_sessions 
            WHERE status = 'end' 
            AND timestamp > start_session.timestamp
        )
),
total_active_time AS (
    -- 计算总活动时间
    SELECT COALESCE(SUM(duration_minutes), 0) as total_minutes
    FROM activity_periods
),
takeover_by_type AS (
    -- 按接管类型统计
    SELECT 
        pr.function_type as 接管类型,
        COUNT(*) as 接管次数,
        tat.total_minutes as 总活动时间
    FROM processed_records pr
    CROSS JOIN total_active_time tat
    WHERE pr.function_type LIKE '%接管%'
    AND EXISTS (
        SELECT 1 FROM activity_periods ap
        WHERE pr.timestamp BETWEEN ap.start_time AND ap.end_time
    )
    GROUP BY pr.function_type, tat.total_minutes
),
takeover_stats AS (
    -- 计算每种接管类型的统计数据
    SELECT 
        接管类型,
        接管次数,
        CASE 
            WHEN 接管次数 > 0 AND 总活动时间 > 0 
            THEN ROUND(总活动时间 / 接管次数, 2)
            ELSE 0 
        END as 平均间隔时间_分钟,
        ROUND(总活动时间, 2) as 总时长_分钟
    FROM takeover_by_type
),
total_stats AS (
    -- 计算总计
    SELECT 
        '总计' as 接管类型,
        SUM(接管次数) as 接管次数,
        CASE 
            WHEN SUM(接管次数) > 0 AND MAX(总时长_分钟) > 0 
            THEN ROUND(MAX(总时长_分钟) / SUM(接管次数), 2)
            ELSE 0 
        END as 平均间隔时间_分钟,
        MAX(总时长_分钟) as 总时长_分钟
    FROM takeover_stats
),
final_result AS (
    -- 合并各接管类型和总计
    SELECT 接管类型, 接管次数, 平均间隔时间_分钟, 总时长_分钟
    FROM takeover_stats

    UNION ALL

    SELECT 接管类型, 接管次数, 平均间隔时间_分钟, 总时长_分钟
    FROM total_stats
    WHERE EXISTS (SELECT 1 FROM takeover_stats)
)

SELECT 接管类型, 接管次数, 平均间隔时间_分钟, 总时长_分钟
FROM final_result
ORDER BY 
    CASE 
        WHEN 接管类型 = '总计' THEN 2 
        ELSE 1 
    END,
    接管类型;