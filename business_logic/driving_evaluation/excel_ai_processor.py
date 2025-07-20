"""Excel数据处理与AI处理解耦模块 - 简化版"""
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any, Union
import os
import logging
import sys
import glob
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入AI处理模块
from ai_service.ai_api import ai_process_test_text

# 导入配置管理器
from config_manager import get_config

# 获取日志实例
logger = logging.getLogger(__name__)


class ExcelAIProcessor:
    """Excel数据读取和AI处理的核心处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.config = get_config()
        logger.info("ExcelAIProcessor初始化成功")
    
    def get_latest_excel_file(self) -> Optional[str]:
        """
        获取download目录下最新的子目录，并从中获取"asr_results_*.xlsx"的文件。
        """
        download_dir = self.config.storage.download_dir
    
        if not os.path.exists(download_dir):
            logger.warning(f"下载目录不存在: {download_dir}")
            return None
    
        # 获取所有子目录
        subdirs = [os.path.join(download_dir, d) for d in os.listdir(download_dir) if os.path.isdir(os.path.join(download_dir, d))]
        if not subdirs:
            logger.info("没有找到任何子目录")
            return None
    
        # 按修改时间排序，获取最新的子目录
        latest_subdir = max(subdirs, key=os.path.getmtime)
    
        # 定义搜索模式
        search_pattern = os.path.join(latest_subdir, "asr_results_*.xlsx")
    
        # 获取匹配的Excel文件
        excel_files = glob.glob(search_pattern)
        if not excel_files:
            logger.info(f"最新子目录中没有找到匹配的Excel文件: {latest_subdir}")
            return None
    
        # 获取文件路径
        latest_file = excel_files[0]  # 假设子目录中只有一个匹配文件
    
        # 获取文件修改时间用于日志
        file_modified = os.path.getmtime(latest_file)
        modified_time = datetime.fromtimestamp(file_modified).strftime('%Y-%m-%d %H:%M:%S')
    
        logger.debug(f"找到最新的ASR结果Excel文件: {os.path.basename(latest_file)} (修改时间: {modified_time})")
        return latest_file
    
    def get_task_file(self, task_path: Optional[Union[str, Path]] = None) -> Optional[str]:
        """
        获取指定任务目录下的Excel文件。
        
        Args:
            task_path: 任务目录路径，如果为None则自动获取最新的asr_results文件
        
        Returns:
            Excel文件路径，如果未找到则返回None
        """
        if task_path is None:
            return self.get_latest_excel_file()
        
        download_dir = self.config.storage.download_dir
        task_dir = os.path.join(download_dir, task_path)
        task_abspath = os.path.abspath(task_dir)
        if not os.path.exists(task_abspath):
            logger.warning(f"任务目录不存在: {task_abspath}")
            return None
        # 定义搜索模式
        search_pattern = os.path.join(task_abspath, "asr_results_*.xlsx")
        # 获取匹配的Excel文件
        excel_files = glob.glob(search_pattern)
        if not excel_files:
            logger.info(f"任务目录中没有找到匹配的Excel文件: {task_abspath}")
            return None
        task_file = excel_files[0]
        return task_file

    def process_excel_file(self, task_path: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
        """
        处理Excel文件的主入口方法
        
        Args:
            task_path: 任务目录路径
            
        Returns:
            处理后的数据列表，每个元素包含原始数据和AI处理结果
        """
        try:
            # 如果没有提供文件路径，则自动获取最新文件
            if task_path is not None:
                # file_path = select_excel_file()   待实现，让用户选择待处理的excel文件             
                # file_path = self.get_latest_excel_file()
                task_path = self.get_task_file(task_path)
                if task_path is None:
                    logger.error("没有找到可处理的Excel文件")
                    return []

                # if file_path is None:
                #     logger.error("没有找到可处理的Excel文件")
                #     return []
                # # logger.info(f"自动选择最新文件: {file_path}")
            
            # 解析文件路径
            full_path = self._resolve_file_path(task_path)
            
            # 读取Excel数据
            raw_data = self._read_excel_data(full_path)
            
            if not raw_data:
                logger.warning("没有从Excel文件中读取到有效数据")
                return []
            
            # AI处理数据
            processed_data = self._process_with_ai(raw_data)
            
            logger.info(f"Excel文件处理完成，共处理{len(processed_data)}条数据")
            return processed_data
            
        except Exception as e:
            logger.error(f"处理Excel文件时出错: {e}")
            return []
    
    def _resolve_file_path(self, file_path: Union[str, Path]) -> str:
        """解析文件路径"""
        path = Path(file_path)
        
        # 如果是绝对路径且存在，直接返回
        if path.is_absolute() and path.exists():
            return str(path)
        
        # 如果是相对路径，尝试不同位置
        if not path.is_absolute():
            # 相对于当前工作目录
            cwd_path = Path.cwd() / path
            if cwd_path.exists():
                return str(cwd_path)
            
            # 相对于项目根目录
            project_root = Path(__file__).parent.parent
            project_path = project_root / path
            if project_path.exists():
                return str(project_path)
            
            # 相对于download目录
            download_path = project_root / "download" / path
            if download_path.exists():
                return str(download_path)
        
        raise FileNotFoundError(f"Excel文件不存在: {file_path}")
    
    def _read_excel_data(self, file_path: str) -> List[Dict[str, Any]]:
        """从Excel文件读取数据"""
        try:
            logger.info(f"开始读取Excel文件: {file_path}")
            
            # 读取Excel文件
            df = pd.read_excel(file_path)
            
            # 验证必要的列
            if 'time' not in df.columns or 'result' not in df.columns:
                raise ValueError(f"Excel文件必须包含'time'和'result'列，当前列: {list(df.columns)}")
            
            # 处理数据
            processed_data = []
            for index, row in df.iterrows():
                try:
                    # 处理时间
                    time_value = row['time']
                    if pd.isna(time_value):
                        continue
                    
                    time_obj = pd.to_datetime(time_value)
                    
                    # 处理结果
                    result_value = row['result']
                    if pd.isna(result_value) or not str(result_value).strip():
                        continue
                    
                    result_value = str(result_value).strip()
                    
                    # 创建记录
                    record = {
                        'time': time_obj,
                        'result': result_value,
                        'row_index': index + 1
                    }
                    
                    processed_data.append(record)
                    
                except Exception as e:
                    logger.warning(f"处理第{index + 1}行数据时出错: {e}")
                    continue
            
            logger.info(f"Excel数据读取完成: {len(processed_data)}条有效数据")
            return processed_data
            
        except Exception as e:
            logger.error(f"读取Excel文件时出错: {e}")
            raise
    
    def _process_with_ai(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用AI处理数据"""
        logger.info(f"开始AI处理，共{len(data)}条数据")
        processed_data = []
        success_count = 0
        
        for i, record in enumerate(data):
            try:
                logger.info(f"AI处理进度: {i+1}/{len(data)}")
                
                # 调用AI处理
                ai_result = ai_process_test_text(record['result'])
                
                # 判断处理是否成功
                processing_success = bool(ai_result and ai_result.strip())
                
                if processing_success:
                    success_count += 1
                
                # 创建处理结果
                processed_record = {
                    'time': record['time'],
                    'original_result': record['result'],
                    'ai_processed_result': ai_result,
                    'ai_processing_status': 'success' if processing_success else 'failed',
                    'row_index': record['row_index']
                }
                
                processed_data.append(processed_record)
                
            except Exception as e:
                logger.error(f"AI处理第{i+1}条数据时出错: {e}")
                
                # 处理失败也保留记录
                error_record = {
                    'time': record['time'],
                    'original_result': record['result'],
                    'ai_processed_result': None,
                    'ai_processing_status': 'error',
                    'row_index': record['row_index'],
                    'error_message': str(e)
                }
                
                processed_data.append(error_record)
        
        success_rate = success_count / len(data) * 100 if data else 0
        logger.info(f"AI处理完成: 成功{success_count}/{len(data)}条 ({success_rate:.1f}%)")
        
        return processed_data


