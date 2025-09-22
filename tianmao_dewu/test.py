import sys
import os

sys.path.append(os.path.abspath('.'))

import re
from constant import excel
from util import excel_util
from dict import size_dict, color_dict


eu = excel_util.ExcelUtil('dewu.xlsx')
eu.load_data([value for key, value in excel.DEWU_COLUMN_INDEX.items() if key != '结果'], 3)
print(eu.get_group_by_column(8))
# print(size_dict.montbell_size_convert("XXL-"))
# print(color_dict.montbell_color_convert("沙土棕"))
color_size_list = "LBL浅蓝色 XL".split(" ")
print(color_size_list)
colors = None
size = None
for color_size in color_size_list:
    if colors is None:
        colors = color_dict.montbell_color_convert(color_size)
        print(f"colors:{colors}")
    if size is None:
        size = size_dict.montbell_size_convert(color_size)
        print(f"size:{size}")
print(((colors and 'BK' in colors) and ('L' == size)))

specifications = '黑色 EU 43.5'.split(' ')
for specification in specifications:
    print(specification)
    if isinstance(specification, (int, float)):
        print(f"number:{specification}")
print(float('43.0') == int('43'))
