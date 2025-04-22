import re
import csv
from io import StringIO, BytesIO, TextIOWrapper


def prices_formatter(prices):
    # pattern = r'¥|￥(\d+,\d+|\d+)'
    # match = re.search(pattern, prices)
    # if match:
    #     # 提取匹配的数字部分
    #     number_with_commas = match.group(1)
    #     # number_without_commas = number_with_commas.replace(',', '')
    #     # return number_without_commas
    #     return number_with_commas

    # numbers = re.findall(r'\d+', prices.replace('，', ','))
    # return ''.join(numbers)
    num = int(re.sub(r'[^\d]', '', prices))
    return num


def color_formatter(color, item_code):
    if color and item_code:
        color = color[color.find(item_code)+len(item_code)+1:].strip()
        color = color[:color.find(' ')].strip()
        return color


def deep_key_check(data, keys):
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif isinstance(current, list) and isinstance(key, int) and key < len(current):
            current = current[key]
        else:
            return False
    return True


def convert_sku_to_code(sku):
    return sku.split("-")[0]


def convert_sku_to_code_color(input_str):
    parts = input_str.split('-')
    return '-'.join(parts[:2]) if len(parts) >= 2 else input_str


def transform_dict_to_list(input_data):
    if not input_data:
        return []
    # 获取所有键，假设所有字典的键顺序一致
    keys = list(input_data[0].keys())
    # 构建输出列表，首行为键，之后每行为对应值
    output = [keys]
    for item in input_data:
        row = [item[key] for key in keys]
        output.append(row)
    return output


def generate_excel_friendly_csv(input_data_list):
    # output = StringIO()
    output = BytesIO()
    # writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL,)
    text_wrapper = TextIOWrapper(output, encoding='utf-8', newline='')
    writer = csv.writer(text_wrapper, quoting=csv.QUOTE_MINIMAL)
    writer.writerows(input_data_list)
    text_wrapper.flush()
    output.seek(0)
    return output.getvalue()


def reorder_dict(dict_list, order):
    return [
        {k: d.get(k) for k in order if k in d}
        for d in dict_list
    ]


def deduplicate(original_lst):
    unique_lst = list(set(original_lst))
    return unique_lst
