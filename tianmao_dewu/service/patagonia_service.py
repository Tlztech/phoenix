import re
import os
import pandas as pd

from constant import excel
from util import env_util, common_util
from util.excel_util import ExcelUtil
from datetime import datetime
from collections import OrderedDict

def extract_model_and_color(huohao):
    # 提取货号的数字部分作为model，英文字母部分作为color
    if pd.isna(huohao) or huohao == '':
        return "", ""
    
    huohao_str = str(huohao).strip()
    # 提取数字部分
    model_match = re.search(r'\d+', huohao_str)
    model = model_match.group() if model_match else ""
    
    # 提取英文字母部分
    color_match = re.search(r'[a-zA-Z]+', huohao_str)
    color = color_match.group() if color_match else ""
    
    return model, color

def extract_color_keyword1(spec):
    # 从规格字符串中提取color_keyword1的主要函数
    # 思路：先移除所有尺码信息，再提取颜色部分

    # 第一步：预处理，统一处理常见特殊情况
    spec = preprocess_spec(spec)
    
    # 第二步：移除所有可能的尺码信息
    spec = remove_all_size_info(spec)
    
    # 第三步：清理和格式化颜色信息
    color_text = spec.strip()
    
    # 第四步：处理特殊情况和格式化输出
    return format_color_keyword(color_text)


def preprocess_spec(spec):
    # """预处理规格字符串"""
    spec = spec.strip()
    
    # 处理特殊括号格式
    if '（' in spec and '）' in spec:
        spec = spec.replace('（', '(').replace('）', ')')
    
    # 处理带数字的品牌格式，如"黑色/73 Text Logo: Black"
    # 这里我们暂时保持原样，稍后处理
    
    return spec


def remove_all_size_info(spec):
    # """移除所有尺码相关信息的通用函数"""
    # 定义所有可能的尺码模式（按优先级）
    size_patterns = [
        # 1. 复杂的复合尺码模式
        r'(?i)\b(?:SIZE|Size|尺寸|尺码)\s+[A-Za-z0-9\-+/]+(?:[A-Za-z0-9\-+/]+\b)?',
        
        # 2. 品牌尺码模式
        r'(?i)\b(?:Brand\s+Size|Belt\s+Size|Belt|Brand|Size)\s+\d+[A-Za-z]*',
        
        # 3. 数字尺码模式
        r'\b\d+(?:[A-Za-z\-+/]+\b)?\s+(?:[A-Za-z\u4e00-\u9fff]+)',  # 数字在前的格式
        r'(?:[A-Za-z\u4e00-\u9fff]+\s+)?\b\d+[A-Za-z]*\b',  # 单独数字尺码
        
        # 4. 年龄尺码
        r'(?i)\bAge\s+\d+\b',
        r'\b\d+(?:Y|y|岁|\s*Years?\s*Old)?\b',
        
        # 5. 儿童尺码
        r'\b\d+(?:[A-Za-z]?\-?\d*[A-Za-z]?)?[TtMm]\b',
        r'\b\d+(?:\-\d+)?[TtMm]\b',
        
        # 6. US/JP等前缀尺码
        r'(?i)\b(?:US|JP|UK|EU|FR|IT|DE|ES)\s*\d+\b',
        
        # 7. 单独的常见尺码
        r'\b(?:XXXL|XXL|XL|L|M|S|XS|XXS|OS|One\s+Size|均码|OneSize|均号)\b',
        
        # 8. Ordered Size相关
        r'(?i)\bOrdered\s+Size\s+[A-Za-z0-9\-/]+\b',
        r'(?i)\bInternational\s+Code\s+[A-Za-z0-9]+\b',
        
        # 9. 其他特殊尺码格式
        r'\b(?:S|M|L|XL|XXL)(?:S|M|L)?\b',  # 复合尺码如LS, MS等
    ]
    
    # 应用所有模式
    cleaned_spec = spec
    for pattern in size_patterns:
        cleaned_spec = re.sub(pattern, '', cleaned_spec, flags=re.IGNORECASE)
    
    # 移除可能残留的尺码关键词
    keywords_to_remove = [
        'SIZE', 'Size', 'size', 'SIZE:', 'Size:',
        'BRAND SIZE', 'Brand Size', 'brand size',
        'BELT SIZE', 'Belt Size', 'belt size',
        'ORDERED SIZE', 'Ordered Size', 'ordered size',
        '均码', '均号', 'ONE SIZE', 'One Size', 'one size',
        '国际码', 'International Code', 'international code',
        'Age', 'age', '歳', '岁'
    ]
    
    for keyword in keywords_to_remove:
        cleaned_spec = re.sub(r'(?i)\b' + re.escape(keyword) + r'\b', '', cleaned_spec)
    
    # 清理多余空格和特殊字符
    cleaned_spec = re.sub(r'\s+', ' ', cleaned_spec).strip()
    
    # 移除开头或结尾的标点
    cleaned_spec = re.sub(r'^[\s\-:;/]+|[\s\-:;/]+$', '', cleaned_spec)
    
    return cleaned_spec


