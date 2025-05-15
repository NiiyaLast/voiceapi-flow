import pandas as pd
import os

def export_to_excel(results, filename):
    """
    将识别结果导出为 Excel 文件。

    :param results: 包含识别结果的列表，每个元素是一个字典，格式为 {"time": 时间, "result": 结果}
    :param filename: 导出的 Excel 文件名
    """
  
    output_dir = "./download"
    os.makedirs(output_dir, exist_ok=True)

    # 拼接完整路径
    filepath = os.path.join(output_dir, filename)

    # 将结果转换为 pandas DataFrame
    df = pd.DataFrame(results)

    # 导出为 Excel 文件
    df.to_excel(filepath, index=False)

    print(f"Results exported to {filepath}")