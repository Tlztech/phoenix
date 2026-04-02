import re

from util import common_util

MONBELL_SIZE_DICT = ["L",
                     "L/XL",
                     "L-AB",
                     "L-CD",
                     "L-EF",
                     "L-L",
                     "L-R",
                     "L-S",
                     "L-SS",
                     "M",
                     "M/L",
                     "M-AB",
                     "M-CD",
                     "M-EF",
                     "M-L",
                     "M-R",
                     "M-S",
                     "S",
                     "S/M",
                     "S-AB",
                     "S-CD",
                     "S-EF",
                     "S-L",
                     "U/L",
                     "XL",
                     "XL2XL",
                     "XL-AB",
                     "XL-CD",
                     "XL-EF",
                     "XL-L",
                     "XL-S",
                     "XL-SS",
                     "XS",
                     "XS/S",
                     "XS-L",
                     "XXL",
                     "XXL-S",
                     "XXS",
                     "XXXLS"
                     ]


def montbell_size_convert(size):
    result = None
    if size in MONBELL_SIZE_DICT:
        result = size
    return result


ASICS_SIZE_EU_TO_JP_DICT = {17: 10.5,
                            18: 11,
                            18.5: 11.5,
                            19.5: 12,
                            20.5: 12.5,
                            21: 13,
                            21.5: 13.5,
                            22.5: 14,
                            23.5: 14.5,
                            23.5: 15,
                            25: 15.5,
                            26: 16,
                            26.5: 16.5,
                            27: 17,
                            28: 17.25,
                            28.5: 17.5,
                            29.5: 18,
                            30: 18.5,
                            30.5: 19,
                            31.5: 19.5,
                            32.5: 20,
                            33: 20.5,
                            33.5: 21,
                            34.5: 21.5,
                            35: 22,
                            35.5: 22.25,
                            36: 22.5,
                            37: 23,
                            37.5: 23.5,
                            38: 24,
                            39: 24.5,
                            39.5: 25,
                            40: 25.25,
                            40.5: 25.75,
                            41.5: 26,
                            42: 26.5,
                            42.5: 27,
                            43.5: 27.5,
                            44: 28,
                            44.5: 28.25,
                            45: 28.5,
                            46: 29,
                            46.5: 29.5,
                            47: 30,
                            48: 30.5,
                            48.5: 30.75,
                            49: 31,
                            49.5: 31.5,
                            50.5: 32,
                            100: 100,
                            110: 110,
                            120: 120,
                            130: 130,
                            140: 140,
                            150: 150,
                            160: 160,
                            170: 170
                            }

ASICS_SIZE_DEWU_TO_TIANMAO = {'S':'S', 'M':'M', 'L':'L', 'XS':'SS', 'XL':'LL', '2XL':'3L', 'XXL':'3L', '3XL':'4L', 'XXXL':'4L', 'SS':'SS', 'LL':'LL', '3L':'3L', '4L':'4L'} 

def asics_size_convert(size):
    if common_util.is_number(size):
        return ASICS_SIZE_EU_TO_JP_DICT.get(size, None)
    else:
        return ASICS_SIZE_DEWU_TO_TIANMAO.get(size, None)


ASICS_SIZE_SOCKS_TO_JP_DICT = {'L': '27-29',
                            'M': '25-27',
                            'S': '23-25',
                            'XS': '21-23',
                            'XXS': '19-21',
                            '2XS': '19-21'
                            }

def asics_size_convert_socks(size):
    return ASICS_SIZE_SOCKS_TO_JP_DICT.get(size, None)


KEEN_SIZE_EU_TO_JP_DICT = {'童': {'19': 11.5,
                                 '20/21': 12.5,
                                 '22': 13.5,
                                 '23': 14.5,
                                 '24': 15,
                                 '25/26': 16,
                                 '27/28': 17,
                                 '29': 18,
                                 '30': 18.5,
                                 '31': 19.5,
                                 '32/33': 20,
                                 '34': 21,
                                 '35': 22,
                                 '36': 22.5,
                                 '37': 23.5,
                                 '38': 24.5,
                                 '39': 25.5
                                 },
                           '男': {'35': 21,
                                 '35.5': 21.5,
                                 '36': 22,
                                 '36.5': 22.5,
                                 '37': 23,
                                 '38': 23.5,
                                 '38.5': 24,
                                 '39': 24.5,
                                 '39.5': 25,
                                 '40': 25.5,
                                 '40.5': 26,
                                 '41': 26.5,
                                 '42': 27,
                                 '42.5': 27.5,
                                 '43': 28,
                                 '44': 28.5,
                                 '44.5': 29,
                                 '45': 29.5,
                                 '46': 30,
                                 '47': 31,
                                 '47.5': 32,
                                 '48': 33,
                                 '48.5': 34,
                                 '49': 35
                                 },
                           '女': {'35': 22,
                                 '35.5': 22.5,
                                 '36': 23,
                                 '37': 23.5,
                                 '37.5': 24,
                                 '38': 24.5,
                                 '38.5': 25,
                                 '39': 25.5,
                                 '39.5': 26,
                                 '40': 26.5,
                                 '40.5': 27,
                                 '41': 27.5,
                                 '42': 28,
                                 '43': 29
                                 },
                           }
