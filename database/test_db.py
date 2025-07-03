"""
数据库基础设施测试脚本
验证数据库创建、连接和基本操作
"""
import sys
import logging
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.connection import get_db_manager
from database.models import ProcessedRecord

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_creation():
    """测试数据库创建"""
    print("=== 测试数据库创建 ===")
    
    try:
        # 使用测试数据库
        db_manager = get_db_manager('./data/test_voiceapi_flow.db')
        
        # 检查表是否创建成功
        processed_records_info = db_manager.get_table_info('processed_records')
        
        print(f"✅ processed_records 表字段数: {len(processed_records_info)}")
        
        # 显示表结构
        print("\n📋 processed_records 表结构:")
        for field in processed_records_info:
            print(f"  {field['name']}: {field['type']}")
            
        return True
        
    except Exception as e:
        print(f"❌ 数据库创建测试失败: {e}")
        return False

def test_data_insertion():
    """测试数据插入"""
    print("\n=== 测试数据插入 ===")
    
    try:
        db_manager = get_db_manager('./data/test_voiceapi_flow.db')
        
        # 插入测试数据
        test_record = ProcessedRecord(
            timestamp=datetime.now(),
            original_text="这是一个测试语音转录结果",
            comment="测试评论",
            function_type="导航",
            scores={'Mental_Load': 7.5, 'Comfort': 8.0, 'Safety': 6.5},
            rating='avg'
        )
        
        # 插入处理记录
        processed_data = test_record.to_dict()
        processed_insert_query = """
        INSERT INTO processed_records 
        (timestamp, original_text, comment, function_type, mental_load, predictability,
         timely_response, comfort, efficiency, features, safety, rating)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        processed_id = db_manager.execute_insert(
            processed_insert_query,
            (processed_data['timestamp'], processed_data['original_text'], processed_data['comment'],
             processed_data['function_type'], processed_data['mental_load'], processed_data['predictability'],
             processed_data['timely_response'], processed_data['comfort'], processed_data['efficiency'],
             processed_data['features'], processed_data['safety'], processed_data['rating'])
        )
        
        print(f"✅ 插入处理记录成功，ID: {processed_id}")
        
        # 验证数据
        processed_count = db_manager.get_table_count('processed_records')
        
        print(f"✅ processed_records 记录数: {processed_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据插入测试失败: {e}")
        return False

def test_data_query():
    """测试数据查询"""
    print("\n=== 测试数据查询 ===")
    
    try:
        db_manager = get_db_manager('./data/test_voiceapi_flow.db')
        
        # 查询所有记录
        records = db_manager.execute_query("""
            SELECT id, timestamp, original_text, comment, function_type, 
                   mental_load, comfort, safety, rating
            FROM processed_records
            ORDER BY timestamp DESC
        """)
        
        print(f"✅ 查询到 {len(records)} 条记录")
        
        for record in records:
            print(f"  ID: {record['id']}, 时间: {record['timestamp']}")
            print(f"  原文: {record['original_text'][:50]}...")
            print(f"  功能: {record['function_type']}, 评论: {record['comment'][:30]}...")
            print(f"  评分: 压力性={record['mental_load']}, 舒适性={record['comfort']}, 安全性={record['safety']}")
            print(f"  评级: {record['rating']}")
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ 数据查询测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 数据库基础设施测试")
    print("=" * 50)
    
    success = True
    success &= test_database_creation()
    success &= test_data_insertion()
    success &= test_data_query()
    
    if success:
        print("\n🎉 所有测试通过！数据库基础设施就绪")
        
        # 清理测试文件
        test_db_path = Path('./data/test_voiceapi_flow.db')
        if test_db_path.exists():
            test_db_path.unlink()
            print("🧹 测试数据库文件已清理")
    else:
        print("\n❌ 测试失败，请检查错误信息")
        sys.exit(1)
