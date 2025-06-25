import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import os
from ai_models.ai_api import ai_process_test_text 
from toexcel.toexcel import export_to_excel,export_to_excel_sheetn  # 导入 toexcel.py 中的函数
# import threading
# from concurrent.futures import ThreadPoolExecutor, as_completed # 用于并发处理
score_pinyin_dict = {'压力性': 'Mental_Load', '可预测性': 'Predicatabl', '响应性': 'Timely_Response',
    '舒适性': 'Comfort', '效率性': 'Efficiency', '功能性': 'Features', '安全性': 'safety'}

chinese_to_english = {
    '压力性': 'Mental_Load', 
    '可预测性': 'Predicatabl', 
    '响应性': 'Timely_Response',
    '舒适性': 'Comfort', 
    '效率性': 'Efficiency', 
    '功能性': 'Features', 
    '安全性': 'safety'
}
class ExcelDataReader:
    """Excel数据读取器"""
    

    def __init__(self, enable_ai_processing: bool = True):
        self.data = []
        self.enable_ai_processing = enable_ai_processing
        self.processed_data = []  # 存储经过AI处理的数据
        self.formatted_data = []  # 存储格式化后的数据
        # self._processing_lock = threading.Lock()  # 添加锁
        # self._is_processing = False  # 添加处理状态标志

    def read_excel_data(self, file_path: str, file_name: str) -> List[Dict]:
        """
        从Excel文件读取数据
        
        Args:
            file_path: Excel文件路径
            file_name: Excel文件名
            
        Returns:
            包含时间和结果数据的字典列表
        """
        try:
            # 构建完整的文件路径
            full_path = os.path.join(file_path, file_name)
            
            # 检查文件是否存在
            if not os.path.exists(full_path):
                raise FileNotFoundError(f"文件不存在: {full_path}")
            
            # 读取Excel文件
            df = pd.read_excel(full_path)
            
            # 验证列名是否存在
            if 'time' not in df.columns or 'result' not in df.columns:
                raise ValueError("Excel文件必须包含'time'和'result'列")
            
            # 清理数据并转换格式
            processed_data = []
            for index, row in df.iterrows():
                try:
                    # 处理时间数据
                    time_value = row['time']
                    if pd.isna(time_value):
                        continue
                    
                    # 如果时间是字符串，尝试解析
                    if isinstance(time_value, str):
                        time_obj = datetime.strptime(time_value, '%Y-%m-%d %H:%M:%S')
                    else:
                        time_obj = time_value
                    
                    # 处理结果数据
                    result_value = row['result']
                    if pd.isna(result_value):
                        result_value = ""
                    else:
                        result_value = str(result_value).strip()
                    
                    # 创建数据记录
                    record = {
                        'time': time_obj,
                        'result': result_value,
                        'row_index': index + 1  # 记录原始行号（从1开始）
                    }
                    
                    processed_data.append(record)
                    
                except Exception as e:
                    print(f"处理第{index + 1}行数据时出错: {e}")
                    continue
            
            # 存储到实例变量中
            self.data = processed_data
            
            print(f"成功读取{len(processed_data)}条数据")
            
            # 如果启用AI处理，则进行AI文本处理
            if self.enable_ai_processing:
                self._process_with_ai()
            
            return processed_data
            
        except Exception as e:
            print(f"读取Excel文件时出错: {e}")
            return []
    
    def _process_with_ai(self):
        """
        使用AI处理result字段中的文本数据
        """
        print("开始AI文本处理...")
        # 使用锁来防止并发执行
        # with self._processing_lock:
        #     if self._is_processing:
        #         print("AI处理已在进行中，跳过重复调用")
        #         return
            
        #     self._is_processing = True

        self.processed_data = []
        
        for i, record in enumerate(self.data):
            try:
                print(f"处理第{i+1}/{len(self.data)}条数据...")
                
                # 调用AI API处理result文本
                ai_result = ai_process_test_text(record['result'])
                
                # 显示处理进度和结果
                print(f"  原始: {record['result'][:50]}")
                print(f"  AI处理: {ai_result.strip()}")
                
                # 显示处理进度
                print(f"已处理: {i+1}/{len(self.data)} 条数据")
                print("-" * 60)

                # 创建包含AI处理结果的新记录
                processed_record = {
                    'time': record['time'],
                    'original_result': record['result'],
                    'ai_processed_result': ai_result,
                    'row_index': record['row_index'],
                    'processing_status': 'success' if ai_result else 'failed'
                }
                
                self.processed_data.append(processed_record)
                
            except Exception as e:
                print(f"AI处理第{i+1}条数据时出错: {e}")
                # 即使AI处理失败，也保留原始数据
                processed_record = {
                    'time': record['time'],
                    'original_result': record['result'],
                    'ai_processed_result': None,
                    'row_index': record['row_index'],
                    'processing_status': 'error',
                    'error_message': str(e)
                }
                self.processed_data.append(processed_record)
        
        successful_count = len([r for r in self.processed_data if r['processing_status'] == 'success'])
        print(f"AI处理完成，成功处理{successful_count}/{len(self.data)}条数据")
        # 结构化数据
        self.format_data()
    
    def format_data(self):
        """
        将AI处理后的数据格式化为Excel格式
        
        Returns:
            格式化后的数据列表，每个字典包含Excel所需的所有列
        """
        if not self.enable_ai_processing or not self.processed_data:
            print("没有AI处理数据可格式化")
            return []
        
        # 反向映射字典，用于将中文维度转换为英文列名
        # chinese_to_english = {v: k for k, v in score_pinyin_dict.items()}
        
        for record in self.processed_data:
            try:
                # 处理时间格式，确保为 yyyy-MM-dd HH:mm:ss 格式
                time_value = record['time']
                formatted_time = time_value.strftime('%Y-%m-%d %H:%M:%S')
                # 初始化Excel行数据
                excel_row = {
                    'time': formatted_time,
                    'comment': '',
                    'function': '',
                    'Mental_Load': '',
                    'Predicatabl': '',
                    'Timely_Response': '',
                    'Comfort': '',
                    'Efficiency': '',
                    'Features': '',
                    'safety': '',
                    '是否剪辑': '否'  # 默认值
                }
                
                # 如果AI处理成功且有结果
                if record['processing_status'] == 'success' and record['ai_processed_result']:
                    try:
                        # 尝试解析AI返回的JSON字符串
                        import json
                        
                        # 清理AI返回的数据，去除可能的格式问题
                        ai_result = record['ai_processed_result'].strip()
                        
                        # 如果不是标准JSON格式，尝试修复
                        if not ai_result.startswith('{'):
                            # 查找第一个{和最后一个}
                            start = ai_result.find('{')
                            end = ai_result.rfind('}')
                            if start != -1 and end != -1:
                                ai_result = ai_result[start:end+1]
                        
                        # 替换可能的格式问题（如分号结尾改为逗号）
                        ai_result = ai_result.replace('";', '",').replace("';", "',")
                        
                        ai_data = json.loads(ai_result)
                        
                        # 提取基本信息
                        excel_row['comment'] = ai_data.get('comment', '')
                        excel_row['function'] = ai_data.get('function', '')
                        
                        # 获取总分
                        total_score = ai_data.get('score', '')
                        
                        # 初始化所有分数维度为总分
                        score_columns = ['Mental_Load', 'Predicatabl', 'Timely_Response', 
                                    'Comfort', 'Efficiency', 'Features', 'safety']
                        for col in score_columns:
                            excel_row[col] = total_score
                        
                        # 处理具体的中文维度分数
                        for ai_key, ai_value in ai_data.items():
                            print(f"检查AI键: '{ai_key}' -> 值: '{ai_value}'")
                            # 检查是否为中文维度
                            if ai_key in chinese_to_english:
                                english_col = chinese_to_english[ai_key]
                                print(f"找到匹配: '{ai_key}' -> '{english_col}' = '{ai_value}'")
                                if english_col in excel_row:
                                    excel_row[english_col] = ai_value
                                    print(f"成功设置: {english_col} = {ai_value}")
                        
                        # 处理"是否剪辑"字段
                        if '是否剪辑' in ai_data:
                            excel_row['是否剪辑'] = ai_data['是否剪辑']
                        
                    except json.JSONDecodeError as e:
                        print(f"解析AI结果JSON失败: {e}")
                        print(f"原始AI结果: {record['ai_processed_result']}")
                        # JSON解析失败时，仍保留时间信息
                        excel_row['comment'] = record.get('original_result', '')[:100]  # 截取前100个字符作为备用
                        
                    except Exception as e:
                        print(f"处理AI结果时出错: {e}")
                        excel_row['comment'] = record.get('original_result', '')[:100]
                
                else:
                    # AI处理失败或无结果时，使用原始数据
                    excel_row['comment'] = record.get('original_result', '')[:100]
                    if 'error_message' in record:
                        excel_row['function'] = f"处理错误: {record['error_message']}"
                
                self.formatted_data.append(excel_row)
                
            except Exception as e:
                print(f"格式化数据时出错: {e}")
                # 即使出错也要保留基本的时间信息
                error_row = {
                    'time': record.get('time', ''),
                    'comment': f"格式化错误: {str(e)}",
                    'function': '',
                    'Mental_Load': '',
                    'Predicatabl': '',
                    'Timely_Response': '',
                    'Comfort': '',
                    'Efficiency': '',
                    'Features': '',
                    'safety': '',
                    '是否剪辑': '否'
                }
                self.formatted_data.append(error_row)
        
        print(f"format_data: 成功格式化{len(self.formatted_data)}条数据")
        # 计算平均分和评级
        self.calculate_average_and_rating()
        # 输出formatted_data的所有数据
        # for i, row in enumerate(formatted_data):
        #     print(f"Row {i+1}: {row}")
        filename = f"ai_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        export_to_excel(self.formatted_data, filename)
        rating_total_statistics = self.get_total_rating_statistics()
        export_to_excel_sheetn(rating_total_statistics, filename, sheet_name="统计总结果")
        rating_function_statistics = self.get_function_rating_statistics()
        export_to_excel_sheetn(rating_function_statistics, filename, sheet_name="统计各个场景评价")
        get_takeover_statistics = self.get_takeover_statistics()
        export_to_excel_sheetn(get_takeover_statistics, filename, sheet_name="接管统计")

    # 计算平均分和评级
    def calculate_average_and_rating(self):
        """
        为每行数据计算各维度平均分并进行评级
        
            
        Returns:
            添加了avg和mark列的数据列表
        """
        # 需要计算平均分的维度列
        score_columns = ['Mental_Load', 'Predicatabl', 'Timely_Response', 
                        'Comfort', 'Efficiency', 'Features', 'safety']
        
        for row in self.formatted_data:
            try:
                # 收集有效分数
                valid_scores = []
                
                for col in score_columns:
                    score_value = row.get(col, '')
                    
                    # 处理分数值
                    if score_value and str(score_value).strip():
                        try:
                            # 尝试转换为数值
                            score = float(str(score_value).strip())
                            # 验证分数范围（假设1-10分制）
                            if 0 <= score <= 10:
                                valid_scores.append(score)
                            else:
                                print(f"警告: 分数超出范围 {col}={score}")
                        except (ValueError, TypeError):
                            print(f"警告: 无法解析分数 {col}={score_value}")
                            continue
                
                # 计算平均分
                if valid_scores:
                    avg_score = sum(valid_scores) / len(valid_scores)
                    # 保留两位小数
                    avg_score = round(avg_score, 1)
                else:
                    avg_score = 0
                    print(f"警告: 该行没有有效分数数据")
                
                # 根据平均分进行评级
                if avg_score >= 8:
                    rating = "pos"
                elif avg_score >= 7:
                    rating = "avg"
                elif avg_score >= 5:
                    rating = "neg"
                else:
                    rating = "bad"
                
                # 添加新列
                row['平均'] = avg_score
                row['评价'] = rating

                # 输出处理结果
                print(f"时间: {row.get('time', '')}, 有效分数: {valid_scores}, 平均分: {avg_score}, 评级: {rating}")
                
            except Exception as e:
                print(f"计算平均分时出错: {e}")
                # 出错时设置默认值
                row['平均'] = 0
                row['评价'] = "bad"
        

    def get_total_rating_statistics(self) -> List[Dict]:
        """
        统计各评级的数量和比例，生成统计列表
            
        Returns:
            统计结果列表，格式为[{"评级": "pos", "数量": 10, "比例": "25.0%"}, ...]
        """
        if not self.formatted_data:
            return []
        
        # 统计各评级数量
        rating_counts = {"pos": 0, "avg": 0, "neg": 0, "bad": 0}
        total_count = len(self.formatted_data)
        
        for row in self.formatted_data:
            rating = row.get('评价', 'bad')
            if rating in rating_counts:
                rating_counts[rating] += 1
            else:
                rating_counts['bad'] += 1  # 未知评级归为"bad"
        
        # 生成统计列表
        statistics_list = []
        
        for rating_code, count in rating_counts.items():
            percentage = (count / total_count * 100) if total_count > 0 else 0
            statistics_list.append({
                "评级": rating_code,
                "数量": count,
                "比例": f"{percentage:.1f}%"
            })
        
        # 添加总计行
        statistics_list.append({
            "评级": "总计",
            "数量": total_count,
            "比例": "100.0%"
        })
        
        return statistics_list

    def get_function_rating_statistics(self) -> List[Dict]:
        """
        统计不同场景（function）下的各个评级（评价）的数量
        
        Returns:
            统计结果列表，每个字典包含场景和各评级的数量
        """
        if not self.formatted_data:
            return []
        
        # 收集所有场景和评级
        function_rating_stats = {}
        all_ratings = {"pos", "avg", "neg", "bad"}
        
        # 遍历数据，按场景分组统计
        for row in self.formatted_data:
            function = row.get('function', '未知场景').strip()
            if not function:
                function = '未知场景'
            
            rating = row.get('评价', 'bad')
            
            # 初始化场景统计
            if function not in function_rating_stats:
                function_rating_stats[function] = {
                    "pos": 0, "avg": 0, "neg": 0, "bad": 0, "total": 0
                }
            
            # 统计评级数量
            if rating in all_ratings:
                function_rating_stats[function][rating] += 1
            else:
                function_rating_stats[function]["bad"] += 1
            
            function_rating_stats[function]["total"] += 1
        
        # 生成统计结果列表
        statistics_list = []
        
        # 按场景生成统计数据
        for function, stats in function_rating_stats.items():
            for rating_code in ["pos", "avg", "neg", "bad"]:
                count = stats[rating_code]
                total = stats["total"]
                percentage = (count / total * 100) if total > 0 else 0
                
                statistics_list.append({
                    "场景": function,
                    "评级": rating_code,
                    "数量": count,
                    "比例": f"{percentage:.1f}%",
                    "场景总数": total
                })
        
        return statistics_list

    def get_takeover_statistics(self) -> List[Dict]:
        """
        统计接管次数以及平均时间
        
        Returns:
            接管统计结果列表
        """
        if not self.formatted_data:
            return [{"接管类型": "无数据", "接管次数": 0, "平均间隔时间(分钟)": 0}]
        
        # 定义接管类型关键词
        takeover_keywords = {
            "危险接管": ["危险接管", "紧急接管", "安全接管"],
            "车机接管": ["车机接管", "系统接管", "自动接管"],
            "人为接管": ["人为接管", "手动接管", "优化接管"]
        }
        
        # 统计各类接管次数
        takeover_counts = {
            "危险接管": 0,
            "车机接管": 0,
            "人为接管": 0,
            "其他接管": 0
        }
        
        # 记录接管时间点
        takeover_times = {
            "危险接管": [],
            "车机接管": [],
            "人为接管": [],
            "其他接管": []
        }
        
        # 遍历数据统计接管
        for row in self.formatted_data:
            comment = row.get('comment', '').strip()
            time_str = row.get('time', '')
            
            if not comment:
                continue
            
            # 判断接管类型
            takeover_type = None
            for category, keywords in takeover_keywords.items():
                if any(keyword in comment for keyword in keywords):
                    takeover_type = category
                    break
            
            if takeover_type:
                takeover_counts[takeover_type] += 1
                takeover_times[takeover_type].append(time_str)
            else:
                # 检查是否包含"接管"关键词
                if "接管" in comment:
                    takeover_counts["其他接管"] += 1
                    takeover_times["其他接管"].append(time_str)
        
        # 计算总时间范围
        all_times = []
        for row in self.formatted_data:
            time_str = row.get('time', '')
            if time_str:
                all_times.append(time_str)
        
        total_duration_minutes = 0
        if len(all_times) >= 2:
            try:
                # 解析时间字符串
                first_time = datetime.strptime(all_times[0], '%Y-%m-%d %H:%M:%S')
                last_time = datetime.strptime(all_times[-1], '%Y-%m-%d %H:%M:%S')
                
                # 计算总时长（分钟）
                total_duration = last_time - first_time
                total_duration_minutes = total_duration.total_seconds() / 60
                
            except ValueError as e:
                print(f"时间解析错误: {e}")
                total_duration_minutes = 0
        
        # 生成统计结果
        statistics_list = []
        
        for takeover_type, count in takeover_counts.items():
            if count > 0:
                # 计算平均间隔时间
                avg_interval = total_duration_minutes / count if count > 0 and total_duration_minutes > 0 else 0
                
                statistics_list.append({
                    "接管类型": takeover_type,
                    "接管次数": count,
                    "平均间隔时间(分钟)": round(avg_interval, 2),
                    "总时长(分钟)": round(total_duration_minutes, 2)
                })
        
        # 如果没有任何接管记录
        if not statistics_list:
            statistics_list.append({
                "接管类型": "无接管记录",
                "接管次数": 0,
                "平均间隔时间(分钟)": 0,
                "总时长(分钟)": round(total_duration_minutes, 2)
            })
        else:
            # 添加总计行
            total_takeovers = sum(takeover_counts.values())
            overall_avg = total_duration_minutes / total_takeovers if total_takeovers > 0 else 0
            
            statistics_list.append({
                "接管类型": "总计",
                "接管次数": total_takeovers,
                "平均间隔时间(分钟)": round(overall_avg, 2),
                "总时长(分钟)": round(total_duration_minutes, 2)
            })
        
        return statistics_list
    
    def get_data(self) -> List[Dict]:
        """获取原始读取的数据"""
        return self.data
    
    def get_processed_data(self) -> List[Dict]:
        """获取经过AI处理的数据"""
        return self.processed_data if self.enable_ai_processing else self.data
    
    def get_data_count(self) -> int:
        """获取数据条数"""
        return len(self.data)
    
    def get_successful_processed_count(self) -> int:
        """获取成功处理的数据条数"""
        if not self.enable_ai_processing:
            return 0
        return len([r for r in self.processed_data if r['processing_status'] == 'success'])
    
    # def print_sample_data(self, count: int = 5, show_processed: bool = True):
    #     """打印样本数据"""
    #     if show_processed and self.enable_ai_processing and self.processed_data:
    #         data_to_show = self.processed_data
    #         print(f"显示前{min(count, len(data_to_show))}条AI处理后的数据:")
    #         for i, record in enumerate(data_to_show[:count]):
    #             print(f"第{i+1}条:")
    #             print(f"  时间: {record['time']}")
    #             print(f"  原始: {record['original_result']}")
    #             print(f"  AI处理: {record['ai_processed_result']}")
    #             print(f"  状态: {record['processing_status']}")
    #             print("-" * 50)
    #     else:
    #         data_to_show = self.data
    #         if not data_to_show:
    #             print("没有数据可显示")
    #             return
            
    #         print(f"显示前{min(count, len(data_to_show))}条原始数据:")
    #         for i, record in enumerate(data_to_show[:count]):
    #             print(f"第{i+1}条: 时间={record['time']}, 结果={record['result'][:50]}...")
    
    # def print_processing_summary(self):
    #     """打印处理摘要"""
    #     if not self.enable_ai_processing:
    #         print("未启用AI处理")
    #         return
        
    #     total = len(self.data)
    #     successful = self.get_successful_processed_count()
    #     failed = total - successful
        
    #     print("=== AI处理摘要 ===")
    #     print(f"总数据条数: {total}")
    #     print(f"成功处理: {successful}")
    #     print(f"处理失败: {failed}")
    #     print(f"成功率: {successful/total*100:.1f}%" if total > 0 else "0%")


