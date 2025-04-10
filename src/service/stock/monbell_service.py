# -*- coding: utf-8 -*-
import copy
import json

from service.common.monbell_common import sprider
from util import excel_util, yaml_util, crawler_util, env_util, common_utils, date_util, log_util
from constant import stock, shop, brand, excel


def service():
    log_util.info(f"品牌{brand.MONTBELL_BRAND}库存检查脚本processing")
    item_codes = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('item_code'), excel.COLUMNS_NAMES)
    targets = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('target'), excel.COLUMNS_NAMES)
    if not item_codes:
        error_msg = f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整没有item_code，数据处理停止"
        log_util.error(error_msg)
    elif not targets:
        error_msg = f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整没有target，数据处理停止"
        log_util.error(error_msg)
    else:
        output_data_list = sprider(item_codes, targets)
        if output_data_list and len(output_data_list) > 0:
            excel_util.write_excel(env_util.get_env('EXCEL_OUTPUT_FILE'), data=output_data_list)
        else:
            log_util.info("没有数据写入到EXCEL")
    log_util.info(f"品牌{brand.MONTBELL_BRAND}库存检查脚本processed")
