import math
import re
import os
import pandas as pd

from constant import excel
from util import env_util, common_util
from util.excel_util import ExcelUtil
from datetime import datetime

def process_specification(spec):
    #"""处理规格列数据"""
    if pd.isna(spec) or spec == '':
        return "", "", "", ""
    
    spec_str = str(spec).replace('1双装', '').replace('1条装', '').replace('3双装', '').replace('3条装', '').replace('套装', '').strip()
    
    # 3. 提取中文部分作为颜色匹配关键词1
    chinese_matches = re.findall(r'[\u4e00-\u9fffx×/\+]+', spec_str)
    color_keyword1 = ''.join(chinese_matches) if chinese_matches else ""
    color_keyword1 = color_keyword1.replace('宽', '').rstrip('/').lstrip('/').strip()
    
    # 4. 去掉非英语字母的数据（中文及/符号），保留空格
    # 先保留英文和空格
    temp = re.sub(r'[^a-zA-Z0-9./（）\-\(\)\s]', '', spec_str)
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
                first_word_match = re.match(r'^([a-zA-Z0-9./（）\-\(\)]+)', after_size)
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
        
        # 对尺码进行分割处理
        if size:
            # 处理尺码字符串
            size = process_string_size_v2(size)
            size = size.replace('XXXXL', '4XL').replace('XXXL', '3XL').replace('2XL', 'XXL').strip()
    
    return temp, size, color_keyword1, color_keyword2

def process_string_size(input_str):
    # """
    # 按照规则处理字符串并返回Size
    
    # 规则：
    # 1. 如果字符串中包含有括号()或者中文的（），那么先提取括号中的数据
    #    （注意：有可能存在前半括号是英文的，后半括号是中文的括号。反之，也可能是前半括号是中文的，后半括号是英文的括号）
    #     1.1 对于提取后的数据以及剩余的数据（去掉括号）
    #         1.1.1 如果有/的话，那么就按照/进行分割。把分割后的数据，用逗号进行连接，然后作为Size返回。
    #         1.1.2 如果没有/的话，那么就把1.1的处理的数据，用逗号进行连接，然后作为Size返回。
    # 2. 如果字符串中没有括号()以及中文的（），但是有/的话
    #     2.1 那么就按照/进行分割。把分割后的数据，用逗号进行连接，然后作为Size返回。
    # 3. 上面以外的情况，不做任何处理，把原字符串作为Size返回。
    # """
    
    # 检查输入是否为字符串
    if not isinstance(input_str, str):
        return input_str
    
    # 检查是否有任何类型的括号（英文或中文）
    has_any_brackets = any(char in input_str for char in ['(', ')', '（', '）'])
    
    if has_any_brackets:
        # 方法1：使用更灵活的正则表达式匹配各种括号组合
        bracket_pattern = r'[\(（].*?[\)）]'
        bracket_matches = re.findall(bracket_pattern, input_str)
        
        # 获取括号外的内容（去掉括号及其内容）
        remaining_str = re.sub(bracket_pattern, '', input_str).strip()
        
        # 收集所有需要处理的部分
        all_parts = []
        
        # 处理括号外的内容
        if remaining_str:
            if '/' in remaining_str:
                # 1.1.1 有/的情况，按/分割
                all_parts.extend([part.strip() for part in remaining_str.split('/') if part.strip()])
            else:
                # 1.1.2 没有/的情况，直接添加
                all_parts.append(remaining_str)
        
        # 处理括号内的内容（去掉括号字符本身）
        for bracket_content in bracket_matches:
            # 去掉开头和结尾的括号字符
            content = bracket_content[1:-1].strip()  # 去掉第一个和最后一个字符（括号）
            if '/' in content:
                # 1.1.1 有/的情况，按/分割
                all_parts.extend([part.strip() for part in content.split('/') if part.strip()])
            else:
                # 1.1.2 没有/的情况，直接添加
                all_parts.append(content)
        
        # 用逗号连接所有部分
        return ','.join(all_parts)
    
    # 规则2：没有括号但是有/
    elif '/' in input_str:
        # 2.1 按照/进行分割，然后用逗号连接
        parts = [part.strip() for part in input_str.split('/') if part.strip()]
        return ','.join(parts)
    
    # 规则3：其他情况，返回原字符串
    else:
        return input_str

