import re

def normalize_size(size_str):
    if not size_str:
        return size_str
    s = str(size_str).upper().strip()
    s = re.sub(r'\s+', '', s)

    size_map = {
        '2XL': 'XXL',
        '3XL': 'XXXL',
        '4XL': 'XXXXL',
        '5XL': 'XXXXXL',
        'XS': 'XS',
        'S': 'S',
        'M': 'M',
        'L': 'L',
        'XL': 'XL',
        'XXL': 'XXL',
        'XXXL': 'XXXL',
        # 处理一些特殊的写法
        'DOUBLEXL': 'XXL',
        'TRIPLEXL': 'XXXL',
        'EXTRALARGE': 'XL',
        'DOUBLEEXTRALARGE': 'XXL',
        'LARGE': 'L',
        'MEDIUM': 'M',
        'SMALL': 'S',
        'XSMALL': 'XS',
        # 数字写法映射 (以防万一字典没覆盖)
        '2X': 'XXL',
        '3X': 'XXXL',
    }
    if s in size_map:
        return size_map[s]
    return s
