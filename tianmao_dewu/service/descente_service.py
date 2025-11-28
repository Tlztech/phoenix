import re
import os
import pandas as pd

from constant import excel
from dict import color_dict, size_dict
from util import env_util, common_util
from util.excel_util import ExcelUtil
from datetime import datetime
from collections import OrderedDict

def extract_model_and_color(huohao):
    # 提取货号的数字部分作为model，英文字母部分作为color
    if pd.isna(huohao) or huohao == '':
        return "", ""
    
    if '-' in huohao:
        # 找到最后一个横线的位置
        last_dash_index = huohao.rfind('-')
        model = huohao[:last_dash_index]
        color_data = huohao[last_dash_index + 1:]
        
        color_match = re.search(r'[a-zA-Z0-9]+', color_data)
        color = color_match.group() if color_match else ""
        if color.isdigit():
            color = ""
        return model, color
    else:
        # 提取数字部分
        model_match = re.search(r'[a-zA-Z0-9]+', huohao)
        model = model_match.group() if model_match else ""
        # 没有横线的情况
        return model, ""


def process_specification(spec):
    #"""处理规格列数据"""
    if pd.isna(spec) or spec == '':
        return "", "", "", ""
    
    spec_str = str(spec).replace('双装', '').strip()
    
    # 3. 提取中文部分作为颜色匹配关键词1
    chinese_matches = re.findall(r'[\u4e00-\u9fffx×/]+', spec_str)
    color_keyword1 = ''.join(chinese_matches) if chinese_matches else ""
    color_keyword1 = color_keyword1.replace('宽', '').rstrip('/').strip()
    
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
        else:
            size = temp
            color_keyword2 = color_keyword2.strip()
        
        # 处理一些特殊情况以及纯数字的情况
        color_keyword2 = color_keyword2.replace('Logo', '').replace('x 2E', '').replace('x', '').replace('One', '').strip()
        if color_keyword2.isdigit():
            color_keyword2 = ""
    
    return temp, size, color_keyword1, color_keyword2

def load_color_mapping(file_path):
    #"""加载颜色对照表并创建映射字典（不区分大小写）"""
    try:
        if not os.path.exists(file_path):
            print(f"警告：颜色对照文件 {file_path} 不存在")
            return None
            
        color_df = pd.read_excel(file_path)
        print(f"成功加载颜色对照表，共 {len(color_df)} 行数据")
        
        # 创建快速查找的字典
        color_ref = {
            'abbr_lower': {},  # 色号（英文缩写）的小写映射
            'desc_lower': {},  # 官方英文描述的小写映射
            'chinese_colors': {}  # 中文颜色词映射到色号列表
        }
        
        # 处理每一行颜色数据
        for idx, row in color_df.iterrows():
            # 获取色号（英文缩写）
            abbr = ''
            if '色号（英文缩写）' in row and pd.notna(row['色号（英文缩写）']):
                abbr = str(row['色号（英文缩写）']).strip()
            
            # 处理色号（英文缩写）列 - 建立小写映射
            if abbr:
                color_ref['abbr_lower'][abbr.lower()] = abbr
            
            # 处理官方英文描述列
            if '官方英文描述' in row and pd.notna(row['官方英文描述']):
                desc = str(row['官方英文描述']).strip()
                if desc and abbr:
                    color_ref['desc_lower'][desc.lower()] = abbr
            
            # 处理得物颜色列 - 建立中文颜色词映射
            if '得物颜色' in row and pd.notna(row['得物颜色']):
                chinese_colors = str(row['得物颜色']).strip()
                if chinese_colors and abbr:
                    # 按逗号分割中文颜色词
                    colors_list = [color.replace(" ", "").replace("Logo", "") for color in chinese_colors.split(',')]
                    for color in colors_list:
                        if color:
                            if color not in color_ref['chinese_colors']:
                                color_ref['chinese_colors'][color] = []
                            if abbr not in color_ref['chinese_colors'][color]:
                                color_ref['chinese_colors'][color].append(abbr)
        
        print(f"颜色对照表预处理完成:")
        print(f"  - 色号数量: {len(color_ref['abbr_lower'])}")
        print(f"  - 英文描述数量: {len(color_ref['desc_lower'])}")
        print(f"  - 中文颜色词数量: {len(color_ref['chinese_colors'])}")
        
        return color_ref
        
    except Exception as e:
        print(f"加载颜色对照表时出错: {e}")
        return None

