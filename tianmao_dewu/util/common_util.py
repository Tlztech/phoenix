import pandas as pd
import os
import glob
import re
import math

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

def calculate_bid_price(cost_price, base_multiplier=1.15, round_mode='ceil'):
    """
    根据采购成本计算出价。

    参数:
        cost_price (float): 采购成本
        round_mode (str): 取整模式
            - 'ceil': 向上取整到最近的100 (默认，推荐用于出价)
            - 'round': 四舍五入到最近的100

    返回:
        int: 换算成100的整数倍的出价
    """
    # base_multiplier = 1.15
    raw_price = 0.0

    # ① 采购成本 < 11500
    if cost_price < 11500:
        # 公式: (1.15 * 成本 + 2600) / 0.99
        raw_price = (base_multiplier * cost_price + 2600) / 0.99

    # ② 11500 ≤ 采购成本 ≤ 78500
    elif 11500 <= cost_price <= 78500:
        # 公式: (1.15 * 成本 + 1900) / 0.94
        raw_price = (base_multiplier * cost_price + 1900) / 0.94

    # ③ 采购成本 > 78500
    else:
        # 公式: (1.15 * 成本 + 5930) / 0.99
        raw_price = (base_multiplier * cost_price + 5930) / 0.99

    # 换算成100的整数
    if round_mode == 'ceil':
        # 向上取整逻辑: 先除以100，向上取整，再乘以100
        # 例: 12310 -> 123.1 -> ceil(124) -> 12400
        final_price = math.ceil(raw_price / 100) * 100
    elif round_mode == 'round':
        # 四舍五入逻辑: 先除以100，四舍五入，再乘以100
        # 例: 12340 -> 123.4 -> round(123) -> 12300
        final_price = round(raw_price / 100) * 100
    else:
        raise ValueError("round_mode 必须是 'ceil' 或 'round'")

    return int(final_price)

def normalize_size(val):
    """标准化尺码：去除数字的 .0 后缀，保留字母原样"""
    if isinstance(val, float):
        val = str(val)
    else:
        val = str(val).strip()

    try:
        num = float(val)
        return f"{num:g}"  # 24.0 -> "24", 24.5 -> "24.5"
    except ValueError:
        return val  # "XL" -> "XL"
