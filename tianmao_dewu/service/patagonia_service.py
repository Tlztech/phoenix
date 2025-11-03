import re
import os
import pandas as pd

from constant import excel
from dict import color_dict, size_dict
from util import env_util, common_util
from util.excel_util import ExcelUtil
from datetime import datetime


def service():
    # 读取Excel数据
    tianmao_input = ExcelUtil(env_util.get_env('EXCEL_INPUT_FILE_TIANMAO'))
    tianmao_input.load_data([value for key, value in excel.TIANMAO_COLUMN_INDEX.items() if key != '结果'], 1)
    
    # 读取排序后的第一个得物文件
    dewu_input = ExcelUtil(common_util.get_sorted_excelfiles('.')[0])
    dewu_input.load_data([value for key, value in excel.DEWU_COLUMN_INDEX.items() if key != '结果'], 3)
    
    tianmao_input_group_data_dict = tianmao_input.get_group_by_column(excel.TIANMAO_COLUMN_INDEX.get('model'))
    dewu_input_group_data_dict = dewu_input.get_group_by_column(excel.DEWU_COLUMN_INDEX.get('货号'))
    tianmao_model_list = list(tianmao_input_group_data_dict.keys())
    dewu_model_in_tianmao_list = []
    
    for dewu_key, dewu_value in dewu_input_group_data_dict.items():
        color_value = None
        if isinstance(dewu_key, str):
            # 1. 提取数字部分作为model
            dewu_formatted_model = int(re.findall(r'\d+', dewu_key)[0])
            # print(f"货号 '{dewu_key}' -> model: '{dewu_formatted_model}'")
            
            # 2. 提取英文字母部分作为color
            english_match = re.findall(r'[A-Za-z]+', dewu_key)
            if english_match:
                color_value = ''.join(english_match)
                # print(f"货号 '{dewu_key}' -> color: '{color_value}'")
        else:
            dewu_formatted_model = dewu_key

        tianmao_value = tianmao_input_group_data_dict.get(dewu_formatted_model)
        
        if dewu_formatted_model in tianmao_model_list:
            dewu_model_in_tianmao_list.append(dewu_formatted_model)
            for dewu in dewu_value:
                
                spec_value = dewu.get(excel.DEWU_COLUMN_INDEX.get('规格')).strip()
                # print(f"原始规格数据: '{spec_value}'")
        
                # 3. 去掉非英语字母和数字的数据（中文以及/符号），数据原有的空格保留
                temp_value = re.sub(r'[^A-Za-z0-9\s]', '', spec_value)
                temp_value = re.sub(r'\s+', ' ', temp_value).strip()
                # print(f"处理后temp数据: '{temp_value}'")

                size_word = None
                color_word = None

                # 检查条件：剩余数据不为空串 并且 步骤2中的color也没有数据
                color_is_empty = (not color_value or 
                                pd.isna(color_value) or 
                                str(color_value).strip() == '')
                
                if not color_is_empty:
                    color_word = color_value
                    # print(f"color列已有数据 '{color_value}'，不覆盖")

                # 5. 对于temp列的字符串数据，检查是否包含SIZE
                if re.search(r'\bsize\b', temp_value, re.IGNORECASE):
                    # 使用正则表达式匹配SIZE及后面的内容
                    size_pattern = re.compile(r'(.*?)\bsize\s+([A-Za-z0-9]+)(?:\s+(.*))?', re.IGNORECASE)
                    match = size_pattern.search(temp_value)
                    
                    if match:
                        before_size = match.group(1).strip() if match.group(1) else ''  # SIZE之前的内容
                        size_word = match.group(2)  # SIZE后的第一个单词
                        after_size_rest = match.group(3).strip() if match.group(3) else ''  # SIZE第一个单词后的剩余内容
                        # print(f"匹配结果 - SIZE前: '{before_size}', size单词: '{size_word}', SIZE后剩余: '{after_size_rest}'")
                        
                        # 6. 处理剩余数据作为color的条件
                        # 剩余数据包括SIZE之前的内容和SIZE第一个单词后的剩余内容
                        remaining_data = ''
                        if before_size and after_size_rest:
                            remaining_data = f"{before_size} {after_size_rest}"
                        elif before_size:
                            remaining_data = before_size
                        elif after_size_rest:
                            remaining_data = after_size_rest
                        
                        remaining_cleaned = remaining_data.strip()

                        if remaining_cleaned and color_is_empty:
                            color_word = remaining_cleaned
                            # print(f"条件满足，写入color: '{remaining_cleaned}' ")
                        # else:
                        #     if not color_is_empty:
                        #         # color_word = color_value
                        #         print(f"color列已有数据 '{color_value}'，不覆盖")
                        #     elif not remaining_cleaned:
                        #         print(f" 剩余文本为空，不写入color")
                                
                    # else:
                    #     print(f"虽然包含SIZE但正则匹配失败")
                else:
                    # 未找到SIZE关键词。规格处理后的数据不是空 并且货号中没有color的话作为color"
                    if color_is_empty and str(temp_value).strip() != '':
                        color_word = temp_value

                # specifications = dewu.get(excel.DEWU_COLUMN_INDEX.get('规格')).split(" ")
                # colors = None
                # size = None
                # dewu_color_specification = None
                # for specification in specifications:
                #     if colors is None:
                #         colors = color_dict.montbell_color_convert(specification)
                #         if colors is not None:
                #             dewu_color_specification = specification
                #     if size is None:
                #         size = size_dict.montbell_size_convert(specification)
                dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '没有color size匹配到，确认'})
                # print(f"color_word: '{color_word}', size_word: '{size_word}'")
                
                for tianmao in tianmao_value:
                    # print(f"TIANMAO_color: '{tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('color'))}'")
                    # print(f"TIANMAO_size: '{tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size'))}'")
                    # print(f"color_result: '{tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('color')) in color_word}'")
                    # print(f"color_result: '{str(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size'))) == size_word}'")
                    if (((  color_word is not None and size_word is not None) and (
                            tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('color')) in color_word ) and (
                            str(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size'))) == size_word)) or (
                            
                            ((  color_word is None and size_word is not None) and (
                            str(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size'))) == size_word) and (
                            str(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('color'))).strip() == ''))) or (
                            
                            ((  color_word is not None and size_word is None) and (
                            tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('color')) in color_word) and (
                            str(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size'))).strip() == '')))
                        ):
                        dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '',
                                    excel.DEWU_COLUMN_INDEX.get('*修改后发货时效（天）'): dewu.get(
                                        excel.DEWU_COLUMN_INDEX.get('发货时效（天）')),
                                    excel.DEWU_COLUMN_INDEX.get('*修改后出价(JPY)'): dewu.get(
                                        excel.DEWU_COLUMN_INDEX.get('我的出价(JPY)')),
                                    excel.DEWU_COLUMN_INDEX.get('*修改后库存'): tianmao.get(
                                        excel.TIANMAO_COLUMN_INDEX.get('quantity'))})
                        if tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('msrp')) > float(str(dewu.get(
                                excel.DEWU_COLUMN_INDEX.get('预计收入(JPY)'))).replace(" ", "").replace(",", "")):
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
            str(v) if k == excel.DEWU_COLUMN_INDEX.get('出价ID') or k == excel.DEWU_COLUMN_INDEX.get('SKU ID') or k == excel.DEWU_COLUMN_INDEX.get('条形码') else v) for
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
