import math
from datetime import datetime

import pandas as pd
import os

from constant import excel
from dict.size_dict import onitsukatiger_parse_specs_optimized
from util import common_util, env_util
from util.common_util import calculate_bid_price, normalize_size
from util.excel_util import ExcelUtil


def detect_gender_cn(product_name):
    if not product_name:
        return '男款'
    name_str = str(product_name)
    if '男女同款' in name_str:
        return '男款'
    if '男' in name_str:
        return '男款'
    if '女' in name_str:
        return '女款'
    return '男款'


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

                size_word = None

                # 处理规格列
                results = onitsukatiger_parse_specs_optimized(spec_value, detect_gender_cn(
                    dewu.get(excel.DEWU_COLUMN_INDEX.get('商品名称'))))
                if results:
                    size_word = results.get('Size')
                else:
                    size_word = 'ONE SIZE'
                dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '没有匹配到天猫的规格(颜色尺码)，下架'})

                for tianmao in tianmao_value:
                    size = normalize_size(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size')))
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