# 便捷函数
def process_excel_file(file_path: Optional[Union[str, Path]] = None) -> List[Dict[str, Any]]:
    """
    便捷函数：处理Excel文件
    
    Args:
        file_path: Excel文件路径，如果为None则自动获取最新的asr_results文件
        
    Returns:
        处理后的数据列表
    """
    processor = ExcelAIProcessor()
    return processor.process_excel_file(file_path)

def select_excel_file(initial_dir: str = "./download") -> Optional[str]:
    """
    使用文件选择器打开窗口，让用户选择 Excel 文件。

    :param initial_dir: 初始目录，默认为 "./download"
    :return: 用户选择的文件路径，如果未选择则返回 None
    """
    task_dir = os.path.join("./download", initial_dir)
    try:
        # 确保任务目录存在
        if not os.path.exists(task_dir):
            logger.warning(f"任务目录不存在: {task_dir}")
            return None

        # 使用 tkinter 打开文件选择窗口
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        file_path = filedialog.askopenfilename(
            initialdir=os.path.abspath(task_dir),
            title="选择Excel文件",
            filetypes=[("Excel文件", "*.xlsx *.xls")]
        )

        # 验证用户选择的文件路径
        if not file_path or not os.path.exists(file_path):
            logger.warning("用户未选择有效文件")
            return None

        return file_path
    except Exception as e:
        logger.error(f"打开文件选择窗口时出错: {e}")
        return None
    
if __name__ == "__main__":
    # 测试代码
    import sys
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        print(f"测试处理指定文件: {test_file}")
        
        try:
            results = process_excel_file(test_file)
            print(f"处理完成，共{len(results)}条数据")
            
            # 显示前几条结果
            for i, result in enumerate(results[:3]):
                print(f"记录{i+1}: {result['time']} - 状态: {result['ai_processing_status']}")
                if result['ai_processed_result']:
                    print(f"  AI结果: {result['ai_processed_result'][:100]}...")
                    
        except Exception as e:
            print(f"测试失败: {e}")
    else:
        print("没有指定文件，将自动查找最新的asr_results文件...")
        
        try:
            results = process_excel_file()  # 无参数调用
            if results:
                print(f"处理完成，共{len(results)}条数据")
                
                # 显示前几条结果
                for i, result in enumerate(results[:3]):
                    print(f"记录{i+1}: {result['time']} - 状态: {result['ai_processing_status']}")
                    if result['ai_processed_result']:
                        print(f"  AI结果: {result['ai_processed_result'][:100]}...")
            else:
                print("没有找到可处理的文件或处理失败")
                    
        except Exception as e:
            print(f"自动处理失败: {e}")
        
        print("\n使用方法:")
        print("  python excel_ai_processor.py                    # 自动处理最新的asr_results文件")
        print("  python excel_ai_processor.py <excel_file_path>  # 处理指定文件")
