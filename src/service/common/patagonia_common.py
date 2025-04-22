import copy
import json
import traceback
from lxml import etree
from selenium.common import NoSuchElementException, StaleElementReferenceException, ElementNotInteractableException, \
    TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from constant import brand, shop, excel
from util import excel_util, log_util, crawler_util, env_util, yaml_util, common_utils

from exception.TemplateError import TemplateError

def sprider(item_codes, targets):
    output_data_list = []
    driver = None
    try:
        if item_codes and targets:
            patagonia_hosts = yaml_util.get_brand_hosts(brand.PATAGONIA_BRAND)
            for target in targets:
                if target in patagonia_hosts:
                    log_util.info(f"网站{target}脚本processing")
                    for item_code in item_codes:
                        sku_file = copy.deepcopy(item_code)
                        code = common_utils.convert_sku_to_code(item_code)
                        item_code = copy.deepcopy(common_utils.convert_sku_to_code_color(item_code))
                        if item_code == code:
                            output_data_list.append({'item_code': item_code, 'url': '商品sku无效', 'sku': sku_file})
                            log_util.error(f"sku无效,商品{sku_file}数据无法获取")
                            continue
                        item_data_list = []
                        item_data = {'item_code': item_code}
                        actions = yaml_util.get_object_price_actions_top(brand=brand.PATAGONIA_BRAND, host=target)
                        log_util.info(f"商品{sku_file}脚本processing")
                        for action in actions:
                            if action['action_type'] == 'dynamic':
                                try:
                                    if not driver:
                                        driver = crawler_util.get_driver("INFO")
                                    if action['url']:
                                        driver.get(action['url'].replace('%item_code%', str(item_code)))
                                    if action['action'] == "click and get":
                                        try:
                                            current_path = action['path']['check-product-exists']
                                            driver.find_element(By.XPATH, current_path)
                                            output_data_list.append({'item_code': item_code, 'url': '商品无货', 'sku': sku_file})
                                            log_util.error(f"检索不到商品,商品{sku_file}数据无法获取")
                                            break
                                        except NoSuchElementException as nsee:
                                            pass
                                        # color遍历
                                        current_path = list(action['path'].values())[0]
                                        color_elements = driver.find_elements(By.XPATH, current_path)
                                        find_color = False
                                        for color_element in color_elements:
                                            item_code_color = color_element.get_attribute(list(action['path'].keys())[0])
                                            if item_code_color == item_code:
                                                color_element.click()
                                                find_color = True
                                                break
                                        if not find_color and color_elements:
                                            output_data_list.append({'item_code': item_code, 'url': '商品color无货', 'sku': sku_file})
                                            log_util.error(f"color不匹配有货商品,商品{sku_file}数据无法获取")
                                            break
                                        # 商品检索
                                        current_path = action['path']['item_url']
                                        element = driver.find_element(By.XPATH, current_path)
                                        item_url = element.get_attribute('href')
                                        item_data = {'item_code': item_code, 'url': item_url}
                                        if 'actions' in action and action['actions'] and len(action['actions']) > 0:
                                            for action_l_1 in action['actions']:
                                                item_data.update({'size': '', 'color': ''})
                                                driver.get(item_url)
                                                current_path = list(action_l_1['path'].values())[2]
                                                color_element = WebDriverWait(driver, 10).until(
                                                    EC.visibility_of_element_located((By.XPATH, current_path))
                                                )
                                                color_class_list = color_element.get_attribute("class").split(" ")
                                                # 网站上不论该商品是不是有货，都要读取直营店库存 2025/04/14
                                                # if "disabled" in color_class_list:
                                                #     output_data_list.append({'item_code': item_code, 'url': '商品color无货', 'sku': sku_file})
                                                #     log_util.error(f"color不匹配有货商品,商品{sku_file}数据无法获取")
                                                #     break
                                                color = color_element.get_attribute(list(action_l_1['path'].keys())[2])
                                                item_data = {'item_code': item_code, 'url': item_url, 'color': color}
                                                current_path = list(action_l_1['path'].values())[0]
                                                size_elements = WebDriverWait(driver, 10).until(
                                                    EC.presence_of_all_elements_located((By.XPATH, current_path))
                                                )
                                                size_url_list = []
                                                for size_element in size_elements:
                                                    # size遍历
                                                    size = size_element.get_attribute(list(action_l_1['path'].keys())[0])
                                                    # sku price
                                                    sku_url = size_element.get_attribute(list(action_l_1['path'].keys())[1])
                                                    size_url_list.append({'size': size, 'sku_url': sku_url})
                                                find_flg = False
                                                for size_url in size_url_list:
                                                    if find_flg:
                                                        break
                                                    size = size_url.get('size')
                                                    if size == 'ALL':
                                                        if sku_file == item_code:
                                                            sku = sku_file
                                                            item_data = {'item_code': item_code, 'url': item_url, 'size': size, 'color': color, 'sku': sku}
                                                            find_flg = True
                                                        else:
                                                            item_data = {'item_code': item_code, 'url': '商品无size属性，sku无效'}
                                                            item_data_list.append(copy.deepcopy(item_data))
                                                            log_util.error(f"商品无size属性,sku无效,商品{sku_file}数据无法获取")
                                                            break
                                                    else:
                                                        sku = f"{item_code}-{size.replace('/', '-')}"
                                                        if sku_file == sku:
                                                            item_data = {'item_code': item_code, 'url': item_url, 'size': size, 'color': color, 'sku': sku}
                                                            find_flg = True
                                                        else:
                                                            continue
                                                    if 'actions' in action_l_1 and action_l_1['actions'] and len(action_l_1['actions']) > 0:
                                                        sku_url = size_url.get('sku_url')
                                                        for action_l_2 in action_l_1['actions']:
                                                            driver.get(sku_url)
                                                            html_sku = driver.page_source.encode("utf-8", "ignore").decode("utf-8")
                                                            tree = etree.HTML(html_sku)
                                                            if tree is not None:
                                                                sku_json = json.loads(tree.xpath(action_l_2['path']['sku'])[0])
                                                                if common_utils.deep_key_check(sku_json, ["product", "price", "sales", "decimalPrice"]):
                                                                    price = sku_json['product']['price']['sales']['decimalPrice']
                                                                    item_data = {'item_code': item_code, 'url': item_url, 'size': size, 'color': color, 'price': price, 'sku': sku}
                                                                else:
                                                                    item_data = {'item_code': item_code, 'url': item_url, 'size': size, 'color': color, 'price': 'price数据无法获取', 'sku': sku}
                                                                    log_util.error(f"{sku_url}返回数据无法正确解析product.price.sales.decimalPrice，商品{sku_file}.price数据无法获取，api返回数据：{sku_json}")
                                                                if common_utils.deep_key_check(sku_json, ["product", "id"]):
                                                                    sku_id = sku_json['product']['id']
                                                                    if 'actions' in action_l_2 and action_l_2['actions'] and len(action_l_2['actions']) > 0:
                                                                        for action_l_3 in action_l_2['actions']:
                                                                            driver.get(action_l_3['url'].replace('%sku_id%', str(sku_id)))
                                                                            current_path = action_l_3['path']['parent']
                                                                            parent_elements = WebDriverWait(driver, 10).until(
                                                                                EC.presence_of_all_elements_located((By.XPATH, current_path))
                                                                            )
                                                                            for parent_element in parent_elements:
                                                                                current_path = action_l_3['path'][list(action_l_3['path'].keys())[1]]
                                                                                stock_id_element = parent_element.find_element(By.XPATH, current_path)
                                                                                stock_id = stock_id_element.get_attribute(list(action_l_3['path'].keys())[1])
                                                                                for key, value in shop.PATAGONIA_SHOP_DICT.items():
                                                                                    if stock_id == key:
                                                                                        current_path = action_l_3['path']['store-name']
                                                                                        stock_name_element = parent_element.find_element(By.XPATH, current_path)
                                                                                        current_path = action_l_3['path']['stock-value']
                                                                                        stock_value_element = parent_element.find_element(By.XPATH, current_path)
                                                                                        if stock_name_element.text == value:
                                                                                            item_data.update({stock_name_element.text: stock_value_element.text})
                                                                                        else:
                                                                                            item_data.update({value: '店铺ID，店铺名定义同网页返回不一致, stock数据无法获取'})
                                                                                            log_util.error(f"{action_l_3['url'].replace('%sku_id%', str(sku_id))}返回店铺ID店铺名数据同定义不一致，商品{sku_file}.stock数据无法获取，返回数据店铺ID店铺名：{stock_id}{stock_name_element.text}")
                                                                    else:
                                                                        item_data_list.append(copy.deepcopy(item_data))
                                                                        log_util.error(f"模板文件的stock的action定义错误，商品{sku_file}数据无法获取，action：{action_l_2}")
                                                                        output_data_list.extend(item_data_list)
                                                                        raise TemplateError()
                                                                else:
                                                                    for shop_name in shop.LULULEMON_SHOP_DICT.values():
                                                                        item_data.update({shop_name: "检索商品库存数据出错"})
                                                                    log_util.error(f"{sku_url}返回数据无法正确解析product.id，商品{sku_file}.stock数据无法获取，api返回数据：{sku_json}")
                                                            else:
                                                                log_util.error(f"{sku_url}返回HTML无法解析，商品{sku_file}.price.stock数据无法获取，html：{html_sku}")
                                                    else:
                                                        item_data_list.append(copy.deepcopy(item_data))
                                                        log_util.error(f"模板文件的sku的action定义错误，商品{sku_file}数据无法获取，action：{action_l_1}")
                                                        output_data_list.extend(item_data_list)
                                                        raise TemplateError()
                                                    item_data_list.append(copy.deepcopy(item_data))
                                                if not find_flg:
                                                    output_data_list.append({'item_code': item_code, 'url': '商品size无货', 'sku': sku_file})
                                                    log_util.error(f"size不匹配有货商品,商品{sku_file}数据无法获取")
                                        else:
                                            item_data_list.append(copy.deepcopy(item_data))
                                            log_util.error(f"模板文件的size的action定义错误，商品{sku_file}数据无法获取，action：{action}")
                                            output_data_list.extend(item_data_list)
                                            raise TemplateError()
                                except TimeoutException as toe:
                                    item_data_list.append(copy.deepcopy(item_data))
                                    log_util.error(f"标签元素未加载，商品{sku_file}数据无法获取，{''.join(traceback.format_exception(None, toe, toe.__traceback__))}")
                                    break
                                except NoSuchElementException as nsee:
                                    item_data_list.append(copy.deepcopy(item_data))
                                    log_util.error(f"url:{driver.current_url}页面没有{current_path}标签，商品{sku_file}数据无法获取，{''.join(traceback.format_exception(None, nsee, nsee.__traceback__))}")
                                    break
                                except StaleElementReferenceException as sere:
                                    item_data_list.append(copy.deepcopy(item_data))
                                    log_util.error(f"url:{driver.current_url}页面没有{current_path}标签，商品{sku_file}数据无法获取，{''.join(traceback.format_exception(None, sere, sere.__traceback__))}")
                                    break
                                except ElementNotInteractableException as enie:
                                    item_data_list.append(copy.deepcopy(item_data))
                                    log_util.error(f"url:{driver.current_url}页面{current_path}标签无法交互，商品{sku_file}数据无法获取，{''.join(traceback.format_exception(None, enie, enie.__traceback__))}")
                                    break
                        output_data_list.extend(item_data_list)
                        log_util.info(f"商品{sku_file}脚本processed")
                    log_util.info(f"网站{target}脚本processed")
                else:
                    log_util.info(f"{brand.PATAGONIA_BRAND}品牌没有{env_util.get_env('EXCEL_INPUT_FILE')}文件指定{target}网站脚本定义")
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