# 开放接口函数
def load_excel_data(file_path: str, file_name: str, enable_ai_processing: bool = True) -> ExcelDataReader:
    """
    开放接口：从指定位置读取Excel文件数据并进行AI处理
    
    Args:
        file_path: Excel文件所在路径
        file_name: Excel文件名
        enable_ai_processing: 是否启用AI处理
        
    Returns:
        ExcelDataReader实例，包含读取和处理的数据
    """
    reader = ExcelDataReader(enable_ai_processing=enable_ai_processing)
    reader.read_excel_data(file_path, file_name)
    return reader


# 使用示例
if __name__ == "__main__":
    # 示例用法
    file_path = r"C:\niiya\tools\AI\voiceapi\voiceapi\download"  # 替换为实际路径
    file_name = "asr_results_2025-06-23_18-09-33.xlsx"  # 替换为实际文件名
    
    # 使用开放接口读取数据并进行AI处理
    reader = load_excel_data(file_path, file_name, enable_ai_processing=True)
    
    # 显示读取结果
    # print(f"共读取到{reader.get_data_count()}条数据")
    
    # 显示处理摘要
    # reader.print_processing_summary()
    
    # 显示样本数据
    # reader.print_sample_data(3, show_processed=True)
    
    # 获取处理后的数据进行后续处理
    # processed_data = reader.get_processed_data()
    # print(f"\n获取到{len(processed_data)}条处理后的数据，等待进一步处理...")
    
    # 后续处理代码...