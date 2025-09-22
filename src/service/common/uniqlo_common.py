import time

import copy
import json
import traceback
from lxml import etree
from selenium.common import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from constant import brand, shop
from exception.TemplateError import TemplateError
from util import log_util, crawler_util, env_util, yaml_util, common_utils


def sprider(item_codes, targets, object='stock'):
    output_data_list = []
    driver = None
    try:
        if item_codes and targets:
            uniqlo_hosts = yaml_util.get_brand_hosts(brand.UNIQLO_BRAND)
            for target in targets:
                if target in uniqlo_hosts:
                    log_util.info(f"网站{target}脚本processing")
                    if object == 'stock':
                        for item_code in item_codes:
                            sku_file = copy.deepcopy(item_code)
                            code = common_utils.convert_sku_to_code(item_code)
                            color_file = common_utils.convert_sku_to_color(item_code)
                            size_file = common_utils.convert_sku_to_size(item_code)
                            item_code = copy.deepcopy(common_utils.convert_sku_to_code_color(item_code))
                            if item_code == code:
                                output_data_list.append({'item_code': item_code, 'url': '商品sku无效', 'sku': sku_file})
                                log_util.error(f"sku无效,商品{sku_file}数据无法获取")
                                continue
                            item_data_list = []
                            item_data = {'item_code': item_code}
                            actions = yaml_util.get_object_price_actions_top(brand=brand.UNIQLO_BRAND, host=target)
                            log_util.info(f"商品{sku_file}脚本processing")
                            for action in actions:
                                if action['action_type'] == 'dynamic':
                                    if not driver:
                                        driver = crawler_util.get_driver(env_util.get_env('DRIVER_MODE'))
                                    if action['url']:
                                        driver.get(action['url'].replace('%item_code%', str(item_code)))
                                    if action['action'] == "click and get":
                                        try:
                                            current_path = action['path']['check-product-exists']
                                            WebDriverWait(driver, 10).until(
                                                EC.element_to_be_clickable((By.XPATH, current_path))
                                            )
                                            output_data_list.append(
                                                {'item_code': item_code, 'url': '商品无货', 'sku': sku_file})
                                            log_util.error(f"检索不到商品,商品{sku_file}数据无法获取")
                                            break
                                        except TimeoutException as te:
                                            pass
                                        # click search item
                                        try:
                                            current_path = action['path']['item_click']
                                            search_item_element = WebDriverWait(driver, 10).until(
                                                EC.element_to_be_clickable((By.XPATH, current_path))
                                            )
                                            search_item_element.click()
                                        except TimeoutException as te:
                                            output_data_list.append(
                                                {'item_code': item_code, 'url': '无法检索商品', 'sku': sku_file})
                                            log_util.error(
                                                f"检索商品页面加载出错,无法检索到商品{sku_file}, {''.join(traceback.format_exception(None, te, te.__traceback__))}")
                                            break
                                        except ElementClickInterceptedException as ecie:
                                            output_data_list.append(
                                                {'item_code': item_code, 'url': '无法跳转商品页面', 'sku': sku_file})
                                            log_util.error(
                                                f"无法点击检索到商品,跳转到商品{sku_file}页面失败, {''.join(traceback.format_exception(None, ecie, ecie.__traceback__))}")
                                            break
                                        # color,size遍历
                                        if 'actions' in action and action['actions'] and len(action['actions']) > 0:
                                            for action_l_1 in action['actions']:
                                                item_data.update({'size': '', 'color': ''})
                                                current_path = action_l_1['path']['color-id-value']
                                                try:
                                                    color_elements = WebDriverWait(driver, 10).until(
                                                        EC.presence_of_all_elements_located((By.XPATH, current_path))
                                                    )
                                                except TimeoutException as te:
                                                    output_data_list.append(
                                                        {'item_code': item_code, 'url': '商品color获取失败', 'sku': sku_file})
                                                    log_util.error(
                                                        f"商品{sku_file} color获取失败, {''.join(traceback.format_exception(None, te, te.__traceback__))}")
                                                    break
                                                for color_element in color_elements:
                                                    color_id = color_element.get_attribute('id').split('-')[0].replace(' ', '')
                                                    if color_id in color_file:
                                                        color = color_id
                                                        item_data.update({'color': color})
                                                        color_code = color_element.get_attribute('value')
                                                        color_element.click()
                                                        break
                                                    else:
                                                        color = None
                                                if color:
                                                    if size_file:
                                                        current_path = action_l_1['path']['size-id-value']
                                                        try:
                                                            size_elements = WebDriverWait(driver, 10).until(
                                                                EC.visibility_of_all_elements_located((By.XPATH, current_path))
                                                            )
                                                        except TimeoutException as te:
                                                            output_data_list.append(
                                                                {'item_code': item_code, 'url': '商品size获取失败', 'sku': sku_file})
                                                            log_util.error(
                                                                f"商品{sku_file} size获取失败, {''.join(traceback.format_exception(None, te, te.__traceback__))}")
                                                            break
                                                        for size_element in size_elements:
                                                            size_id = size_element.get_attribute('id').split('-')[0]
                                                            if size_id in size_file.replace('MEN', '').replace('WOMEN', '').replace('KIDS', '').replace('BABY', ''):
                                                                size = size_id
                                                                item_data.update({'size': size})
                                                                size_code = size_element.get_attribute('value')
                                                                size_element.click()
                                                                break
                                                            else:
                                                                size = None
                                                        if size is None:
                                                            output_data_list.append(
                                                                {'item_code': item_code, 'url': f'商品size不匹配，根据数据文件SKU解析size:{size_file.replace("MEN", "").replace("WOMEN", "").replace("KIDS", "").replace("BABY", "")}', 'sku': sku_file})
                                                            log_util.error(
                                                                f"商品{sku_file} color不匹配, 根据数据文件SKU解析size:{size_file.replace('MEN', '').replace('WOMEN', '').replace('KIDS', '').replace('BABY', '')}")
                                                            break
                                                    else:
                                                        log_util.info(f"商品{sku_file}没有size指定，不遍历页面size")
                                                    item_url = driver.current_url
                                                    item_data.update({'url':item_url})
                                                else:
                                                    output_data_list.append(
                                                        {'item_code': item_code, 'url': f'商品color不匹配，根据数据文件SKU解析color:{color_file}', 'sku': sku_file})
                                                    log_util.error(
                                                        f"商品{sku_file} color不匹配, 根据数据文件SKU解析color:{color_file}")
                                                    break
                                                if 'actions' in action_l_1 and action_l_1['actions'] and len(action_l_1['actions']) > 0:
                                                    for action_l_2 in action_l_1['actions']:
                                                        l2_id_url = action_l_2['url'].replace('%code%', code)
                                                        driver.get(l2_id_url)
                                                        html_l2_id = driver.page_source.encode("utf-8", "ignore").decode("utf-8")
                                                        tree = etree.HTML(html_l2_id)
                                                        if tree is not None:
                                                            l2_id_json = json.loads(tree.xpath(action_l_2['path']['l2Id'])[0])
                                                            if common_utils.deep_key_check(l2_id_json, ["status"]):
                                                                if l2_id_json['status'] == 'ok':
                                                                    if common_utils.deep_key_check(l2_id_json, ["result", "l2s"]):
                                                                        l2s = l2_id_json['result']['l2s']
                                                                        l2_id = None
                                                                        if l2s:
                                                                            for l2 in l2s:
                                                                                if color_code == l2['color']['displayCode']:
                                                                                    if size_code:
                                                                                        if size_code == l2['size']['displayCode']:
                                                                                            l2_id = l2['l2Id']
                                                                                            break
                                                                                    else:
                                                                                        l2_id = l2['l2Id']
                                                                                        break
                                                                            if l2_id:
                                                                                item_data.update({'l2Id':str(l2_id)})
                                                                                if 'actions' in action_l_2 and action_l_2['actions'] and len(action_l_2['actions']) > 0:
                                                                                    for action_l_3 in action_l_2['actions']:
                                                                                        stock_url = action_l_3['url'].replace('%l2Id%', str(l2_id))
                                                                                        driver.get(stock_url)
                                                                                        html_stock = driver.page_source.encode("utf-8", "ignore").decode("utf-8")
                                                                                        tree_stock = etree.HTML(html_stock)
                                                                                        if tree_stock is not None:
                                                                                            stock_json = json.loads(tree_stock.xpath(action_l_3['path']['stock'])[0])
                                                                                            if common_utils.deep_key_check(stock_json, ["status"]):
                                                                                                if stock_json['status'] == 'ok':
                                                                                                    if common_utils.deep_key_check(stock_json, ["result", "stores"]):
                                                                                                        stores = stock_json['result']['stores']
                                                                                                        if stores:
                                                                                                            for key, value in shop.UNIQLO_SHOP_DICT.items():
                                                                                                                item_data.update({value: '网页没有匹配到店铺ID，stock数据无法获取'})
                                                                                                                for store in stores:
                                                                                                                    if store['storeId'] == key:
                                                                                                                        if store['storeName'] == value:
                                                                                                                            item_data.update({store['storeName']: store['stockStatus']})
                                                                                                                        else:
                                                                                                                            item_data.update({value: '店铺ID，店铺名定义同网页返回不一致, stock数据无法获取'})
                                                                                                                        break
                                                                                                        else:
                                                                                                            item_data = {'item_code': item_code, 'url': item_url, 'size': size, 'color': color, 'l2Id': l2_id, 'sku': sku_file}
                                                                                                            for shop_name in shop.UNIQLO_SHOP_DICT.values():
                                                                                                                item_data.update({shop_name: "检索商品库存数据出错"})
                                                                                                            log_util.error(f"{stock_url}返回数据结果不正确，商品{sku_file}.stores无数据，api返回数据：{stock_json}")
                                                                                                            break
                                                                                                    else:
                                                                                                        item_data = {'item_code': item_code, 'url': item_url, 'size': size, 'color': color, 'l2Id': l2_id, 'sku': sku_file}
                                                                                                        for shop_name in shop.UNIQLO_SHOP_DICT.values():
                                                                                                            item_data.update({shop_name: "检索商品库存数据出错"})
                                                                                                        log_util.error(f"{stock_url}返回数据结果不正确，商品{sku_file}，api返回数据：{stock_json}")
                                                                                                        break
                                                                                                else:
                                                                                                    item_data = {'item_code': item_code, 'url': item_url, 'size': size, 'color': color, 'l2Id': l2_id, 'sku': sku_file}
                                                                                                    for shop_name in shop.UNIQLO_SHOP_DICT.values():
                                                                                                        item_data.update({shop_name: "检索商品库存数据出错"})
                                                                                                    log_util.error(f"{stock_url}返回数据结果不正确，商品{sku_file}，api返回数据：{stock_json}")
                                                                                                    break
                                                                                            else:
                                                                                                item_data = {'item_code': item_code, 'url': item_url, 'size': size, 'color': color, 'l2Id': l2_id, 'sku': sku_file}
                                                                                                for shop_name in shop.UNIQLO_SHOP_DICT.values():
                                                                                                    item_data.update({shop_name: "检索商品库存数据出错"})
                                                                                                log_util.error(f"{stock_url}返回数据无法正确解析，商品{sku_file}.status数据无法获取，api返回数据：{stock_json}")
                                                                                                break
                                                                                        else:
                                                                                            item_data = {'item_code': item_code, 'url': item_url, 'size': size, 'color': color, 'l2Id': l2_id, 'sku': sku_file}
                                                                                            for shop_name in shop.UNIQLO_SHOP_DICT.values():
                                                                                                item_data.update({shop_name: "检索商品库存数据出错"})
                                                                                            log_util.error(f"{stock_url}返回HTML无法解析，商品{sku_file}.stock数据无法获取，html：{html_stock}")
                                                                                            break
                                                                            else:
                                                                                item_data = {'item_code': item_code, 'url': item_url, 'size': size, 'color': color, 'l2Id': 'l2Id数据无法解析', 'sku': sku_file}
                                                                                log_util.error(f"{l2_id_url}返回数据结果没有匹配到color size无法解析l2Id，商品{sku_file}，api返回数据：{l2_id_json}，color_code：{color_code}， size_code：{size_code}")
                                                                                break

                                                                else:
                                                                    item_data = {'item_code': item_code, 'url': item_url, 'size': size, 'color': color, 'l2Id': 'l2Id数据无法获取', 'sku': sku_file}
                                                                    log_util.error(f"{l2_id_url}返回数据结果不正确，商品{sku_file}，api返回数据：{l2_id_json}")
                                                                    break
                                                            else:
                                                                item_data = {'item_code': item_code, 'url': item_url, 'size': size, 'color': color, 'l2Id': 'l2Id数据无法获取', 'sku': sku_file}
                                                                log_util.error(f"{l2_id_url}返回数据无法正确解析，商品{sku_file}.status数据无法获取，api返回数据：{l2_id_json}")
                                                                break
                                                        else:
                                                            item_data = {'item_code': item_code, 'url': item_url, 'size': size, 'color': color, 'l2Id': 'l2Id数据无法获取', 'sku': sku_file}
                                                            log_util.error(f"{l2_id_url}返回HTML无法解析，商品{sku_file}.l2Id数据无法获取，html：{html_l2_id}")
                                                            break
                                                item_data_list.append(copy.deepcopy(item_data))
                                        else:
                                            item_data_list.append(copy.deepcopy(item_data))
                                            log_util.error(
                                                f"模板文件的color size的action定义错误，商品{sku_file}数据无法获取，action：{action}")
                                            output_data_list.extend(item_data_list)
                                            raise TemplateError()
                            output_data_list.extend(item_data_list)
                            log_util.info(f"商品{sku_file}脚本processed")
                    elif object == 'replenish':
                        for item_code in item_codes:
                            actions = yaml_util.get_object_actions_top(brand=brand.UNIQLO_BRAND, host=target, o=object)
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
                                            current_path = action['path']['stock']
                                            element_stock = WebDriverWait(driver, 10).until(
                                                EC.visibility_of_element_located((By.XPATH, current_path))
                                            )
                                            stock = element_stock.text
                                        except TimeoutException as te:
                                            log_util.error(
                                                f"商品{item_code}库存获取失败:{''.join(traceback.format_exception(None, te, te.__traceback__))}")
                                            stock = ''
                                        try:
                                            current_path = action['path']['price']
                                            element = WebDriverWait(driver, 10).until(
                                                EC.visibility_of_element_located((By.XPATH, current_path))
                                            )
                                            price = element.text
                                        except TimeoutException as te:
                                            log_util.error(
                                                f"商品{item_code}价格获取失败:{''.join(traceback.format_exception(None, te, te.__traceback__))}")
                                            price = ''
                                        except NoSuchElementException as nsee:
                                            log_util.error(
                                                f"商品{item_code}价格获取失败:{''.join(traceback.format_exception(None, nsee, nsee.__traceback__))}")
                                            price = ''
                                        item_data = {'url': item_code, '官网库存': stock, 'price': price}
                                        item_data_list.append(copy.deepcopy(item_data))
                            output_data_list.extend(item_data_list)
                            log_util.info(f"商品{item_code}脚本processed")
                    log_util.info(f"网站{target}脚本processed")
                else:
                    log_util.info(f"{brand.UNIQLO_BRAND}品牌没有{env_util.get_env('EXCEL_INPUT_FILE')}文件指定{target}网站脚本定义")
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