def format_color_keyword(color_text):
    # """格式化颜色关键词"""
    if not color_text:
        return ""
    
    # 处理特殊格式：带括号的中文描述
    if '(' in color_text and ')' in color_text:
        # 提取括号内的内容
        match = re.search(r'\((.*?)\)', color_text)
        if match:
            inner_content = match.group(1)
            # 如果括号内是颜色信息，优先使用
            if any(char in inner_content for char in ['/', '-', ' ']):
                return format_specific_color(inner_content)
    
    # 处理标准颜色格式
    return format_specific_color(color_text)


def format_specific_color(color_text):
    # """处理具体的颜色格式"""
    
    # 1. 包含斜杠的格式（可能多个斜杠）
    if '/' in color_text:
        # 清理斜杠周围的空格
        parts = [part.strip() for part in color_text.split('/')]
        
        # 如果有多个部分，尝试找到有意义的中英文对应
        if len(parts) >= 2:
            # 找到可能的中文部分（包含中文字符的部分）
            chinese_parts = [p for p in parts if re.search(r'[\u4e00-\u9fff]', p)]
            english_parts = [p for p in parts if re.search(r'[A-Za-z]', p) and not re.search(r'[\u4e00-\u9fff]', p)]
            
            if chinese_parts and english_parts:
                # 取第一个中文和第一个英文部分
                chinese = chinese_parts[0]
                english = ' '.join(english_parts[0].split())  # 清理空格
                return f"{chinese}/{english}"
            elif len(parts) == 2:
                # 只有两部分，直接组合
                return f"{parts[0]}/{parts[1]}"
            else:
                # 多个部分，保持原样
                return '/'.join(parts)
    
    # 2. 包含连字符的格式
    elif '-' in color_text:
        parts = [part.strip() for part in color_text.split('-')]
        if len(parts) >= 2:
            # 判断哪部分包含中文
            chinese_part = next((p for p in parts if re.search(r'[\u4e00-\u9fff]', p)), '')
            english_part = next((p for p in parts if re.search(r'^[A-Za-z\s]+$', p)), '')
            
            if chinese_part and english_part:
                return f"{chinese_part}/{english_part}"
            elif len(parts) == 2:
                return f"{parts[0]}/{parts[1]}"
    
    # 3. 中英混合但没有分隔符（如"黑色BLK"）
    elif re.search(r'[\u4e00-\u9fff]', color_text) and re.search(r'[A-Za-z]', color_text):
        # 尝试分离中文和英文
        chinese_match = re.search(r'[\u4e00-\u9fff]+', color_text)
        english_match = re.search(r'[A-Za-z\s]+', color_text)
        
        if chinese_match and english_match:
            chinese = chinese_match.group()
            english = english_match.group().strip()
            # 确保英文部分合理（不是单个字母或奇怪的组合）
            if len(english) > 1 or english in ['BLK', 'WHI', 'INBK', 'OLGG']:
                return f"{chinese}/{english}"
    
    # 4. 纯英文格式（包含空格）
    elif re.search(r'^[A-Za-z\s]+$', color_text):
        # 清理多余空格，保持单词间单个空格
        cleaned = ' '.join(color_text.split())
        return cleaned
    
    # 5. 纯中文格式
    elif re.search(r'^[\u4e00-\u9fff]+$', color_text):
        return color_text
    
    # 6. 复合格式：中文拼接英文
    # 处理如"鹈鹕白拼烟熏蓝/PNSM"或"黑色拼锻造灰/BFO"
    if '拼' in color_text and '/' in color_text:
        # 保持原样
        return color_text
    
    # 7. 默认情况：返回清理后的文本
    # 清理多余空格
    cleaned = ' '.join(color_text.split())
    return cleaned