KEEN_SIZE_UK_TO_JP_DICT = {
    '童': { '3': 11.5,
            '4': 12.5,
            '5': 13.5,
            '6': 14.5,
            '7': 15,
            '8': 16,
            '9': 17,
            '10': 18,
            '11': 18.5,
            '12': 19.5,
            '13': 20,
            '1': 21,
            '2': 22,
            '3': 22.5,
            '4': 23.5,
            '5': 24.5,
            '6': 25.5
            },
    '男': {'2': 21,
          '2.5': 21.5,
          '3': 22,
          '3.5': 22.5,
          '4': 23,
          '4.5': 23.5,
          '5': 24,
          '5.5': 24.5,
          '6': 25,
          '6.5': 25.5,
          '7': 26,
          '7.5': 26.5,
          '8': 27,
          '8.5': 27.5,
          '9': 28,
          '9.5': 28.5,
          '10': 29,
          '10.5': 29.5,
          '11': 30,
          '12': 31,
          '13': 32,
          '14': 33,
          '15': 34,
          '16': 35
          },
    '女': {'2.5': 22,
          '3': 22.5,
          '3.5': 23,
          '4': 23.5,
          '4.5': 24,
          '5': 24.5,
          '5.5': 25,
          '6': 25.5,
          '6.5': 26,
          '7': 26.5,
          '7.5': 27,
          '8': 27.5,
          '8.5': 28,
          '9': 29
          },
}
KEEN_SIZE_US_TO_JP_DICT = {
    '童': { '4': 11.5,
            '5': 12.5,
            '6': 13.5,
            '7': 14.5,
            '8': 15,
            '9': 16,
            '10': 17,
            '11': 18,
            '12': 18.5,
            '13': 19.5,
            '1': 20,
            '2': 21,
            '3': 22,
            '4': 22.5,
            '5': 23.5,
            '6': 24.5,
            '7': 25.5
            },
    '男': {'3': 21,
          '3.5': 21.5,
          '4': 22,
          '4.5': 22.5,
          '5': 23,
          '5.5': 23.5,
          '6': 24,
          '6.5': 24.5,
          '7': 25,
          '7.5': 25.5,
          '8': 26,
          '8.5': 26.5,
          '9': 27,
          '9.5': 27.5,
          '10': 28,
          '10.5': 28.5,
          '11': 29,
          '11.5': 29.5,
          '12': 30,
          '13': 31,
          '14': 32,
          '15': 33,
          '16': 34,
          '17': 35
          },
    '女': {'5': 22,
          '5.5': 22.5,
          '6': 23,
          '6.5': 23.5,
          '7': 24,
          '7.5': 24.5,
          '8': 25,
          '8.5': 25.5,
          '9': 26,
          '9.5': 26.5,
          '10': 27,
          '10.5': 27.5,
          '11': 28,
          '12': 29
          },
}
KEEN_SIZE_ENCODE_DICT = {
    'EU': KEEN_SIZE_EU_TO_JP_DICT,
    'UK': KEEN_SIZE_UK_TO_JP_DICT,
    'US': KEEN_SIZE_US_TO_JP_DICT
}
KEEN_ENCODE_LIST = ['JP', 'EU', 'US', 'UK']


def keen_get_encode(encode):
    if encode in KEEN_ENCODE_LIST:
        return encode
    else:
        return None


def keen_size_convert(size, size_key, encode):
    jp_size = None
    if encode:
        if encode == 'JP' and common_util.is_number(size):
            jp_size = size
        elif encode == 'JP':
            jp_size = None
        else:
            for key in KEEN_SIZE_EU_TO_JP_DICT.keys():
                if key in size_key:
                    jp_size = KEEN_SIZE_ENCODE_DICT.get(encode).get(key).get(str(size), None)
                    break
    else:
        if '童' in size_key:
            jp_size = None
        else:
            if common_util.is_number(size):
                jp_size = size
            else:
                jp_size = None
    return jp_size

