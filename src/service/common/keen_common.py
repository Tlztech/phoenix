import time

import copy
import json
import traceback
from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from constant import brand
from exception.TemplateError import TemplateError
from util import log_util, crawler_util, env_util, yaml_util


def sprider(item_codes, targets):
    output_data_list = []
    driver = None
    try:
        if item_codes and targets:
            keen_hosts = yaml_util.get_brand_hosts(brand.KEEN_BRAND)
            for target in targets:
                if target in keen_hosts:
                    log_util.info(f"网站{target}脚本processing")
                    for item_code in item_codes:
                        actions = yaml_util.get_object_price_actions_top(brand=brand.KEEN_BRAND, host=target)
                        item_data_list = []
                        log_util.info(f"商品{item_code}脚本processing")
                        for action in actions:
                            if action['action_type'] == 'dynamic':
                                if not driver:
                                    driver = crawler_util.get_driver("INFO")
                                driver.delete_all_cookies()
                                action['url'] = item_code
                                driver.get(item_code)
                                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                                if action['action'] == "get":
                                    stock = ''
                                    size = ''
                                    color = ''
                                    try:
                                        current_path = action['path']['color']
                                        element_color = WebDriverWait(driver, 10).until(
                                            EC.visibility_of_element_located((By.XPATH, current_path))
                                        )
                                        color = element_color.text
                                    except TimeoutException as te:
                                        log_util.error(f"商品{item_code}color获取失败:{''.join(traceback.format_exception(None, te, te.__traceback__))}")
                                        color = ''
                                    try:
                                        current_path = action['path']['size-list']
                                        elements = WebDriverWait(driver, 30).until(
                                            EC.presence_of_all_elements_located((By.XPATH, current_path))
                                        )
                                        for element in elements:
                                            current_path = action['path']['size']
                                            size = element.get_attribute(current_path)
                                            current_path = action['path']['stock']
                                            stock = element.get_attribute(current_path)
                                            if stock == 'out-stock':
                                                stock = '在庫なし'
                                            elif stock == 'in-stock':
                                                stock = '在庫有り'
                                            else:
                                                stock = ''
                                            item_data = {'url': item_code, '官网库存': stock, 'size': size, 'color': color}
                                            item_data_list.append(copy.deepcopy(item_data))
                                    except TimeoutException as te:
                                        log_util.error(f"商品{item_code} size list获取失败:{''.join(traceback.format_exception(None, te, te.__traceback__))}")
                                        item_data = {'url': item_code, '官网库存': stock, 'size': size, 'color': color}
                                        item_data_list.append(copy.deepcopy(item_data))
                        output_data_list.extend(item_data_list)
                        log_util.info(f"商品{item_code}脚本processed")
                    log_util.info(f"网站{target}脚本processed")
                else:
                    log_util.info(f"{brand.KEEN_BRAND}品牌没有{env_util.get_env('EXCEL_INPUT_FILE')}文件指定{target}网站脚本定义")
                return output_data_list
        else:
            log_util.info(f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整，数据处理停止")
    except TemplateError:
        log_util.error("模板文件发生错误，数据处理停止")
    except Exception as e:
        log_util.error(f"发生未知错误，数据处理停止: {''.join(traceback.format_exception(None, e, e.__traceback__))}")
    finally:
        if driver:
            crawler_util.close_driver(driver)
        log_util.info(json.dumps(output_data_list, indent=4, ensure_ascii=False))