def process_string_size_v2(input_str):
    """
    更精确的版本，处理混合括号情况
    """
    if not isinstance(input_str, str):
        return input_str
    
    # 查找所有括号对的位置
    def find_bracket_pairs(text):
        pairs = []
        stack = []
        
        for i, char in enumerate(text):
            if char in ['(', '（']:  # 左括号
                stack.append((char, i))
            elif char in [')', '）']:  # 右括号
                if stack:
                    left_char, left_pos = stack.pop()
                    # 检查括号是否匹配（不要求同类型）
                    pairs.append((left_pos, i))
        
        # 按起始位置排序
        pairs.sort()
        return pairs
    
    bracket_pairs = find_bracket_pairs(input_str)
    
    if bracket_pairs:
        # 提取括号内容
        bracket_contents = []
        remaining_indices = set(range(len(input_str)))
        
        for start, end in bracket_pairs:
            # 提取括号内的内容（不包括括号本身）
            content = input_str[start+1:end].strip()
            bracket_contents.append(content)
            # 标记这些位置为已处理（包括括号）
            for i in range(start, end+1):
                if i in remaining_indices:
                    remaining_indices.remove(i)
        
        # 构建剩余字符串
        remaining_chars = [input_str[i] for i in sorted(remaining_indices)]
        remaining_str = ''.join(remaining_chars).strip()
        
        # 收集所有需要处理的部分
        all_parts = []
        
        # 处理括号外的内容
        if remaining_str:
            if '/' in remaining_str:
                all_parts.extend([part.strip() for part in remaining_str.split('/') if part.strip()])
            else:
                all_parts.append(remaining_str)
        
        # 处理括号内的内容
        for content in bracket_contents:
            if '/' in content:
                all_parts.extend([part.strip() for part in content.split('/') if part.strip()])
            else:
                all_parts.append(content)
        
        return ','.join(all_parts)
    
    # 规则2：没有括号但是有/
    elif '/' in input_str:
        parts = [part.strip() for part in input_str.split('/') if part.strip()]
        return ','.join(parts)
    
    # 规则3：其他情况
    else:
        return input_str
    

def service():
    # 读取Excel数据
    tianmao_input = ExcelUtil(env_util.get_env('EXCEL_INPUT_FILE_TIANMAO'))
    tianmao_input.load_data([value for key, value in excel.TIANMAO_COLUMN_INDEX.items() if key != '结果'], 1)
    
    # 读取排序后的第一个得物文件
    dewu_input = ExcelUtil(common_util.get_sorted_excelfiles('.')[0])
    dewu_input.load_data([value for key, value in excel.DEWU_COLUMN_INDEX.items() if key != '结果' and key != '得物原价格'], 3)
    
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
                match_size_flag = False

                # 处理规格列
                temp, size, color_keyword1, color_keyword2 = process_specification(spec_value)

                # 对于规格列的字符串数据，检查是否包含SIZE
                if size:
                    size_word = size

                dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '没有匹配到天猫的规格(颜色尺码)，下架'})
                # print(f"color_word: '{color_word}', size_word: '{size_word}'")
                
                for tianmao in tianmao_value:
                    # 如果size有多个，按逗号分隔
                    if size_word and (',' in size_word):
                        size_splits = [size_split.strip() for size_split in size_word.split(',')]  # 去除每个部分两端的空格
                        # 检查tianmao中的size是否与分隔后的任意部分完全相等
                        if str(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size'))) in size_splits:
                            match_size_flag = True
                    
                    # 如果size中没有逗号，直接比较
                    else:
                         if str(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('size'))) == size_word:
                            match_size_flag = True

                    if (match_size_flag):
                        dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '',
                                     excel.DEWU_COLUMN_INDEX.get('*修改后发货时效（天）'): dewu.get(
                                         excel.DEWU_COLUMN_INDEX.get('发货时效（天）')),
                                     excel.DEWU_COLUMN_INDEX.get('*修改后出价(JPY)'): dewu.get(
                                         excel.DEWU_COLUMN_INDEX.get('我的出价(JPY)')),
                                     excel.DEWU_COLUMN_INDEX.get('*修改后库存'): tianmao.get(
                                         excel.TIANMAO_COLUMN_INDEX.get('quantity'))})
                        # msrp 不等于 采购成本(JPY)
                        if pd.isna(dewu.get(excel.DEWU_COLUMN_INDEX.get('采购成本(JPY)'))) or not dewu.get(excel.DEWU_COLUMN_INDEX.get('采购成本(JPY)')):
                            dewu.update(
                                {excel.DEWU_COLUMN_INDEX.get(
                                    '结果'): f"天猫价格和采购成本(JPY)不一致，已更新O列"})
                            dewu.update({
                                excel.DEWU_COLUMN_INDEX.get('采购成本(JPY)'): 
                                    round(float(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('msrp'))))})
                        elif round(float(tianmao.get(excel.TIANMAO_COLUMN_INDEX.get('msrp')))) != round(float(str(dewu.get(
                                excel.DEWU_COLUMN_INDEX.get('采购成本(JPY)'))).replace(" ", "").replace(",", ""))):
                            dewu.update(
                                {excel.DEWU_COLUMN_INDEX.get(
                                    '结果'): f"天猫价格和采购成本(JPY)不一致，已更新O列"})
                            dewu.update(
                                {excel.DEWU_COLUMN_INDEX.get('得物原价格'): 
                                    round(float(str(dewu.get(excel.DEWU_COLUMN_INDEX.get('采购成本(JPY)'))).replace(" ", "").replace(",", "")))})
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
