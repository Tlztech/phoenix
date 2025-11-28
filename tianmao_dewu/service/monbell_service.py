import re
import os
import pandas as pd

from constant import excel
from dict import color_dict, size_dict
from util import env_util, common_util
from util.excel_util import ExcelUtil
from datetime import datetime


def extract_model_and_color(huohao):
    # 提取货号的数字部分作为model，英文字母部分作为color"""
    if pd.isna(huohao) or huohao == '':
        return "", ""
    
    huohao_str = str(huohao).strip()
    
    if '-' in huohao_str:
        # 找到最后一个横线的位置
        last_dash_index = huohao_str.rfind('-')
        
        model_data = huohao_str[:last_dash_index]
        # 提取数字部分
        model_match = re.search(r'\d+', model_data)
        model = model_match.group() if model_match else ""
        
        color_data = huohao_str[last_dash_index + 1:]
        color_match = re.search(r'[a-zA-Z]+', color_data)
        color = color_match.group() if color_match else ""
    else:
        # 没有横线的情况
        
        # 提取数字部分
        model_match = re.search(r'\d+', huohao_str)
        model = model_match.group() if model_match else ""
        
        # 提取英文字母部分
        color_match = re.search(r'[a-zA-Z]+', huohao_str)
        color = color_match.group() if color_match else ""
    
    return model, color

def process_specification(spec):
    # 处理规格列数据"""
    if pd.isna(spec) or spec == '':
        return "", "", "", ""
    
    spec_str = str(spec).strip()
    
    # 3. 提取中文部分作为颜色匹配关键词1
    chinese_matches = re.findall(r'[\u4e00-\u9fffx×]+', spec_str)
    color_keyword1 = ''.join(chinese_matches) if chinese_matches else ""
    
    # 4. 去掉非英语字母的数据（中文及/符号），保留空格
    # 先保留英文和空格
    temp = re.sub(r'[^a-zA-Z0-9.\-\s]', '', spec_str)
    # 规范化空格（多个空格合并为一个）
    temp = re.sub(r'\s+', ' ', temp).replace('SZIE', 'SIZE').strip()
    temp = re.sub(r'\b(Mens|Ordered)\b', '', temp, flags=re.IGNORECASE).strip()
    
    # 6. 提取size和7. 处理颜色匹配关键词2
    size = ""
    color_keyword2 = ""
    
    if temp:
        # 查找SIZE（不区分大小写）
        size_pattern = re.compile(r'\bsize\b', re.IGNORECASE)
        size_match = size_pattern.search(temp)
        
        # 查找JP（不区分大小写）
        jp_pattern = re.compile(r'\bjp\b', re.IGNORECASE)
        jp_match = jp_pattern.search(temp)
        
        # 查找EU（不区分大小写）
        eu_pattern = re.compile(r'\beu\b', re.IGNORECASE)
        eu_match = eu_pattern.search(temp)
        
        # 查找US（不区分大小写）
        us_pattern = re.compile(r'\bus\b', re.IGNORECASE)
        us_match = us_pattern.search(temp)
        
        if size_match:
            # 获取SIZE后的部分
            after_size = temp[size_match.end():].strip()
            if after_size:
                # 提取SIZE后的第一个英文单词作为size
                first_word_match = re.match(r'^([a-zA-Z0-9.\-]+)', after_size)
                if first_word_match:
                    size = re.sub(r'\bOne\b', '', first_word_match.group(1), flags=re.IGNORECASE).strip()
            
            # 7. 处理颜色匹配关键词2 - 去掉SIZE及后面的第一个单词
            # 构建要移除的模式
            if size:
                # 使用更精确的模式匹配
                pattern_to_remove = r'size\s*' + re.escape(size)
                color_keyword2 = re.sub(pattern_to_remove, '', temp, flags=re.IGNORECASE)
                color_keyword2 = re.sub(r'-', '', color_keyword2)
            else:
                # 如果没找到size单词，只移除SIZE
                color_keyword2 = re.sub(size_pattern, '', temp)
            
            color_keyword2 = color_keyword2.strip()
        elif jp_match:
            # 获取JP后的部分
            after_size = temp[jp_match.end():].strip()
            if after_size:
                # 提取SIZE后的第一个英文单词作为size
                first_word_match = re.match(r'^([a-zA-Z0-9.\-]+)', after_size)
                if first_word_match:
                    size = re.sub(r'\bOne\b', '', first_word_match.group(1), flags=re.IGNORECASE).strip()
            
            # 7. 处理颜色匹配关键词2 - 去掉SIZE及后面的第一个单词
            # 构建要移除的模式
            if size:
                # 使用更精确的模式匹配
                pattern_to_remove = r'JP\s*' + re.escape(size)
                color_keyword2 = re.sub(pattern_to_remove, '', temp, flags=re.IGNORECASE)
                color_keyword2 = re.sub(r'-', '', color_keyword2)
            else:
                # 如果没找到size单词，只移除SIZE
                color_keyword2 = re.sub(jp_pattern, '', temp)
        elif eu_match:
            # 获取EU后的部分
            after_size = temp[eu_match.end():].strip()
            if after_size:
                # 提取SIZE后的第一个英文单词作为size
                first_word_match = re.match(r'^([a-zA-Z0-9.\-]+)', after_size)
                if first_word_match:
                    size = re.sub(r'\bOne\b', '', first_word_match.group(1), flags=re.IGNORECASE).strip()
            
            # 7. 处理颜色匹配关键词2 - 去掉SIZE及后面的第一个单词
            # 构建要移除的模式
            if size:
                # 使用更精确的模式匹配
                pattern_to_remove = r'EU\s*' + re.escape(size)
                color_keyword2 = re.sub(pattern_to_remove, '', temp, flags=re.IGNORECASE)
                color_keyword2 = re.sub(r'-', '', color_keyword2)
            else:
                # 如果没找到size单词，只移除SIZE
                color_keyword2 = re.sub(eu_pattern, '', temp)
        elif us_match:
            # 获取EU后的部分
            after_size = temp[us_match.end():].strip()
            if after_size:
                # 提取SIZE后的第一个英文单词作为size
                first_word_match = re.match(r'^([a-zA-Z0-9.\-]+)', after_size)
                if first_word_match:
                    size = re.sub(r'\bOne\b', '', first_word_match.group(1), flags=re.IGNORECASE).strip()
            
            # 7. 处理颜色匹配关键词2 - 去掉SIZE及后面的第一个单词
            # 构建要移除的模式
            if size:
                # 使用更精确的模式匹配
                pattern_to_remove = r'US\s*' + re.escape(size)
                color_keyword2 = re.sub(pattern_to_remove, '', temp, flags=re.IGNORECASE)
                color_keyword2 = re.sub(r'-', '', color_keyword2)
            else:
                # 如果没找到size单词，只移除SIZE
                color_keyword2 = re.sub(us_pattern, '', temp)
        else:
            size = temp
        
            color_keyword2 = color_keyword2.strip()
    
    return temp, size, color_keyword1, color_keyword2

