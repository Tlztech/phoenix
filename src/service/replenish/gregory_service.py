import copy
import time
import traceback
import json

from constant import brand, excel
from service.common.gregory_common import sprider
from util import log_util, excel_util, env_util, mail_util, common_utils


def service():
    log_util.info(f"品牌{brand.GREGORY_BRAND}补货检查脚本processing")
    item_codes = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('url'), excel.COLUMNS_NAMES)
    targets = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('target'), excel.COLUMNS_NAMES)
    intervals = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('interval'), excel.COLUMNS_NAMES)
    prices = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('price'), excel.COLUMNS_NAMES)
    if not item_codes:
        error_msg = f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整没有item_code，数据处理停止"
        log_util.error(error_msg)
        # notify error with mail
        mail_util.send_message("补货检查处理错误信息", error_msg)
        log_util.info(f"品牌{brand.GREGORY_BRAND}补货检查脚本processed")
    elif not targets:
        error_msg = f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整没有target，数据处理停止"
        log_util.error(error_msg)
        # notify error with mail
        mail_util.send_message("补货检查处理错误信息", error_msg)
        log_util.info(f"品牌{brand.GREGORY_BRAND}补货检查脚本processed")
    elif not prices:
        error_msg = f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整没有price，数据处理停止"
        log_util.error(error_msg)
        # notify error with mail
        mail_util.send_message("补货检查处理错误信息", error_msg)
        log_util.info(f"品牌{brand.GREGORY_BRAND}补货检查脚本processed")
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
        if interval > 0:
            log_util.info(f"脚本已启动，每隔 {interval} 分执行一次...")
        else:
            log_util.info(f"脚本已启动，执行一次...")
        try:
            while interval >= 0:
                try:
                    output_data_list = sprider(item_codes, targets)
                    if output_data_list and len(output_data_list) > 0:
                        output_mail_list = []
                        item_codes = []
                        price_list = []
                        error_price_list = []
                        for index, output_data in enumerate(output_data_list):
                            if prices[index] and int(prices[index]) > 0:
                                if not output_data['price']:
                                    error_price_list.append(output_data['url'])
                                elif int(prices[index]) >= common_utils.prices_formatter(output_data['price']) and output_data['官网库存'] and output_data['官网库存'] == '有货':
                                    output_mail_list.append(output_data)
                                else:
                                    item_codes.append(output_data['url'])
                                    price_list.append(prices[index])
                            else:
                                if output_data['官网库存'] and output_data['官网库存'] == '有货':
                                    output_mail_list.append(output_data)
                                else:
                                    item_codes.append(output_data['url'])
                                    price_list.append(prices[index])
                        prices = copy.deepcopy(price_list)
                        # mail
                        output_mail_str = json.dumps(output_mail_list, indent=4, ensure_ascii=False)
                        log_util.info(f"output_mail_list:{output_mail_str}")
                        if output_mail_list:
                            byte_data = common_utils.generate_excel_friendly_csv(common_utils.transform_dict_to_list(output_mail_list))
                            log_util.info(f"mail:{bytes.decode(byte_data)}")
                            mail_util.send_csv_attachment("补货检查", byte_data)
                        if error_price_list:
                            error_msg = f"价格获取失败，请确认这些商品网页{':'.join(error_price_list)}"
                            log_util.error(error_msg)
                            # notify error with mail
                            mail_util.send_message("补货检查处理错误信息", error_msg)
                    else:
                        log_util.info("没有数据写入到邮件")
                except Exception as e:  # 捕获服务调用中的异常
                    if interval == 0:
                        error_msg = f"脚本执行失败, 处理停止: {''.join(traceback.format_exception(None, e, e.__traceback__))}"
                    else:
                        error_msg = f"脚本执行失败, 间隔{interval}分，处理再次执行: {''.join(traceback.format_exception(None, e, e.__traceback__))}"
                    log_util.error(error_msg)
                    # notify error with mail
                    mail_util.send_message("补货检查处理错误信息", error_msg)
                if interval > 0:
                    time.sleep(interval*60)
                else:
                    break
        except KeyboardInterrupt:
            log_util.info("\n脚本已停止")
        finally:
            log_util.info(f"品牌{brand.GREGORY_BRAND}价格变动检查脚本processed")