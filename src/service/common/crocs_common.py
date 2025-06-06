import time

import copy
import json
import traceback
from selenium.common import TimeoutException, NoSuchElementException
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
            crocs_hosts = yaml_util.get_brand_hosts(brand.CROCS_BRAND)
            for target in targets:
                if target in crocs_hosts:
                    log_util.info(f"网站{target}脚本processing")
                    for item_code in item_codes:
                        actions = yaml_util.get_object_price_actions_top(brand=brand.CROCS_BRAND, host=target)
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
                                    try:
                                        current_path = action['path']['price']
                                        element = WebDriverWait(driver, 10).until(
                                            EC.visibility_of_element_located((By.XPATH, current_path))
                                        )
                                        price = element.text
                                    except TimeoutException as te:
                                        log_util.error(f"商品{item_code}价格获取失败:{''.join(traceback.format_exception(None, te, te.__traceback__))}")
                                        price = ''
                                    try:
                                        current_path = action['path']['color']
                                        element_color_list = WebDriverWait(driver, 10).until(
                                            EC.visibility_of_all_elements_located((By.XPATH, current_path))
                                        )
                                        for element_color in element_color_list:
                                            element_color.click()
                                            color = element_color.text
                                            try:
                                                current_path = action['path']['parent']
                                                element_parent_list = WebDriverWait(driver, 10).until(
                                                    EC.visibility_of_all_elements_located((By.XPATH, current_path))
                                                )
                                                for element_parent in element_parent_list:
                                                    try:
                                                        current_path = action['path']['size']
                                                        element_size = element_parent.find_element(By.XPATH, current_path)
                                                        size = element_size.text
                                                    except NoSuchElementException as nsee:
                                                        log_util.error(f"商品{item_code}size获取失败:{''.join(traceback.format_exception(None, nsee, nsee.__traceback__))}")
                                                        size = ''
                                                    try:
                                                        current_path = action['path']['stock']
                                                        element_stock = element_parent.find_element(By.XPATH, current_path)
                                                        stock = element_stock.text
                                                    except NoSuchElementException as nsee:
                                                        stock = '在庫あり'
                                                    item_data = {'url': item_code, '官网库存': stock, 'price': price, 'color': color, 'size': size}
                                                    item_data_list.append(copy.deepcopy(item_data))
                                            except TimeoutException as te:
                                                log_util.error(f"商品{item_code}size, stock获取失败:{''.join(traceback.format_exception(None, te, te.__traceback__))}")
                                                size = ''
                                                stock = ''
                                                item_data = {'url': item_code, '官网库存': stock, 'price': price, 'color': color, 'size': size}
                                                item_data_list.append(copy.deepcopy(item_data))
                                    except TimeoutException as te:
                                        log_util.error(f"商品{item_code}color获取失败:{''.join(traceback.format_exception(None, te, te.__traceback__))}")
                                        color = ''
                                        size = ''
                                        stock = ''
                                        item_data = {'url': item_code, '官网库存': stock, 'price': price, 'color': color, 'size': size}
                                        item_data_list.append(copy.deepcopy(item_data))
                        output_data_list.extend(item_data_list)
                        log_util.info(f"商品{item_code}脚本processed")
                    log_util.info(f"网站{target}脚本processed")
                else:
                    log_util.info(f"{brand.CROCS_BRAND}品牌没有{env_util.get_env('EXCEL_INPUT_FILE')}文件指定{target}网站脚本定义")
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