def load_color_mapping(file_path):
    # 加载颜色对照表并创建映射字典（不区分大小写）"""
    try:
        color_df = pd.read_excel(file_path)
        
        # 创建映射字典（存储原始值，但搜索时使用小写）
        tianmao_mapping = {}  # key: 小写的tianmao值, value: 原始的tianmao值
        dewu1_mapping = {}    # key: 小写的dewu1值, value: 原始的tianmao值
        dewu_chinese_mapping = {}  # key: 中文值, value: 原始的tianmao值
        
        for _, row in color_df.iterrows():
            tianmao_value = row.get('tianmao', '')
            if pd.notna(tianmao_value) and tianmao_value != '':
                tianmao_str = str(tianmao_value).strip()
                # 存储小写版本作为key，但保留原始值
                tianmao_mapping[tianmao_str.lower()] = tianmao_str
            
            dewu1_value = row.get('dewu1', '')
            if pd.notna(dewu1_value) and dewu1_value != '':
                dewu1_str = str(dewu1_value).strip()
                dewu1_mapping[dewu1_str.lower()] = tianmao_value if pd.notna(tianmao_value) else ""
            
            # 处理dewu2到dewu9的中文颜色词
            for col_num in range(2, 10):
                col_name = f'dewu{col_num}'
                if col_name in row:
                    dewu_value = row[col_name]
                    if pd.notna(dewu_value) and dewu_value != '':
                        dewu_str = str(dewu_value).strip()
                        # 中文不需要转换为小写
                        dewu_chinese_mapping[dewu_str] = tianmao_value if pd.notna(tianmao_value) else ""
        
        return tianmao_mapping, dewu1_mapping, dewu_chinese_mapping
        
    except Exception as e:
        print(f"加载颜色对照表时出错: {e}")
        return {}, {}, {}

