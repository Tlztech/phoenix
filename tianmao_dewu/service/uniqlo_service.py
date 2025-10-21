import math
import re
import json
import os

from constant import excel
from util import env_util, common_util
from util.excel_util import ExcelUtil
from datetime import datetime


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
        tianmao_value = tianmao_input_group_data_dict.get(dewu_key)
        if any(str(dewu_key) == str(x) for x in tianmao_model_list):
            dewu_model_in_tianmao_list.append(dewu_key)
            for dewu in dewu_value:
                specifications = dewu.get(excel.DEWU_COLUMN_INDEX.get('规格')).split(" ")
                size = None
                for specification in specifications:
                    if size is None:
                        if specification != 'SIZE' and not bool(re.search(r'[\u4e00-\u9fa5]', str(specification))):
                            if common_util.is_number(specification) and str(specification) != str(dewu_key.split("-")[1]):
                                size = specification
                            else:
                                str_matches = re.findall(r'\((.*?)\)', str(specification))
                                size = str_matches[0] if str_matches else specification
                    else:
                        break
                if size == '2XL':
                    size = 'XXL'
                elif size == 'XXXL':
                    size = '3XL'
                elif size == 'XXXXL':
                    size = '4XL'

                dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '没有size匹配到，确认'})

                for tianmao in tianmao_value:
                    if size and ((common_util.is_number(size) and common_util.is_number(
                            tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size'))) and math.isclose(
                        float(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size'))),
                        float(size),
                        rel_tol=1e-9,
                        abs_tol=1e-9
                    )) or tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size')) == size):
                        dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '',
                                     excel.DEWU_COLUMN_INDEX.get('*修改后发货时效（天）'): dewu.get(
                                         excel.DEWU_COLUMN_INDEX.get('发货时效（天）')),
                                     excel.DEWU_COLUMN_INDEX.get('*修改后出价(JPY)'): dewu.get(
                                         excel.DEWU_COLUMN_INDEX.get('我的出价(JPY)')),
                                     excel.DEWU_COLUMN_INDEX.get('*修改后库存'): tianmao.get(
                                         excel.TIANMAO_COLUMN_INDEX.get('quantity'))})
                        if tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('msrp')) > float(dewu.get(
                                excel.DEWU_COLUMN_INDEX.get('预计收入(JPY)')).replace(" ", "").replace(",", "")):
                            dewu.update(
                                {excel.DEWU_COLUMN_INDEX.get(
                                    '结果'): f"tianmao价格>预计收入(JPY),tianmao价格={tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('msrp'))}"})
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
                    tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('结果'): '没有size匹配到，确认'})
        else:
            for dewu in dewu_value:
                dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '没有model匹配到，下架'})
    for tianmao_key, tianmao_value in tianmao_input_group_data_dict.items():
        if tianmao_key in dewu_model_in_tianmao_list:
            continue
        else:
            for tianmao in tianmao_value:
                tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('结果'): '上架'})
    
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
