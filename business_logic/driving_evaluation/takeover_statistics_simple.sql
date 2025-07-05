-- 简化的接管统计查询 - 当活动表为空时使用
-- 基于主表的第一条和最后一条数据计算时间范围，然后统计接管次数

WITH time_range AS (
    -- 获取主表数据的时间范围
    SELECT 
        MIN(timestamp) as start_time,
        MAX(timestamp) as end_time,
        ROUND(
            (julianday(MAX(timestamp)) - julianday(MIN(timestamp))) * 24 * 60, 2
        ) as duration_minutes
    FROM processed_records
    WHERE timestamp IS NOT NULL
),
takeover_by_type AS (
    -- 按接管类型统计
    SELECT 
        pr.function_type as 接管类型,
        COUNT(*) as 接管次数,
        tr.duration_minutes as 总时长_分钟
    FROM processed_records pr
    CROSS JOIN time_range tr
    WHERE pr.function_type LIKE '%接管%'
    GROUP BY pr.function_type, tr.duration_minutes
),
takeover_stats AS (
    -- 计算每种接管类型的统计数据
    SELECT 
        接管类型,
        接管次数,
        CASE 
            WHEN 接管次数 > 0 AND 总时长_分钟 > 0 
            THEN ROUND(总时长_分钟 / 接管次数, 2)
            ELSE 0 
        END as 平均间隔时间_分钟,
        总时长_分钟
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

SELECT 
    接管类型, 
    接管次数, 
    平均间隔时间_分钟, 
    总时长_分钟
FROM final_result
ORDER BY 
    CASE 
        WHEN 接管类型 = '总计' THEN 2 
        ELSE 1 
    END,
    接管类型;
