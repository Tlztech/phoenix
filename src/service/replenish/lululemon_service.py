from constant import brand, excel
from util import log_util, excel_util, env_util, mail_util


def service():
    log_util.info(f"品牌{brand.LULULEMON_BRAND}补货检查脚本processing")
    item_codes = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('item_code'), excel.COLUMNS_NAMES)
    targets = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('target'), excel.COLUMNS_NAMES)
    intervals = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('interval'), excel.COLUMNS_NAMES)
    if not item_codes:
        error_msg = f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整没有item_code，数据处理停止"
        log_util.error(error_msg)
        # notify error with mail
        mail_util.send_message("补货检查处理错误信息", error_msg)
        log_util.info(f"品牌{brand.LULULEMON_BRAND}补货检查脚本processed")
    elif not targets:
        error_msg = f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整没有target，数据处理停止"
        log_util.error(error_msg)
        # notify error with mail
        mail_util.send_message("补货检查处理错误信息", error_msg)
        log_util.info(f"品牌{brand.LULULEMON_BRAND}补货检查脚本processed")
    else:
        if not intervals:
            interval = 0
            log_util.info(f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整没有INTERVAL数据，不循环执行脚本")
        else:
            try:
                interval = int(intervals[0])
                if interval < 0:
                    log_util.info("间隔时间不能为负数,执行一次不循环执行脚本")
            except ValueError:
                interval = 0
                log_util.info(f"无效的间隔时间: {intervals[0]},执行一次不循环执行脚本")
