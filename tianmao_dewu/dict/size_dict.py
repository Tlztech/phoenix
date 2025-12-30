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
    '童': {},
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
    '童': {},
    '女': {},
    '男': {}
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
