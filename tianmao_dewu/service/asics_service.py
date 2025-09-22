import re
import math
import pandas as pd

from constant import excel
from dict import color_dict, size_dict
from util import env_util, common_util
from util.excel_util import ExcelUtil


def service():
    # 读取Excel数据
    tianmao_input = ExcelUtil(env_util.get_env('EXCEL_INPUT_FILE_TIANMAO'))
    tianmao_input.load_data([value for key, value in excel.TIANMAO_COLUMN_INDEX.items() if key != '结果'], 1)
    dewu_input = ExcelUtil(env_util.get_env('EXCEL_INPUT_FILE_DEWU'))
    dewu_input.load_data([value for key, value in excel.DEWU_COLUMN_INDEX.items() if key != '结果'], 3)
    tianmao_input_group_data_dict = tianmao_input.get_group_by_column(excel.TIANMAO_COLUMN_INDEX.get('model'))
    dewu_input_group_data_dict = dewu_input.get_group_by_column(excel.DEWU_COLUMN_INDEX.get('货号'))
    tianmao_model_list = list(tianmao_input_group_data_dict.keys())
    dewu_model_in_tianmao_list = []
    for dewu_key, dewu_value in dewu_input_group_data_dict.items():
        dewu_formatted_model = dewu_key.replace('-', '.')
        dewu_formatted_model = dewu_formatted_model if '.' in dewu_formatted_model else dewu_formatted_model[
                                                                                        :8] + "." + dewu_formatted_model[
                                                                                                    8:]
        tianmao_value = tianmao_input_group_data_dict.get(dewu_formatted_model)
        if dewu_formatted_model in tianmao_model_list:
            dewu_model_in_tianmao_list.append(dewu_formatted_model)
            for dewu in dewu_value:
                specifications = dewu.get(excel.DEWU_COLUMN_INDEX.get('规格')).split(" ")
                jp_eu = None
                size = None
                for specification in specifications:
                    if jp_eu is None:
                        jp_eu = specification if specification in ['JP', 'EU'] else None
                    if size is None:
                        size = specification if common_util.is_number(specification) or specification in ['SS', 'LL', '3L', '4L'] else None
                        if size and common_util.is_number(size):
                            size = float(size)
                if (jp_eu is None or jp_eu == 'EU') and size:
                    size = size_dict.asics_size_convert(size)
                dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '没有color size匹配到，确认'})
                for tianmao in tianmao_value:
                    if (common_util.is_number(size) and common_util.is_number(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size'))) and math.isclose(
                            float(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size'))),
                            size,
                            rel_tol=1e-9,
                            abs_tol=1e-9
                    )) or tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size')) == size:
                        dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '',
                                     excel.DEWU_COLUMN_INDEX.get('*修改后发货时效（天）'): dewu.get(
                                         excel.DEWU_COLUMN_INDEX.get('发货时效（天）')),
                                     excel.DEWU_COLUMN_INDEX.get('*修改后出价(JPY)'): dewu.get(
                                         excel.DEWU_COLUMN_INDEX.get('我的出价(JPY)')),
                                     excel.DEWU_COLUMN_INDEX.get('*修改后库存'): tianmao.get(
                                         excel.TIANMAO_COLUMN_INDEX.get('quantity'))})
                        tianmao_pice = tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('discounted_price')) if not pd.isna(tianmao.get(
                            excel.TIANMAO_COLUMN_INDEX.get('discounted_price'))) else tianmao.get(
                            excel.TIANMAO_COLUMN_INDEX.get('msrp'))
                        if int(tianmao_pice.replace(',', '')) > int(dewu.get(excel.DEWU_COLUMN_INDEX.get('预计收入(JPY)'))):
                            dewu.update(
                                {excel.DEWU_COLUMN_INDEX.get(
                                    '结果'): f"tianmao价>预计收入(JPY),tianmao价={tianmao_pice}"})
                        if int(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('quantity'))) == 0:
                            if dewu.get(excel.DEWU_COLUMN_INDEX.get('结果')):
                                dewu.update({excel.DEWU_COLUMN_INDEX.get(
                                    '结果'): f"{dewu.get(excel.DEWU_COLUMN_INDEX.get('结果'))}\n没有库存，下架"})
                            else:
                                dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '没有库存，下架'})
                        tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('结果'): '匹配到'})
                        break
            for tianmao in tianmao_value:
                if tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('结果')) is None:
                    tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('结果'): '没有color size匹配到，确认'})
        else:
            for dewu in dewu_value:
                dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '没有model匹配到，下架'})
    for tianmao_key, tianmao_value in tianmao_input_group_data_dict.items():
        if tianmao_key in dewu_model_in_tianmao_list:
            continue
        else:
            for tianmao in tianmao_value:
                tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('结果'): '上架'})
    dewu_output_data = [item for sublist in dewu_input_group_data_dict.values() for item in sublist]
    dewu_output = ExcelUtil(env_util.get_env('EXCEL_OUTPUT_FILE_DEWU'))
    dewu_output.write_excel(
        [{excel.DEWU_COLUMN_REVERSE_INDEX.get(k, k): (
            str(v) if k == excel.DEWU_COLUMN_INDEX.get('出价ID') or k == excel.DEWU_COLUMN_INDEX.get(
                'SKU ID') or k == excel.DEWU_COLUMN_INDEX.get('条形码') else v) for
            k, v in d.items()} for d in
            dewu_output_data])
    tiammao_output_data = [item for sublist in tianmao_input_group_data_dict.values() for item in sublist]
    # print(json.dumps(tiammao_output_data, indent=4,
    #                  ensure_ascii=False))
    tianmao_output = ExcelUtil(env_util.get_env('EXCEL_OUTPUT_FILE_TIANMAO'))
    tianmao_output.write_excel(
        [{excel.TIANMAO_COLUMN_REVERSE_INDEX.get(k, k): v for
          k, v in d.items()} for d in
         tiammao_output_data])
    return
