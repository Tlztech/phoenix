import copy
import json

from constant import brand, shop, excel
from service.common.patagonia_common import sprider
from util import excel_util, log_util, crawler_util, env_util, yaml_util, common_utils


def service():
    log_util.info(f"品牌{brand.PATAGONIA_BRAND}库存检查脚本processing")
    item_codes = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('sku'), excel.COLUMNS_NAMES)
    targets = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('target'), excel.COLUMNS_NAMES)
    if item_codes and targets:
        output_data_list = sprider(item_codes, targets)
        if output_data_list and len(output_data_list) > 0:
            ordered_list = common_utils.reorder_dict(output_data_list, ["item_code", "sku", "url", "size", "color", "price"]+list(shop.PATAGONIA_SHOP_DICT.values()))
            excel_util.write_excel(env_util.get_env('EXCEL_OUTPUT_FILE'), data=ordered_list)
        else:
            log_util.info("没有数据写入到EXCEL")
    else:
        log_util.info(f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整，数据处理停止")
    log_util.info(f"品牌{brand.PATAGONIA_BRAND}库存检查脚本processed")