def onitsukatiger_build_full_conversion_table():
    table = {}
    common_sizes = [
        (12, 19.5), (13, 21), (13.5, 22.5), (14.5, 23.5), (15, 25),
        (16, 26), (17, 27), (17.5, 28.5), (18.5, 30), (19.5, 31.5),
        (20, 32.5), (20.5, 33), (21, 33.5), (21.5, 34.5), (22, 35),
        (23, 37), (23.5, 37.5), (24, 38), (24.5, 39), (25, 39.5),
        (25.5, 40.5), (26, 41.5), (26.5, 42), (27, 42.5), (27.5, 43.5),
        (28, 44), (28.25, 44.5), (28.5, 45), (29, 46), (29.5, 46.5),
        (30, 47), (30.5, 48), (30.75, 48.5), (31, 49)
    ]
    for jp, eu in common_sizes:
        table[eu] = {'男款': jp, '女款': jp}

    table[35.5] = {'男款': 0, '女款': 22.5}
    table[36] = {'男款': 22.5, '女款': 22.75}
    table[40] = {'男款': 25.25, '女款': 25.5}
    table[40.5] = {'男款': 25.5, '女款': 25.75}
    return table

def onitsukatiger_parse_specs_optimized(raw_spec_cell, gender_flag):
    results = None
    conv_table = onitsukatiger_build_full_conversion_table()


    if isinstance(raw_spec_cell, str):
        raw_cell = raw_spec_cell.strip()

        # --- 1. 尝试匹配 JP 原生数据 ---
        jp_matches = re.findall(r'JP\s*(\d+(?:\.\d+)?)', raw_cell, re.IGNORECASE)
        if jp_matches: # 如果匹配到了 JP
            for val in jp_matches:
                size_num = float(val)
                size_str = f"{size_num:g}"
                results = {
                    'Raw_Source': raw_cell,
                    'Standard': 'JP',
                    'Size': size_str
                }
        else:
            # --- 2. 尝试匹配 EU 数据 ---
            eu_matches = re.findall(r'EU\s*(\d+(?:\.\d+)?)', raw_cell, re.IGNORECASE)
            if eu_matches: # 如果匹配到了 EU
                for val in eu_matches:
                    eu_num = float(val)
                    if eu_num in conv_table:
                        jp_size = conv_table[eu_num][gender_flag]
                        size_str = f"{jp_size:g}"
                        results = {
                            'Raw_Source': raw_cell,
                            'Standard': 'JP',
                            'Size': size_str
                        }
                    else:
                        results = {
                            'Raw_Source': raw_cell,
                            'Standard': 'ERROR',
                            'Size': f'EU{eu_num}_Not_Found'
                        }
            else:
                # --- 3. 尝试匹配 SIZE 110/120/130/140 儿童码 ---
                size_matches = re.findall(r'SIZE\s*(\d+)', raw_cell, re.IGNORECASE)
                if size_matches: # 如果匹配到了 SIZE
                    for val in size_matches:
                        size_out = int(val)
                        size_str = str(int(val))
                        results = {
                            'Raw_Source': raw_cell,
                            'Standard': 'KIDS',
                            'Size': size_str
                        }
                else:
                    # --- 4. 尝试匹配 S/M/L 时尚码 ---
                    fashions = re.findall(r'\b(S|M|L|XL|XXL|XS)\b', raw_cell, re.IGNORECASE)
                    for code in fashions:
                        results = {
                            'Raw_Source': raw_cell,
                            'Standard': 'FASHION',
                            'Size': code.upper()
                        }

    return results

def converse_eu_to_jp(eu_size):
    """
    将 EU (欧洲码) 转换为 JP (日本码)。
    基于上传的 converse尺码表.xlsx 数据构建映射。

    参数:
        eu_size: int 或 float, 欧洲尺码 (如 34, 35, 36.5)

    返回:
        float: 对应的日本尺码 (如 21.0, 22.0, 22.5)，如果未找到则返回 None
    """

    # 1. 构建 EU 到 JP 的映射字典
    # 数据来源：converse尺码表.xlsx
    # 格式：EU: JP
    eu_to_jp_map = {
        "34": 21.0,
        "35": 22.0,
        "36": 22.5,
        "36.5": 23.0,
        "37": 23.5,
        "37.5": 24.0,
        "38": 24.5, # 注意：文档中 38 对应两个 JP 值 (24.5 和 25)，这里取第一个
        "39": 24.5, # 这一行对应 JP 24.5 (US 6)
        "39.5": 25.0,
        "40": 25.5,
        "41": 26.0,
        "41.5": 26.5,
        "42": 27.0,
        "42.5": 27.5,
        "43": 28.0,
        "44": 28.5,
        "44.5": 29.0,
        "45": 29.5,
        "46": 30.0,
        "46.5": 30.5,
        "48": 31.5,
        "49": 32.0,
        "50": 33.0,
        "51.5": 34.0
    }

    # 2. 查询并返回结果
    # 如果 eu_size 不在字典中，get 方法会返回 None
    return eu_to_jp_map.get(eu_size)