def process_specification(spec):
    # """处理规格列数据"""
    if pd.isna(spec) or spec == '':
        return "", "", "", ""
    
    spec_str = str(spec).replace('1双装', '').replace('两件套', '').replace('主页：', '').replace('1条装', '').replace('均码', '').replace('Ordered', '').replace('One Size', '').replace('Brand ', '').replace('Belt ', '').replace('（', '').replace('）', '').strip()
    
    # 3. 提取中文部分作为颜色匹配关键词1
    color_keyword1 = extract_color_keyword1(spec_str)
    if str(color_keyword1).strip() == '':
        chinese_matches = re.findall(r'[\u4e00-\u9fff]+', spec_str)
        color_keyword1 = ''.join(chinese_matches) if chinese_matches else ""
    
    # 4. 去掉非英语字母的数据（中文及/符号），保留空格
    # 先保留英文和空格
    temp = re.sub(r'[^a-zA-Z0-9-\s]', '', spec_str)
    # 规范化空格（多个空格合并为一个）
    temp = re.sub(r'\s+', ' ', temp).strip()
    
    # 6. 提取size和7. 处理颜色匹配关键词2
    size = ""
    size_age = ""
    color_keyword2 = ""
    usual_sizes = {'S', 'M', 'L', 'XS', 'XL', 'XXS', 'XXL', 'XXXL'}
    
    if temp:
        # 查找SIZE（不区分大小写）
        size_pattern = re.compile(r'\bsize\b', re.IGNORECASE)
        size_match = size_pattern.search(temp)
        
        # 查找US（不区分大小写）
        us_pattern = re.compile(r'\bus\b', re.IGNORECASE)
        us_match = us_pattern.search(temp)
        
        # 查找Age（不区分大小写）
        age_pattern = re.compile(r'\bAge\b', re.IGNORECASE)
        age_match = age_pattern.search(temp)
        
        if size_match:
            # 获取SIZE后的部分
            after_size = temp[size_match.end():].strip()
            if after_size:
                # 提取SIZE后的第一个英文单词作为size
                first_word_match = re.match(r'^([a-zA-Z0-9-]+)', after_size)
                if first_word_match:
                    size = first_word_match.group(1)
            
            # 7. 处理颜色匹配关键词2 - 去掉SIZE及后面的第一个单词
            # 构建要移除的模式
            if size:
                # 使用更精确的模式匹配
                pattern_to_remove = r'size\s*' + re.escape(size)
                color_keyword2 = re.sub(pattern_to_remove, '', temp, flags=re.IGNORECASE)
                color_keyword2 = color_keyword2.strip().strip('-')
            else:
                # 如果没找到size单词，只移除SIZE
                color_keyword2 = re.sub(size_pattern, '', temp)
            
            color_keyword2 = color_keyword2.strip()
        elif us_match:
            # 获取US后的部分
            after_size = temp[us_match.end():].strip()
            if after_size:
                # 提取US后的第一个英文单词作为size
                first_word_match = re.match(r'^([a-zA-Z0-9-]+)', after_size)
                if first_word_match:
                    size = first_word_match.group(1)
            
            # 7. 处理颜色匹配关键词2 - 去掉SIZE及后面的第一个单词
            # 构建要移除的模式
            if size:
                # 使用更精确的模式匹配
                pattern_to_remove = r'us\s*' + re.escape(size)
                color_keyword2 = re.sub(pattern_to_remove, '', temp, flags=re.IGNORECASE)
                color_keyword2 = color_keyword2.strip().strip('-')
            else:
                # 如果没找到US单词，只移除US
                color_keyword2 = re.sub(us_pattern, '', temp)
            
            color_keyword2 = color_keyword2.strip()
        elif age_match:
            # 获取Age后的部分
            after_size = temp[age_match.end():].strip()
            if after_size:
                # 提取age后的第一个英文单词作为size
                first_word_match = re.match(r'^([a-zA-Z0-9-]+)', after_size)
                if first_word_match:
                    size_age = first_word_match.group(1)
                    if size_age in {'2', '3', '4', '5'}:
                        size = size_age + 'T'
                    else:
                        size = size_age + 'M'
            
            # 7. 处理颜色匹配关键词2 - 去掉age及后面的第一个单词
            # 构建要移除的模式
            if size:
                # 使用更精确的模式匹配
                pattern_to_remove = r'age\s*' + re.escape(size_age)
                color_keyword2 = re.sub(pattern_to_remove, '', temp, flags=re.IGNORECASE)
                color_keyword2 = color_keyword2.strip().strip('-')
            else:
                # 如果没找到US单词，只移除age
                color_keyword2 = re.sub(age_pattern, '', temp)
            
            color_keyword2 = color_keyword2.strip()
        else:  
            parts = temp.split()
            
            for part in parts:
                if part in usual_sizes:
                    size = part
                    color_keyword2 = re.sub(r'\b' + re.escape(size) + r'\b', '', temp, flags=re.IGNORECASE)
                    color_keyword2 = color_keyword2.strip()
            
            if str(color_keyword2).strip() == '':
                color_keyword2 = temp.strip()
    
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
    matched_color_pattern = ''
    
    # 8.1 先用颜色匹配关键词2匹配
    if color_keyword2:
        keyword2_lower = color_keyword2.lower()
        
        # 在色号（英文缩写）列中匹配
        if keyword2_lower in color_ref['abbr_lower']:
            matched_color = color_ref['abbr_lower'][keyword2_lower]
            matched_color_pattern = '使用颜色关键词2在色号（英文缩写）列中匹配成功'
            # print(f"  匹配成功: 关键词2 '{color_keyword2}' -> 色号 '{matched_color}'")
        
        # 在官方英文描述列中匹配
        elif not matched_color and keyword2_lower in color_ref['desc_lower']:
            matched_color = color_ref['desc_lower'][keyword2_lower]
            matched_color_pattern = '使用颜色关键词2在官方英文描述列中匹配成功'
            # print(f"  匹配成功: 关键词2 '{color_keyword2}' -> 描述 '{matched_color}'")
    
    # 用颜色匹配关键词1匹配中文颜色词
    if not matched_color and color_keyword1:
        if color_keyword1 in color_ref['chinese_colors']:
            # 获取所有匹配的色号，去重
            matched_abbrs = list(OrderedDict.fromkeys(color_ref['chinese_colors'][color_keyword1]))
            matched_color = ','.join(matched_abbrs)
            matched_color_pattern = '使用颜色关键词1在得物颜色列中匹配成功'
            # print(f"  匹配成功: 关键词1 '{color_keyword1}' -> 中文颜色 '{matched_color}'")
                    
    # 8.1.4 如果都没有匹配到，使用关键词2作为color数据
    if not matched_color:
        if color_keyword2 and str(color_keyword2).strip():
            # print(f"keyword2_clean: {keyword2_clean}")
            matched_color = str(color_keyword2).strip().lower().strip()
            matched_color_pattern = '都没有匹配成功，使用颜色关键词2'
        elif color_keyword1 and str(color_keyword1).strip():
            # print(f"keyword1: {keyword1}")
            matched_color =  color_keyword1
            matched_color_pattern = '都没有匹配成功，使用颜色关键词1'
        else:
            matched_color =  ''
            matched_color_pattern = ''

        # print(f"  未匹配到颜色关键词: '{matched_color}'")
    
    return matched_color, matched_color_pattern