def match_color(color_keyword1, color_keyword2, color_ref):
    #"""匹配颜色关键词"""
    if not color_ref:
        return color_keyword1
    
    matched_color = ''
    
    # 8.1 先用颜色匹配关键词2匹配
    if color_keyword2:
        keyword2_lower = color_keyword2.lower()
        
        # 在色号（英文缩写）列中匹配
        if keyword2_lower in color_ref['abbr_lower']:
            matched_color = color_ref['abbr_lower'][keyword2_lower]
            # print(f"  匹配成功: 关键词2 '{color_keyword2}' -> 色号 '{matched_color}'")
        
        # 在官方英文描述列中匹配
        elif not matched_color and keyword2_lower in color_ref['desc_lower']:
            matched_color = color_ref['desc_lower'][keyword2_lower]
            # print(f"  匹配成功: 关键词2 '{color_keyword2}' -> 描述 '{matched_color}'")
    
    # 用颜色匹配关键词1匹配中文颜色词
    if not matched_color and color_keyword1:
        if color_keyword1 in color_ref['chinese_colors']:
            # 获取所有匹配的色号，去重
            matched_abbrs = list(OrderedDict.fromkeys(color_ref['chinese_colors'][color_keyword1]))
            matched_color = ','.join(matched_abbrs)
            # print(f"  匹配成功: 关键词1 '{color_keyword1}' -> 中文颜色 '{matched_color}'")
                    
    # 8.1.4 如果都没有匹配到，使用关键词2作为color数据
    if not matched_color:
        if color_keyword2 and str(color_keyword2).strip():
            # print(f"keyword2_clean: {keyword2_clean}")
            matched_color = str(color_keyword2).strip().lower().strip()
        elif color_keyword1 and str(color_keyword1).strip():
            # print(f"keyword1: {keyword1}")
            matched_color =  color_keyword1
        else:
            matched_color =  ''

        # print(f"  未匹配到颜色关键词: '{matched_color}'")
    
    return matched_color

def service():
    # 读取Excel数据
    tianmao_input = ExcelUtil(env_util.get_env('EXCEL_INPUT_FILE_TIANMAO'))
    tianmao_input.load_data([value for key, value in excel.TIANMAO_COLUMN_INDEX.items() if key != '结果'], 1)
    
    # 读取排序后的第一个得物文件
    print(f"读取排序后的第一个得物文件: {common_util.get_sorted_excelfiles('.')[0]}")
    dewu_input = ExcelUtil(common_util.get_sorted_excelfiles('.')[0])
    dewu_input.load_data([value for key, value in excel.DEWU_COLUMN_INDEX.items() if key != '结果'], 3)
    
    tianmao_input_group_data_dict = tianmao_input.get_group_by_column(excel.TIANMAO_COLUMN_INDEX.get('model'))
    dewu_input_group_data_dict = dewu_input.get_group_by_column(excel.DEWU_COLUMN_INDEX.get('货号'))
    tianmao_model_list = list(tianmao_input_group_data_dict.keys())
    dewu_model_in_tianmao_list = []
    
    # 颜色对照表文件路径
    color_mapping_file = "descente颜色对照.xlsx"

    # 加载颜色映射
    # print(f"正在加载颜色对照表: {color_mapping_file}")
    color_ref = load_color_mapping(color_mapping_file)
    
    for dewu_key, dewu_value in dewu_input_group_data_dict.items():
        color_value = None
        if isinstance(dewu_key, str):
            model, color_from_huohao = extract_model_and_color(dewu_key)
            # 1. 提取数字部分作为model
            dewu_formatted_model = model
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
                    matched_color = match_color(color_keyword1, color_keyword2, color_ref)
                
                    # 如果匹配到颜色且货号中没有提取到颜色，则使用匹配的颜色
                    if matched_color and not color_value:
                        color_word = matched_color
                else:
                    # 未找到SIZE关键词。规格处理后的数据不是空 并且货号中没有color的话作为color"
                    if color_is_empty and str(temp).strip() != '':
                        color_word = temp

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
