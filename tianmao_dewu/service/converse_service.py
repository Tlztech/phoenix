import math
from datetime import datetime

import pandas as pd
import re
import json
import os

from constant import excel
from dict.size_dict import converse_eu_to_jp
from util import env_util, common_util
from util.common_util import calculate_bid_price, normalize_size
from util.excel_util import ExcelUtil


def parse_tianmao_size(raw):
    # 空值处理
    if pd.isna(raw):
        return raw

    raw_str = str(raw).strip()

    # 处理 S(23.0-25.0) 或 S(23.0-24.0cm) 格式
    bracket_match = re.match(r'^([A-Za-z]+)\(.+?cm?\)$', raw_str)

    if bracket_match:
        letter_code = bracket_match.group(1).upper() # 提取字母并转大写
        return {"raw": letter_code}

    # 正则匹配：以数字开头（可能包含小数点），后跟括号内的数字+cm
    # 例如：10.5(29.0cm) -> group1=10.5, group2=29.0
    # 注意：这里不匹配前面带非数字前缀的情况（如 "1.10.5..."），只匹配纯粹的 "数字(数字cm)"
    match = re.match(r'^(\d+\.?\d*)\((\d+\.?\d*)cm\)$', raw_str)

    if match:
        us_code = match.group(1)
        jp_code = match.group(2)
        return {"raw": None,"US": us_code, "JP": jp_code}
    else:
        # 不符合 "数字(数字cm)" 格式的，原样返回
        return {"raw":raw_str}

def parse_dewu_size(raw_str):
    if pd.isna(raw_str):
        return {"raw": "ONE"}

    raw_str = str(raw_str).strip()

    # 情况 5 & 4: 处理 "SIZE S", "SIZE M", "SIZE L", "SIZE XL", "SIZE O" 等
    # 匹配 SIZE 后跟任意字符，提取字母部分
    size_match = re.search(r'SIZE\s*([SMLXO]+)', raw_str, re.IGNORECASE)
    if size_match:
        size_code = size_match.group(1).upper()
        # 得物通常不支持 "O" 码，如果是 "O" 可能代表 "ONE SIZE"，按需求返回 raw:O 或统一处理
        # 根据需求第5点，直接返回提取到的字母
        return {"raw": size_code}

    # 情况 2: 处理 "JP 24.5 (EU 38)" 或 "JP 22 黑色" (只要包含JP和括号内的EU)
    jp_eu_match = re.search(r'JP\s*([0-9]+\.?[0-9]*)[^0-9]*\(EU\s*([0-9]+\.?[0-9]*)', raw_str, re.IGNORECASE)
    if jp_eu_match:
        jp_val = jp_eu_match.group(1)
        eu_val = jp_eu_match.group(2)
        result = {"JP": jp_val, "EU": eu_val}
        return result

    # 情况 1: 处理 "JP 30" 或 "JP 27.5"
    # 必须是 JP 开头或者包含 JP，后面跟数字
    jp_match = re.search(r'JP\s*([0-9]+\.?[0-9]*)', raw_str, re.IGNORECASE)
    if jp_match:
        jp_val = jp_match.group(1)
        result = {"JP": jp_val}
        return result

    # 情况 1: 处理 "EU 30" 或 "EU 27.5"
    # 必须是 EU 开头或者包含 EU，后面跟数字
    eu_match = re.search(r'EU\s*([0-9]+\.?[0-9]*)', raw_str, re.IGNORECASE)
    if eu_match:
        eu_val = eu_match.group(1)
        result = {"EU": eu_val}
        return result

    # 情况 3: 处理 "27-29" 或 "19-21" (纯数字范围)
    range_match = re.search(r'([0-9]+\.?[0-9]*\s*-\s*[0-9]+\.?[0-9]*)', raw_str)
    if range_match:
        range_val = range_match.group(1).replace(" ", "") # 去除中间可能存在的空格
        return {"raw": range_val}

    # 情况 3 变体: 处理 "SIZE 27-29" 或 "SIZE 19-21"
    size_range_match = re.search(r'SIZE\s*([0-9]+\.?[0-9]*\s*-\s*[0-9]+\.?[0-9]*)', raw_str, re.IGNORECASE)
    if size_range_match:
        range_val = size_range_match.group(1).replace(" ", "")
        return {"raw": range_val}

    # 情况 6: 以上都不符合
    return {"raw": "ONE"}

