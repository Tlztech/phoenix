# -*- coding: utf-8 -*-

from service.common.lululemon_common import sprider
from util import excel_util, env_util, log_util
from constant import excel, brand

import json


def service():
    log_util.info(f"品牌{brand.LULULEMON_BRAND}库存检查脚本processing")
    item_codes = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('url'), excel.COLUMNS_NAMES)
    targets = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('target'), excel.COLUMNS_NAMES)
    colors = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('color'), excel.COLUMNS_NAMES)
    sizes = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('size'), excel.COLUMNS_NAMES)
    if item_codes and targets:
        output_data_list = sprider(item_codes, targets)
        if output_data_list and len(output_data_list) > 0:
            output_filtered_list = []
            invalid = True
            for index, item_code in enumerate(item_codes):
                for output_data in output_data_list:
                    if item_code == output_data['url'] and colors[index] == output_data['color'] and sizes[index] == output_data['size']:
                        invalid = False
                        output_filtered_list.append(output_data)
                        break
                if invalid:
                    output_filtered_list.append({'item_code': item_code, 'url': '商品无效'})
                else:
                    invalid = True
            log_util.info(json.dumps(output_filtered_list, indent=4, ensure_ascii=False))
            excel_util.write_excel(env_util.get_env('EXCEL_OUTPUT_FILE'), data=output_filtered_list)
        else:
            log_util.info("没有数据写入到EXCEL")
    else:
        log_util.info(f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整，数据处理停止")
    log_util.info(f"品牌{brand.LULULEMON_BRAND}库存检查脚本processed")
