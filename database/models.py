"""
数据库模型定义
基于第一性原理：存储AI处理的原始结果和解析后的结构化数据
"""
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import logging

logger = logging.getLogger(__name__)

class DatabaseSchema:
    """数据库结构定义"""
    
    # 结构化数据表 - 存储语音识别和AI处理的完整数据
    PROCESSED_RECORDS_TABLE = """
    CREATE TABLE IF NOT EXISTS processed_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- 主键ID，自增
        timestamp DATETIME NOT NULL,                             -- 记录时间戳
        original_text TEXT,                                      -- 语音识别的原始文本
        comment TEXT,                                            -- 用户评论内容
        function_type VARCHAR(50),                               -- 功能场景类型（如："导航变道","超车变道"等）
        mental_load DECIMAL(3,1),                                -- 压力性评分（1-10分）
        predictability DECIMAL(3,1),                             -- 可预测性评分（1-10分）
        timely_response DECIMAL(3,1),                            -- 响应性评分（1-10分）
        comfort DECIMAL(3,1),                                    -- 舒适性评分（1-10分）
        efficiency DECIMAL(3,1),                                 -- 效率性评分（1-10分）
        features DECIMAL(3,1),                                   -- 功能性评分（1-10分）
        safety DECIMAL(3,1),                                     -- 安全性评分（1-10分）
        rating VARCHAR(10),                                      -- 评级等级：pos(好)/avg(中)/neg(差)/bad(很差)
        is_clipped VARCHAR(2),                                   -- 是否剪辑：是/否
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP            -- 记录创建时间
    );
    """
    
    # 索引定义 - 提升查询性能
    INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_processed_records_timestamp ON processed_records(timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_processed_records_rating ON processed_records(rating);",
        "CREATE INDEX IF NOT EXISTS idx_processed_records_function ON processed_records(function_type);",
        "CREATE INDEX IF NOT EXISTS idx_activity_sessions_timestamp ON activity_sessions(timestamp);",
        "CREATE INDEX IF NOT EXISTS idx_activity_sessions_status ON activity_sessions(status);",
    ]
    
    # 活动状态表 - 存储测试活动的开始和结束状态
    ACTIVITY_SESSIONS_TABLE = """
    CREATE TABLE IF NOT EXISTS activity_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,                    -- 主键ID，自增
        timestamp DATETIME NOT NULL,                             -- 状态变更时间戳
        original_text TEXT,                                      -- 语音识别的原始文本
        status VARCHAR(10) NOT NULL,                             -- 活动状态：start/end
        comment TEXT,                                            -- 状态描述
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP            -- 记录创建时间
    );
    """

class ProcessedRecord:
    """AI处理的完整数据模型"""
    
    def __init__(self,
                 timestamp: datetime,
                 original_text: str = '',
                 comment: str = '',
                 function_type: str = '',
                 scores: Dict[str, float] = None,
                 rating: str = 'bad'):
        self.timestamp = timestamp
        self.original_text = original_text
        self.comment = comment
        self.function_type = function_type
        self.scores = scores or {}
        self.rating = rating
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'timestamp': self.timestamp.isoformat(),
            'original_text': self.original_text,
            'comment': self.comment,
            'function_type': self.function_type,
            'rating': self.rating,
            'is_clipped': getattr(self, 'is_clipped', False)
        }
        # 添加各个评分维度
        result.update({
            'mental_load': self.scores.get('Mental_Load', 0),
            'predictability': self.scores.get('Predictable', 0),
            'timely_response': self.scores.get('Timely_Response', 0),
            'comfort': self.scores.get('Comfort', 0),
            'efficiency': self.scores.get('Efficiency', 0),
            'features': self.scores.get('Features', 0),
            'safety': self.scores.get('Safety', 0)
        })
        return result
