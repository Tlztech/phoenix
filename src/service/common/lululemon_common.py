import copy
import json
import time
import traceback

from selenium.common import ElementNotInteractableException, TimeoutException, NoSuchElementException, \
    StaleElementReferenceException
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from lxml import etree

from util import excel_util, yaml_util, crawler_util, env_util, common_utils, date_util, log_util, mail_util
from constant import stock, shop, brand, excel
from exception.TemplateError import TemplateError


def sprider(item_codes, targets):
    output_data_list = []
    driver = None
    try:
        if item_codes and targets:
            lululemon_hosts = yaml_util.get_brand_hosts(brand.LULULEMON_BRAND)
            for target in targets:
                if target in lululemon_hosts:
                    log_util.info(f"网站{target}脚本processing")
                    for item_code in item_codes:
                        item_code = str(common_utils.convert_sku_to_code(str(item_code)))
                        actions = yaml_util.get_object_price_actions_top(brand=brand.LULULEMON_BRAND, host=target)
                        log_util.info(f"商品{item_code}脚本processing")
                        item_data_list = []
                        item_data = {'item_code': item_code}
                        for action in actions:
                            if action['action_type'] == 'dynamic':
                                try:
                                    if not driver:
                                        driver = crawler_util.get_driver("INFO")
                                        driver.maximize_window()
                                    if action['url']:
                                        driver.get(action['url'])
                                    if action['action'] == "click":
                                        # 地域选择
                                        current_path = action['path']['location_optional']
                                        try:
                                            element = driver.find_element(By.XPATH, current_path)
                                            if element.is_displayed():
                                                element.click()
                                                time.sleep(1)
                                        except NoSuchElementException as nsee:
                                            pass
                                    elif action['action'] == "input and enter":
                                        # 商品检索
                                        current_path = action['path']['%item_code%']
                                        element = WebDriverWait(driver, 10).until(
                                            EC.visibility_of_element_located((By.XPATH, current_path))
                                        )
                                        element.send_keys(item_code)
                                        time.sleep(0.5)
                                        element.send_keys(Keys.RETURN)
                                        if 'actions' in action and action['actions'] and len(action['actions']) > 0:
                                            for action_l_1 in action['actions']:
                                                item_data.update({'url': '', 'color': '', 'size': '', 'price': ''})
                                                try:
                                                    current_path = list(action_l_1['path'].values())[2]
                                                    driver.find_element(By.XPATH, current_path)
                                                    item_data.update({'url': f"商品{item_code}不存在"})
                                                    log_util.error(f"商品{item_code}不存在")
                                                    break
                                                except NoSuchElementException as nsee:
                                                    # color遍历
                                                    try:
                                                        current_path = list(action_l_1['path'].values())[0]
                                                        color_elements = WebDriverWait(driver, 10).until(
                                                            EC.presence_of_all_elements_located((By.XPATH, current_path))
                                                        )
                                                        color_list = []
                                                        for color_element in color_elements:
                                                            # item url
                                                            url = color_element.get_attribute(list(action_l_1['path'].keys())[0])
                                                            color_title = color_element.get_attribute(list(action_l_1['path'].keys())[1])
                                                            color_title = "".join(color_title.split())
                                                            color_list.append({'url':url, 'color_title': color_title})
                                                        for color in color_list:
                                                            url = color['url']
                                                            color_title = color['color_title']
                                                            item_data.update({'url': url, 'color': color_title})
                                                            if 'actions' in action_l_1 and action_l_1['actions'] and len(action_l_1['actions']) > 0:
                                                                for action_l_2 in action_l_1['actions']:
                                                                    item_data.update({'size': '', 'price': ''})
                                                                    driver.get(url)
                                                                    current_path = list(action_l_2['path'].values())[0]
                                                                    size_elements = WebDriverWait(driver, 10).until(
                                                                        EC.presence_of_all_elements_located((By.XPATH, current_path))
                                                                    )
                                                                    size_url_list = []
                                                                    for size_element in size_elements:
                                                                        # size遍历
                                                                        size = size_element.get_attribute(list(action_l_2['path'].keys())[0])
                                                                        size_num = size_element.get_attribute(list(action_l_2['path'].keys())[2])
                                                                        # sku price
                                                                        sku_url = size_element.get_attribute(list(action_l_2['path'].keys())[1])
                                                                        size_url_list.append({'size': size, 'sku_url': sku_url, 'size_num': size_num})
                                                                    for size_url in size_url_list:
                                                                        item_data.update({'size': '', 'price': ''})
                                                                        for shop_name in shop.LULULEMON_SHOP_DICT.values():
                                                                            item_data.update({shop_name: ''})
                                                                        size = size_url.get('size')
                                                                        size_num = size_url.get('size_num')
                                                                        # no size
                                                                        if size_num == 'ONE SIZE':
                                                                            item_data.update({'size': size, 'sku': f"{item_code.strip()}-{color_title.strip().replace('/', '-')}"})
                                                                        else:
                                                                            item_data.update({'size': size, 'sku': f"{item_code.strip()}-{color_title.strip().replace('/', '-')}-{size_num.strip().replace('/', '-')}"})
                                                                        if 'actions' in action_l_2 and action_l_2['actions'] and len(action_l_2['actions']) > 0:
                                                                            sku_url = size_url.get('sku_url')
                                                                            for action_l_3 in action_l_2['actions']:
                                                                                driver.get(sku_url)
                                                                                html_sku = driver.page_source.encode("utf-8", "ignore").decode("utf-8")
                                                                                tree = etree.HTML(html_sku)
                                                                                if tree is not None:
                                                                                    sku_json = json.loads(tree.xpath(action_l_3['path']['sku'])[0])
                                                                                    if sku_json and 'product' in sku_json:
                                                                                        product = sku_json['product']
                                                                                        if 'id' in product and product['id']:
                                                                                            sku_id = product['id']
                                                                                            if 'price' in product and product['price']:
                                                                                                price_json = product['price']
                                                                                                if 'sales' in price_json and price_json['sales']:
                                                                                                    sales = price_json['sales']
                                                                                                    if 'decimalPrice' in sales and sales['decimalPrice']:
                                                                                                        price = sales['decimalPrice']
                                                                                                        item_data.update({'price': price})
                                                                                                    else:
                                                                                                        log_util.error(f"{sku_url}返回数据无法正确解析decimalPrice，商品{item_code}.price数据无法获取，库存获取继续，api返回数据：{sku_json}")
                                                                                                else:
                                                                                                    log_util.error(f"{sku_url}返回数据无法正确解析sales，商品{item_code}.price数据无法获取，库存获取继续，api返回数据：{sku_json}")
                                                                                            else:
                                                                                                log_util.error(f"{sku_url}返回数据无法正确解析price，商品{item_code}.price数据无法获取，库存获取继续，api返回数据：{sku_json}")
                                                                                            if 'actions' in action_l_3 and action_l_3['actions'] and len(action_l_3['actions']) > 0:
                                                                                                for action_l_4 in action_l_3['actions']:
                                                                                                    stock_url = action_l_4['url'].replace('%sku%', sku_id)
                                                                                                    driver.get(stock_url)
                                                                                                    stock_html = driver.page_source.encode("utf-8", "ignore").decode("utf-8")
                                                                                                    tree = etree.HTML(stock_html)
                                                                                                    if tree is not None:
                                                                                                        stock_json = json.loads(tree.xpath(action_l_4['path']['stock'])[0])
                                                                                                        if stock_json and 'stores' in stock_json:
                                                                                                            for store in stock_json['stores']:
                                                                                                                for key, value in shop.LULULEMON_SHOP_DICT.items():
                                                                                                                    if store['ID'] == str(key):
                                                                                                                        if 'supply' in store and store['supply'] and 'message' in store['supply'] and store['supply']['message']:
                                                                                                                            if store['supply']['message'] == 'available':
                                                                                                                                item_data.update({value: '在庫あり'})
                                                                                                                            elif store['supply']['message'] == 'onlyfewleft':
                                                                                                                                item_data.update({value: '残りわずか'})
                                                                                                                            else:
                                                                                                                                item_data.update({value: ''})
                                                                                                                        else:
                                                                                                                            item_data.update({value: "检索商品库存数据出错"})
                                                                                                                            log_util.error(f"{stock_url}返回数据无法正确解析supply，商品{item_code}的店铺{value}.stock数据无法获取，api返回数据：store")
                                                                                                        else:
                                                                                                            for shop_name in shop.LULULEMON_SHOP_DICT.values():
                                                                                                                item_data[shop_name] = "检索商品库存数据出错"
                                                                                                            log_util.error(f"{stock_url}返回数据无法正确解析stores，商品{item_code}.stock数据无法获取，api返回数据：{stock_json}")
                                                                                                    else:
                                                                                                        log_util.error(f"{stock_url}返回HTML无法解析，商品{item_code}.stock数据无法获取，html：{stock_html}")
                                                                                            else:
                                                                                                item_data_list.append(copy.deepcopy(item_data))
                                                                                                log_util.error(f"模板文件的stock的action定义错误，商品{item_code}数据无法获取，action：{action_l_4}")
                                                                                                output_data_list.extend(item_data_list)
                                                                                                raise TemplateError()
                                                                                        else:
                                                                                            log_util.error(f"{sku_url}返回数据无法正确解析id，商品{item_code}.price.stock数据无法获取，api返回数据：{sku_json}")
                                                                                    else:
                                                                                        log_util.error(f"{sku_url}返回数据无法正确解析product，商品{item_code}.price.stock数据无法获取，api返回数据：{sku_json}")
                                                                                else:
                                                                                    log_util.error(f"{sku_url}返回HTML无法解析，商品{item_code}.price.stock数据无法获取，html：{html_sku}")
                                                                        else:
                                                                            item_data_list.append(copy.deepcopy(item_data))
                                                                            log_util.error(f"模板文件的sku的action定义错误，商品{item_code}数据无法获取，action：{action_l_2}")
                                                                            output_data_list.extend(item_data_list)
                                                                            raise TemplateError()
                                                                        item_data_list.append(copy.deepcopy(item_data))
                                                            else:
                                                                item_data_list.append(copy.deepcopy(item_data))
                                                                log_util.error(f"模板文件的size的action定义错误，商品{item_code}数据无法获取，action：{action_l_1}")
                                                                output_data_list.extend(item_data_list)
                                                                raise TemplateError()
                                                    except TimeoutException as toe:
                                                        item_data_list.append(copy.deepcopy(item_data))
                                                        log_util.error(f"标签元素未加载，商品{item_code}数据无法获取，{''.join(traceback.format_exception(None, toe, toe.__traceback__))}")
                                                        break
                                        else:
                                            item_data_list.append(copy.deepcopy(item_data))
                                            log_util.error(f"模板文件的color的action定义错误，商品{item_code}数据无法获取，action：{action}")
                                            output_data_list.extend(item_data_list)
                                            raise TemplateError()
                                except NoSuchElementException as nsee:
                                    item_data_list.append(copy.deepcopy(item_data))
                                    log_util.error(f"url:{driver.current_url}页面没有{current_path}标签，商品{item_code}数据无法获取，{''.join(traceback.format_exception(None, nsee, nsee.__traceback__))}")
                                    break
                                except StaleElementReferenceException as sere:
                                    item_data_list.append(copy.deepcopy(item_data))
                                    log_util.error(f"url:{driver.current_url}页面没有{current_path}标签，商品{item_code}数据无法获取，{''.join(traceback.format_exception(None, sere, sere.__traceback__))}")
                                    break
                                except ElementNotInteractableException as enie:
                                    item_data_list.append(copy.deepcopy(item_data))
                                    log_util.error(f"url:{driver.current_url}页面{current_path}标签无法交互，商品{item_code}数据无法获取，{''.join(traceback.format_exception(None, enie, enie.__traceback__))}")
                                    break
                        output_data_list.extend(item_data_list)
                        log_util.info(f"商品{item_code}脚本processed")
                    log_util.info(f"网站{target}脚本processed")
                else:
                    log_util.info(f"{brand.LULULEMON_BRAND}品牌没有{env_util.get_env('EXCEL_INPUT_FILE')}文件指定{target}网站脚本定义")
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