def service():
    # 读取Excel数据
    tianmao_input = ExcelUtil(env_util.get_env('EXCEL_INPUT_FILE_TIANMAO'))
    tianmao_input.load_data([value for key, value in excel.TIANMAO_COLUMN_INDEX.items() if key != '结果'], 1)
    
    # 读取排序后的第一个得物文件
    print(f"正在处理的得物表格: {common_util.get_sorted_excelfiles('.')[0]}")
    dewu_input = ExcelUtil(common_util.get_sorted_excelfiles('.')[0])
    dewu_input.load_data([value for key, value in excel.DEWU_COLUMN_INDEX.items() if key != '结果' and key != '得物原价格'], 3)
    
    tianmao_input_group_data_dict = tianmao_input.get_group_by_column(excel.TIANMAO_COLUMN_INDEX.get('model'))
    # print(f"tianmao_input_group_data_dict '{tianmao_input_group_data_dict}'")
    dewu_input_group_data_dict = dewu_input.get_group_by_column(excel.DEWU_COLUMN_INDEX.get('货号'))
    tianmao_model_list = list(tianmao_input_group_data_dict.keys())
    # print(f"tianmao_model_list '{tianmao_model_list}'")
    dewu_model_in_tianmao_list = []
    
    # 颜色对照表文件路径
    color_mapping_file = "patagonia颜色对照.xlsx"

    # 加载颜色映射
    color_ref = load_color_mapping(color_mapping_file)

    for dewu_key, dewu_value in dewu_input_group_data_dict.items():
        color_value = None
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
        # print(f"dewu_formatted_model: '{dewu_formatted_model}'")

        tianmao_value = tianmao_input_group_data_dict.get(dewu_formatted_model)
        # print(f"tianmao_value: '{tianmao_value}'")
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
                    matched_color, matched_color_pattern = match_color(color_keyword1, color_keyword2, color_ref)
                
                    # 如果匹配到颜色且货号中没有提取到颜色，则使用匹配的颜色
                    if matched_color and not color_value:
                        color_word = matched_color
                else:
                    # 未找到SIZE关键词。规格处理后的数据不是空 并且货号中没有color的话作为color"
                    if color_is_empty and str(temp).strip() != '':
                        color_word = temp

                dewu.update({excel.DEWU_COLUMN_INDEX.get('结果'): '没有匹配到天猫的规格(颜色尺码)，下架'})
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