def match_color(color_keyword1, color_keyword2, tianmao_mapping, dewu1_mapping, dewu_chinese_mapping):
    # 匹配颜色数据（不区分大小写匹配）"""
    matched_color = ""
    
    # 8.1 优先使用颜色匹配关键词2在tianmao列中匹配（不区分大小写）
    if color_keyword2:
        color_keyword2_lower = color_keyword2.lower()
        if color_keyword2_lower in tianmao_mapping:
            matched_color = tianmao_mapping[color_keyword2_lower]
    
    # 如果没有匹配到，尝试颜色匹配关键词2在dewu1列中匹配（不区分大小写）
    if not matched_color and color_keyword2:
        color_keyword2_lower = color_keyword2.lower()
        if color_keyword2_lower in dewu1_mapping:
            matched_color = dewu1_mapping[color_keyword2_lower]
    
    # 如果还没有匹配到，尝试颜色匹配关键词1在dewu2-dewu9中文颜色词中匹配（精确匹配）
    if not matched_color and color_keyword1:
        if color_keyword1 in dewu_chinese_mapping:
            matched_color = dewu_chinese_mapping[color_keyword1]
    
    # 如果都没有匹配到，返回颜色匹配关键词2
    if not matched_color:
        matched_color = color_keyword2
    
    return matched_color


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
    
    # 颜色对照表文件路径
    color_mapping_file = "montbell颜色对照.xlsx"

    # 加载颜色映射
    print(f"正在加载颜色对照表: {color_mapping_file}")
    tianmao_mapping, dewu1_mapping, dewu_chinese_mapping = load_color_mapping(color_mapping_file)
    
    print(f"颜色映射加载完成: tianmao映射{len(tianmao_mapping)}条, dewu1映射{len(dewu1_mapping)}条, 中文映射{len(dewu_chinese_mapping)}条")

    for dewu_key, dewu_value in dewu_input_group_data_dict.items():
        if isinstance(dewu_key, str):
            model, color_from_huohao = extract_model_and_color(dewu_key)
            # 1. 提取数字部分作为model
            dewu_formatted_model = int(model)
            # print(f"货号 '{dewu_key}' -> color: '{color_value}'")

            # 2. 提取英文字母部分作为color
            color_value = color_from_huohao
            # print(f"货号 '{dewu_key}' -> color: '{color_value}'")
        else:
            dewu_formatted_model = dewu_key

        # print(f"货号 '{dewu_key}' -> model: '{dewu_formatted_model}'")

        tianmao_value = tianmao_input_group_data_dict.get(dewu_formatted_model)
        
        if dewu_formatted_model in tianmao_model_list:
            dewu_model_in_tianmao_list.append(dewu_formatted_model)
            
            for dewu in dewu_value:
                spec_value = dewu.get(excel.DEWU_COLUMN_INDEX.get('规格')).strip()
                # print(f"原始规格数据: '{spec_value}'")

                size_word = None
                color_word = None

                # 步骤2中的color也没有数据
                color_is_empty = (not color_value or 
                                pd.isna(color_value) or 
                                str(color_value).strip() == '')
                
                if not color_is_empty:
                    color_word = color_value
                    # print(f"color列已有数据 '{color_value}'，不覆盖")

                # 处理规格列
                temp, size, color_keyword1, color_keyword2 = process_specification(spec_value)

                # 对于规格列的字符串数据，检查是否包含SIZE
                if size:
                    size_word = size

                    # 8. 颜色匹配处理
                    matched_color = match_color(color_keyword1, color_keyword2, tianmao_mapping, dewu1_mapping, dewu_chinese_mapping)
                
                    # 如果匹配到颜色且货号中没有提取到颜色，则使用匹配的颜色
                    if matched_color and not color_value:
                        color_word = matched_color
                else:
                    # 未找到SIZE关键词。规格处理后的数据不是空 并且货号中没有color的话作为color"
                    if color_is_empty and str(temp).strip() != '':
                        color_word = temp
                
                dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '没有color size匹配到，确认'})
                
                for tianmao in tianmao_value:
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
                    # if ((colors and len(colors) == 1 and tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('color')) in colors) or (dewu_color_specification and tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('color')) in dewu_color_specification and len(colors) > 1)) and (
                    #         tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size')) == size):
                        dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '',
                                     excel.DEWU_COLUMN_INDEX.get('*修改后发货时效（天）'): dewu.get(
                                         excel.DEWU_COLUMN_INDEX.get('发货时效（天）')),
                                     excel.DEWU_COLUMN_INDEX.get('*修改后出价(JPY)'): dewu.get(
                                         excel.DEWU_COLUMN_INDEX.get('我的出价(JPY)')),
                                     excel.DEWU_COLUMN_INDEX.get('*修改后库存'): tianmao.get(
                                         excel.TIANMAO_COLUMN_INDEX.get('quantity'))})
                        # msrp > 预计收入(JPY)
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
                    if int(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('quantity'))) > 0:
                        tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('结果'): '该货号没有规格匹配到，得物上架'})
                    else:
                        tianmao.update({excel.TIANMAO_COLUMN_INDEX.get('结果'): '无需处理'})
        else:
            for dewu in dewu_value:
                dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '没有model匹配到，下架'})
    for tianmao_key, tianmao_value in tianmao_input_group_data_dict.items():
        if tianmao_key in dewu_model_in_tianmao_list:
            continue
        else:
            for tianmao in tianmao_value:
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
