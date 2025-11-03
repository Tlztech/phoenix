import pandas as pd
import os
import glob
import re

def is_number(s):
    if s is not None:
        try:
            float(s)
            return True
        except ValueError:
            return False
    else:
        return False


def get_sorted_excelfiles(directory='.'):
    """
    获取当前目录下包含"全量预售导出"的Excel文件，并按文件名降序排列
    
    参数:
    directory: 文件所在目录，默认为当前目录
    
    返回:
    排序后的文件列表
    """
    try:
        # 使用glob模式匹配文件
        pattern = os.path.join(directory, '*全量预售导出*.xlsx')
        excel_files = glob.glob(pattern)
        
        if not excel_files:
            print(f"在目录 '{directory}' 中未找到包含'全量预售导出'的Excel文件")
            return []
        
        # print(f"找到 {len(excel_files)} 个匹配的文件:")
        # for file in excel_files:
        #     print(f"  - {os.path.basename(file)}")
        
        # 按文件名降序排列（从大到小）
        sorted_files = sorted(excel_files, key=lambda x: os.path.basename(x), reverse=True)
        
        # print(f"\n按文件名降序排列后的文件列表:")
        # for i, file in enumerate(sorted_files, 1):
        #     print(f"  {i}. {os.path.basename(file)}")
        
        return sorted_files
        
    except Exception as e:
        print(f"处理文件时出错: {e}")
        return []