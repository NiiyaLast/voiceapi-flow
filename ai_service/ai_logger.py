"""
AI处理日志模块
专门负责记录所有AI处理的输入和输出日志
"""
import os
import logging
from datetime import datetime
from typing import Optional, Any

# 获取日志实例
logger = logging.getLogger(__name__)

class AIProcessLogger:
    """AI处理日志记录器"""
    
    def __init__(self):
        self.log_dir = self._get_log_directory()
        self.current_log_file = None
        self.session_start_time = None
        self._setup_log_file()
    
    def _get_log_directory(self) -> str:
        """获取日志目录路径"""
        # 获取当前文件所在目录（ai_service目录）
        current_dir = os.path.dirname(os.path.abspath(__file__))
        log_dir = os.path.join(current_dir, "ai_process_logs")
        
        # 确保日志目录存在
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            logger.info(f"创建AI处理日志目录: {log_dir}")
        
        return log_dir
    
    def _setup_log_file(self):
        """设置当前的日志文件"""
        try:
            # 生成日志文件名（格式：ai_process_年月日_时分秒.log）
            self.session_start_time = datetime.now()
            timestamp = self.session_start_time.strftime("%Y%m%d_%H%M%S")
            log_filename = f"ai_process_{timestamp}.log"
            self.current_log_file = os.path.join(self.log_dir, log_filename)
            
            # 写入日志文件头部信息
            with open(self.current_log_file, 'w', encoding='utf-8') as f:
                f.write(f"AI处理日志 - 开始时间: {self.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
            
            logger.info(f"AI处理日志文件已创建: {self.current_log_file}")
            
        except Exception as e:
            logger.error(f"创建AI处理日志文件失败: {e}")
            self.current_log_file = None
    
    def log_ai_process(self, 
                      original_text: str, 
                      ai_result: Optional[str], 
                      model_name: str = "unknown",
                      processing_time_ms: float = 0,
                      status: str = "success",
                      error_message: str = None):
        """
        记录AI处理过程
        
        Args:
            original_text: 原始输入文本
            ai_result: AI处理结果
            model_name: 使用的AI模型名称
            processing_time_ms: 处理耗时（毫秒）
            status: 处理状态 (success/failed/error)
            error_message: 错误信息（如果有）
        """
        if not self.current_log_file:
            return
        
        try:
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                timestamp = datetime.now().strftime('%H:%M:%S')
                
                # 基本信息
                f.write(f"[{timestamp}] AI处理记录 - 状态: {status}\n")
                f.write(f"模型: {model_name}\n")
                f.write(f"耗时: {processing_time_ms:.1f}ms\n")
                
                # 原始输入（限制长度避免日志过大）
                original_preview = original_text[:100] + '...' if len(original_text) > 100 else original_text
                f.write(f"原始输入: {original_preview}\n")
                
                # AI处理结果
                if ai_result:
                    result_preview = ai_result.strip()[:200] + '...' if len(ai_result.strip()) > 200 else ai_result.strip()
                    f.write(f"AI处理结果: {result_preview}\n")
                else:
                    f.write("AI处理结果: None\n")
                
                # 错误信息（如果有）
                if error_message:
                    f.write(f"错误信息: {error_message}\n")
                
                f.write("-" * 50 + "\n\n")
                
        except Exception as e:
            logger.error(f"写入AI处理日志失败: {e}")
    
    def log_batch_summary(self, total_count: int, success_count: int, failed_count: int):
        """
        记录批量处理摘要
        
        Args:
            total_count: 总处理数量
            success_count: 成功数量
            failed_count: 失败数量
        """
        if not self.current_log_file:
            return
        
        try:
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "=" * 60 + "\n")
                f.write(f"批量处理摘要 - 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"总共处理: {total_count}条数据\n")
                f.write(f"成功处理: {success_count}条数据\n")
                f.write(f"失败处理: {failed_count}条数据\n")
                f.write(f"成功率: {(success_count/total_count*100):.1f}%\n" if total_count > 0 else "成功率: 0%\n")
                f.write("=" * 60 + "\n")
        except Exception as e:
            logger.error(f"写入批量处理摘要失败: {e}")
    
    def close_log_session(self):
        """关闭当前日志会话"""
        if not self.current_log_file or not self.session_start_time:
            return
        
        try:
            session_duration = datetime.now() - self.session_start_time
            with open(self.current_log_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "=" * 60 + "\n")
                f.write(f"日志会话结束 - 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"会话持续时间: {session_duration}\n")
                f.write("=" * 60 + "\n")
        except Exception as e:
            logger.error(f"关闭日志会话失败: {e}")

# 全局日志实例
_ai_logger = None

def get_ai_logger() -> AIProcessLogger:
    """获取全局AI处理日志实例"""
    global _ai_logger
    if _ai_logger is None:
        _ai_logger = AIProcessLogger()
    return _ai_logger

def log_ai_process(original_text: str, 
                  ai_result: Optional[str], 
                  model_name: str = "unknown",
                  processing_time_ms: float = 0,
                  status: str = "success",
                  error_message: str = None):
    """
    便捷函数：记录AI处理过程
    """
    logger_instance = get_ai_logger()
    logger_instance.log_ai_process(
        original_text=original_text,
        ai_result=ai_result, 
        model_name=model_name,
        processing_time_ms=processing_time_ms,
        status=status,
        error_message=error_message
    )

def log_batch_summary(total_count: int, success_count: int, failed_count: int):
    """
    便捷函数：记录批量处理摘要
    """
    logger_instance = get_ai_logger()
    logger_instance.log_batch_summary(total_count, success_count, failed_count)

def close_ai_log_session():
    """
    便捷函数：关闭AI日志会话
    """
    global _ai_logger
    if _ai_logger:
        _ai_logger.close_log_session()
        _ai_logger = None