def service():
    # 读取Excel数据
    tianmao_input = ExcelUtil(env_util.get_env('EXCEL_INPUT_FILE_TIANMAO'))
    tianmao_input.load_data([value for key, value in excel.TIANMAO_COLUMN_INDEX.items() if
                             key != '结果' and key != '预计出价' and key != 'SKU ID'], 1)

    # 读取排序后的第一个得物文件
    dewu_input = ExcelUtil(common_util.get_sorted_excelfiles('.')[0])
    dewu_input.load_data([value for key, value in excel.DEWU_COLUMN_INDEX.items() if
                          key != '结果' and key != '得物原价格' and key != '预计出价'], 3)

    tianmao_input_group_data_dict = tianmao_input.get_group_by_column(excel.TIANMAO_COLUMN_INDEX.get('model'))
    dewu_input_group_data_dict = dewu_input.get_group_by_column(excel.DEWU_COLUMN_INDEX.get('货号'))
    tianmao_model_list = list(tianmao_input_group_data_dict.keys())
    dewu_model_in_tianmao_list = []

    for dewu_key, dewu_value in dewu_input_group_data_dict.items():
        tianmao_value = tianmao_input_group_data_dict.get(dewu_key)
        if any(str(dewu_key) == str(x) for x in tianmao_model_list):
            dewu_model_in_tianmao_list.append(dewu_key)
            for dewu in dewu_value:
                spec_value = dewu.get(excel.DEWU_COLUMN_INDEX.get('规格')).strip()


                # 处理规格列
                size_word = parse_dewu_size(spec_value)
                if size_word.get('JP'):
                    if size_word.get('JP') == '24.5':
                        size_word = normalize_size(size_word.get('EU'))
                    else:
                        size_word = normalize_size(size_word.get('JP'))
                elif size_word.get('EU'):
                    if size_word.get('EU') == '38' or size_word.get('EU') == '39':
                        size_word = size_word.get('EU')
                    else:
                        size_word = normalize_size(converse_eu_to_jp(size_word.get('EU')))
                else:
                    size_word = normalize_size(size_word.get('raw'))

                dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '没有匹配到天猫的规格(颜色尺码)，下架'})

                for tianmao in tianmao_value:
                    size = parse_tianmao_size(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size')))
                    if size.get('JP'):
                        if size.get('JP') == '24.5':
                            if size.get('US') == '5.5':
                                size = '38'
                            else:
                                size = '39'
                        else:
                            size = normalize_size(size.get('JP'))
                    else:
                        size = size.get('raw')

                    if size == size_word:
                        dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '',
                                     excel.DEWU_COLUMN_INDEX.get('*修改后发货时效（天）'): dewu.get(
                                         excel.DEWU_COLUMN_INDEX.get('发货时效（天）')),
                                     excel.DEWU_COLUMN_INDEX.get('*修改后出价(JPY)'): dewu.get(
                                         excel.DEWU_COLUMN_INDEX.get('我的出价(JPY)')),
                                     excel.DEWU_COLUMN_INDEX.get('*修改后库存'): tianmao.get(
                                         excel.TIANMAO_COLUMN_INDEX.get('quantity'))})
                        tianmao.update(
                            {excel.TIANMAO_COLUMN_INDEX.get('SKU ID'): dewu.get(excel.DEWU_COLUMN_INDEX.get('SKU ID'))})
                        # msrp 不等于 采购成本(JPY)
                        if pd.isna(dewu.get(excel.DEWU_COLUMN_INDEX.get('采购成本(JPY)'))) or not dewu.get(
                                excel.DEWU_COLUMN_INDEX.get('采购成本(JPY)')):
                            dewu.update(
                                {excel.DEWU_COLUMN_INDEX.get(
                                    '结果'): f"天猫价格和采购成本(JPY)不一致，已更新O列"})
                            dewu.update({
                                excel.DEWU_COLUMN_INDEX.get('采购成本(JPY)'):
                                    round(float(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('msrp'))))})
                        elif round(float(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('msrp')))) != round(
                                float(str(dewu.get(
                                    excel.DEWU_COLUMN_INDEX.get('采购成本(JPY)'))).replace(" ", "").replace(",",
                                                                                                            ""))):
                            dewu.update(
                                {excel.DEWU_COLUMN_INDEX.get(
                                    '结果'): f"天猫价格和采购成本(JPY)不一致，已更新O列"})
                            dewu.update(
                                {excel.DEWU_COLUMN_INDEX.get('得物原价格'):
                                    round(float(
                                        str(dewu.get(excel.DEWU_COLUMN_INDEX.get('采购成本(JPY)'))).replace(" ",
                                                                                                            "").replace(
                                            ",", "")))})
                            dewu.update({
                                excel.DEWU_COLUMN_INDEX.get('采购成本(JPY)'):
                                    round(float(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('msrp'))))})
                        if int(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('quantity'))) == 0:
                            if dewu.get(excel.DEWU_COLUMN_INDEX.get('结果')):
                                dewu.update({excel.DEWU_COLUMN_INDEX.get(
                                    '结果'): f"{dewu.get(excel.DEWU_COLUMN_INDEX.get('结果'))}\n没有库存，下架"})
                            else:
                                dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '没有库存，下架'})
                        tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('结果'): '匹配到'})
                        cost_value = dewu.get(excel.DEWU_COLUMN_INDEX.get('采购成本(JPY)'))
                        if cost_value is not None and cost_value != '' and cost_value != '-' and isinstance(cost_value,
                                                                                                            (int,
                                                                                                             float)) and not math.isnan(
                            cost_value):
                            dewu.update({excel.DEWU_COLUMN_INDEX.get('预计出价'): calculate_bid_price(cost_value)})
                        break
            for tianmao in tianmao_value:
                if tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('结果')) is None:
                    if int(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('quantity'))) > 0:
                        tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('结果'): '该货号没有规格匹配到，得物上架'})
                    else:
                        tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('结果'): '无需处理'})
                discounted_value = tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('discounted_price'))
                msrp_value = tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('msrp'))
                if discounted_value is not None and discounted_value != '' and discounted_value != '-' and isinstance(
                        discounted_value, (int, float)) and not math.isnan(discounted_value):
                    tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('预计出价'): calculate_bid_price(discounted_value)})
                elif msrp_value is not None and msrp_value != '' and msrp_value != '-' and isinstance(msrp_value, (
                        int, float)) and not math.isnan(msrp_value):
                    tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('预计出价'): calculate_bid_price(msrp_value)})
        else:
            for dewu in dewu_value:
                dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '没有model匹配到，下架'})
    for tianmao_key, tianmao_value in tianmao_input_group_data_dict.items():
        if tianmao_key in dewu_model_in_tianmao_list:
            continue
        else:
            for tianmao in tianmao_value:
                discounted_value = tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('discounted_price'))
                msrp_value = tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('msrp'))
                if discounted_value is not None and discounted_value != '' and discounted_value != '-' and isinstance(
                        discounted_value, (int, float)) and not math.isnan(discounted_value):
                    tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('预计出价'): calculate_bid_price(discounted_value)})
                elif msrp_value is not None and msrp_value != '' and msrp_value != '-' and isinstance(msrp_value, (
                        int, float)) and not math.isnan(msrp_value):
                    tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('预计出价'): calculate_bid_price(msrp_value)})
                if int(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('quantity'))) > 0:
                    tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('结果'): '上架'})
                else:
                    tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('结果'): '无需处理'})

    # 获取当前日期时间
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    # 获取品牌
    brand_name = env_util.get_env('service_module').split(".")[1].split("_")[0]

    dewu_output_filename = env_util.get_env('EXCEL_OUTPUT_FILE_DEWU')
    # 处理得物文件名
    dewu_base_name = os.path.splitext(dewu_output_filename)[0]
    dewu_extension = os.path.splitext(dewu_output_filename)[1]

    tianmao_output_filename = env_util.get_env('EXCEL_OUTPUT_FILE_TIANMAO')
    # 处理天猫文件名
    tianmao_base_name = os.path.splitext(tianmao_output_filename)[0]
    tianmao_extension = os.path.splitext(tianmao_output_filename)[1]

    dewu_output_data = [item for sublist in dewu_input_group_data_dict.values() for item in sublist]
    dewu_output = ExcelUtil(f"{dewu_base_name}_{brand_name}_{timestamp}{dewu_extension}")
    dewu_output.write_excel(
        [{excel.DEWU_COLUMN_REVERSE_INDEX.get(k, k): (
            str(v) if k == excel.DEWU_COLUMN_INDEX.get('出价ID') or k == excel.DEWU_COLUMN_INDEX.get(
                'SKU ID') or k == excel.DEWU_COLUMN_INDEX.get('条形码') else v) for
            k, v in d.items()} for d in
            dewu_output_data])
    tiammao_output_data = [item for sublist in tianmao_input_group_data_dict.values() for item in sublist]
    # print(json.dumps(tiammao_output_data, indent=4,
    #                  ensure_ascii=False))
    tianmao_output = ExcelUtil(f"{tianmao_base_name}_{brand_name}_{timestamp}{tianmao_extension}")
    tianmao_output.write_excel(
        [{excel.TIANMAO_COLUMN_REVERSE_INDEX.get(k, k): v for
          k, v in d.items()} for d in
         tiammao_output_data])
    return
