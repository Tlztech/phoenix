# -*- coding: utf-8 -*-
import time
import traceback
import json


from service.common.lululemon_common import sprider
from util import excel_util, log_util, mail_util, env_util, common_utils
from constant import brand, excel

def service():
    log_util.info(f"品牌{brand.LULULEMON_BRAND}价格变动检查脚本processing")
    item_codes = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('item_code'), excel.COLUMNS_NAMES)
    targets = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('target'), excel.COLUMNS_NAMES)
    prices = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('price'), excel.COLUMNS_NAMES)
    intervals = excel_util.get_data_list_no_none(excel.COLUMNS_NAMES.index('interval'), excel.COLUMNS_NAMES)

    if not item_codes:
        error_msg = f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整没有item_code，数据处理停止"
        log_util.error(error_msg)
        # notify error with mail
        mail_util.send_message("价格变动检查处理错误信息", error_msg)
        log_util.info(f"品牌{brand.LULULEMON_BRAND}价格变动检查脚本processed")
    elif not targets:
        error_msg = f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整没有target，数据处理停止"
        log_util.error(error_msg)
        # notify error with mail
        mail_util.send_message("价格变动检查处理错误信息", error_msg)
        log_util.info(f"品牌{brand.LULULEMON_BRAND}价格变动检查脚本processed")
    elif not prices:
        error_msg = f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整没有price，数据处理停止"
        log_util.error(error_msg)
        # notify error with mail
        mail_util.send_message("价格变动检查处理错误信息", error_msg)
        log_util.info(f"品牌{brand.LULULEMON_BRAND}价格变动检查脚本processed")
    elif len(item_codes) != len(prices):
        error_msg = f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整item_code,price数量不匹配，数据处理停止"
        log_util.error(error_msg)
        # notify error with mail
        mail_util.send_message("价格变动检查处理错误信息", error_msg)
        log_util.info(f"品牌{brand.LULULEMON_BRAND}价格变动检查脚本processed")
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
        prices_last = []
        for price in prices:
            try:
                prices_last.append(int(price))
            except ValueError:
                prices_last.append(0)
                log_util.info(f"无效的价格: {price},按0处理")
        if interval > 0:
            log_util.info(f"脚本已启动，每隔 {interval} 分执行一次...")
        else:
            log_util.info(f"脚本已启动，执行一次...")
        try:
            while interval >= 0:
                try:
                    output_data_list = sprider(item_codes, targets)
                    if len(output_data_list) > 0:
                        output_filtered_list = []
                        invalid = True
                        for item_code in item_codes:
                            for output_data in output_data_list:
                                if item_code == output_data['sku']:
                                    invalid = False
                                    output_filtered_list.append(output_data)
                                    break
                            if invalid:
                                output_filtered_list.append({'item_code': item_code, 'url': '商品无效'})
                            else:
                                invalid = True
                        if output_filtered_list:
                            # price change
                            output_mail_list = []
                            for index, output_data in enumerate(output_filtered_list):
                                if int(output_data['price']) != prices_last[index]:
                                    output_data.update({'price_last': prices_last[index]})
                                    prices_last[index] = int(output_data['price'])
                                    output_mail_list.append(output_data)
                            # mail
                            output_mail_str = json.dumps(output_mail_list, indent=4, ensure_ascii=False)
                            log_util.info(f"output_mail_list:{output_mail_str}")
                            if output_mail_list:
                                byte_data = common_utils.generate_excel_friendly_csv(common_utils.transform_dict_to_list(output_mail_list))
                                log_util.info(f"mail:{bytes.decode(byte_data)}")
                                mail_util.send_csv_attachment("价格变动检查", byte_data)
                        else:
                            log_util.info("没有符合入力sku的数据写入到邮件")
                    else:
                        log_util.info("没有数据写入到邮件")
                except Exception as e:  # 捕获服务调用中的异常
                    if interval == 0:
                        error_msg = f"脚本执行失败, 处理停止: {''.join(traceback.format_exception(None, e, e.__traceback__))}"
                    else:
                        error_msg = f"脚本执行失败, 间隔{interval}分，处理再次执行: {''.join(traceback.format_exception(None, e, e.__traceback__))}"
                    log_util.error(error_msg)
                    # notify error with mail
                    mail_util.send_message("价格变动检查处理错误信息", error_msg)
                if interval > 0:
                    time.sleep(interval*60)
                else:
                    break
        except KeyboardInterrupt:
            log_util.info("\n脚本已停止")
        finally:
            log_util.info(f"品牌{brand.LULULEMON_BRAND}价格变动检查脚本processed")
