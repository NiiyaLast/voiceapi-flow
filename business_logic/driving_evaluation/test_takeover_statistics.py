"""
测试接管统计功能
验证活动状态表和接管统计SQL的正确性
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import logging
import json
from datetime import datetime, timedelta
from database.data_service import DataService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_takeover_statistics():
    """测试接管统计功能"""
    
    # 初始化数据服务
    data_service = DataService()
    
    # 清理测试数据
    try:
        data_service.execute_update_sql("DELETE FROM activity_sessions")
        data_service.execute_update_sql("DELETE FROM processed_records")
        logger.info("清理测试数据完成")
    except Exception as e:
        logger.warning(f"清理测试数据失败（可能表不存在）: {e}")
    
    # 插入测试的活动状态数据
    test_start_time = datetime.now()
    
    # 第一个活动时段：30分钟
    activity_sessions = [
        (test_start_time, "开始测试", "start", "开始测试"),
        (test_start_time + timedelta(minutes=30), "结束测试", "end", "结束测试"),
        # 休息10分钟
        (test_start_time + timedelta(minutes=40), "继续测试", "start", "继续测试"),
        (test_start_time + timedelta(minutes=70), "今天到此结束", "end", "今天到此结束"),
    ]
    
    for timestamp, original_text, status, comment in activity_sessions:
        sql = "INSERT INTO activity_sessions (timestamp, original_text, status, comment) VALUES (?, ?, ?, ?)"
        params = (timestamp.isoformat(), original_text, status, comment)
        record_id = data_service.execute_insert_sql(sql, params)
        logger.info(f"插入活动状态: ID={record_id}, status={status}, time={timestamp}")
    
    # 插入测试的接管数据
    takeover_records = [
        # 第一个活动时段内的接管
        (test_start_time + timedelta(minutes=5), "危险接管", "危险接管"),
        (test_start_time + timedelta(minutes=15), "车机接管", "车机接管"),
        (test_start_time + timedelta(minutes=25), "人为接管", "人为接管"),
        # 第二个活动时段内的接管
        (test_start_time + timedelta(minutes=45), "危险接管", "危险接管"),
        (test_start_time + timedelta(minutes=60), "车机接管", "车机接管"),
        # 非接管记录
        (test_start_time + timedelta(minutes=10), "左转", "左转"),
        (test_start_time + timedelta(minutes=20), "右转", "右转"),
        (test_start_time + timedelta(minutes=50), "变道", "变道"),
    ]
    
    for timestamp, comment, function_type in takeover_records:
        sql = """
        INSERT INTO processed_records (
            timestamp, original_text, comment, function_type, rating,
            mental_load, predictability, timely_response, comfort,
            efficiency, features, safety, is_clipped
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            timestamp.isoformat(),
            comment,
            comment,
            function_type,
            'avg',
            7.0, 7.0, 7.0, 7.0, 7.0, 7.0, 7.0,
            '否'
        )
        record_id = data_service.execute_insert_sql(sql, params)
        logger.info(f"插入记录: ID={record_id}, function={function_type}")
    
    # 执行接管统计查询
    logger.info("=" * 50)
    logger.info("执行接管统计查询...")
    
    try:
        sql_file_path = Path(__file__).parent / 'takeover_statistics.sql'
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql = f.read().strip()
        
        results = data_service.execute_select_sql(sql)
        
        logger.info("接管统计结果:")
        for i, result in enumerate(results):
            logger.info(f"  第{i+1}行:")
            for key, value in result.items():
                logger.info(f"    {key}: {value}")
        
        # 验证结果
        if results:
            # 检查是否有总计行
            total_row = None
            type_rows = []
            
            for result in results:
                if result.get('接管类型') == '总计':
                    total_row = result
                else:
                    type_rows.append(result)
            
            logger.info("=" * 50)
            logger.info("验证结果:")
            
            # 验证接管类型统计
            expected_types = {'危险接管': 2, '车机接管': 2, '人为接管': 1}  # 预期各类型次数
            logger.info("各类型接管统计:")
            for row in type_rows:
                takeover_type = row.get('接管类型', '')
                count = row.get('接管次数', 0)
                interval = row.get('平均间隔时间_分钟', 0)
                total_time = row.get('总时长_分钟', 0)
                
                logger.info(f"  {takeover_type}: {count}次, 间隔{interval}分钟, 总时长{total_time}分钟")
                
                if takeover_type in expected_types:
                    expected_count = expected_types[takeover_type]
                    if count == expected_count:
                        logger.info(f"    ✅ {takeover_type}次数正确")
                    else:
                        logger.error(f"    ❌ {takeover_type}次数错误: 预期{expected_count}, 实际{count}")
            
            # 验证总计行
            if total_row:
                total_count = total_row.get('接管次数', 0)
                total_interval = total_row.get('平均间隔时间_分钟', 0)
                total_time = total_row.get('总时长_分钟', 0)
                
                logger.info(f"总计统计: {total_count}次, 间隔{total_interval}分钟, 总时长{total_time}分钟")
                
                expected_total_count = 5  # 2+2+1=5
                expected_total_time = 60.0  # 60分钟
                expected_total_interval = expected_total_time / expected_total_count  # 12分钟
                
                if (total_count == expected_total_count and 
                    abs(total_time - expected_total_time) < 1 and
                    abs(total_interval - expected_total_interval) < 1):
                    logger.info("✅ 总计统计正确!")
                else:
                    logger.error(f"❌ 总计统计错误!")
                    logger.error(f"   预期: 次数{expected_total_count}, 时长{expected_total_time}, 间隔{expected_total_interval}")
                    logger.error(f"   实际: 次数{total_count}, 时长{total_time}, 间隔{total_interval}")
            else:
                logger.error("❌ 没有找到总计行!")
                
        else:
            logger.error("❌ 没有返回结果!")
            
    except Exception as e:
        logger.error(f"执行接管统计查询失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_takeover_statistics()
