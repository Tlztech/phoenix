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
from util import log_util, crawler_util, env_util, yaml_util, common_utils, size_utils


# ======== scrapling 静态抓取函数（参照 patagonia_common.py） ========

def fetch_uniqlo_stock_static(item_code, sku_file):
    """使用 scrapling.StealthySession 静态抓取 Uniqlo 商品库存（参照 fetch_patagonia_stock_static）"""
    code = common_utils.convert_sku_to_code(item_code)
    color_file = common_utils.convert_sku_to_color(item_code)
    size_file = common_utils.convert_sku_to_size(item_code)
    color_code_search = common_utils.convert_sku_to_code_color(item_code)

    if color_code_search == code:
        return {'item_code': color_code_search, 'url': '商品sku无效', 'sku': sku_file}

    actions = yaml_util.get_object_price_actions_top(brand=brand.UNIQLO_BRAND, host='uniqlo')

    scrapling_config = {
        "base_url": "https://www.uniqlo.com",
        "home_url": "https://www.uniqlo.com/jp/ja/",
        "backend": "stealthy",  # uniqlo 必须全部走 StealthySession: 1) curl_cffi 被 Akamai 拦 2) 详情页 size button 需要 JS 填充 id/value
        "delay_between": 1.5,
        "failover_min_len": 50000,
        "recycle_every": 15,
        "warmup_timeout": 45000,
    }

    for action in actions:
        if action['action_type'] != 'dynamic':
            continue
        try:
            # 1. 搜索页
            search_url = action['url'].replace('%item_code%', str(color_code_search))
            log_util.info(f"[uniqlo-static] 搜索: {search_url}")
            html_content = crawler_util.fetch_with_scrapling(search_url, config=scrapling_config)
            if not html_content:
                log_util.error("[uniqlo-static] 搜索页获取失败")
                return {'item_code': color_code_search, 'url': '搜索页面无法获取', 'sku': sku_file}

            tree = etree.HTML(html_content)

            # 检查无货
            try:
                if tree.xpath(action['path']['check-product-exists']):
                    return {'item_code': color_code_search, 'url': '商品无货', 'sku': sku_file}
            except Exception:
                pass

            # 2. 商品链接（yaml 中 uniqlo 无 item_url path，用通用 XPath）
            item_urls = tree.xpath("//a[contains(@href, '/products/')]/@href")
            if not item_urls:
                return {'item_code': color_code_search, 'url': '商品链接未找到', 'sku': sku_file}
            item_url = item_urls[0]
            log_util.info(f"[uniqlo-static] 商品链接: {item_url}")

            # 3. 详情页
            html_content = crawler_util.fetch_with_scrapling(item_url, config=scrapling_config)
            if not html_content:
                return {'item_code': color_code_search, 'url': '详情页无法获取', 'sku': sku_file}

            tree = etree.HTML(html_content)

            # 4. 处理颜色/尺码/API
            if 'actions' in action and action['actions']:
                return process_uniqlo_color_size_static(
                    tree, action['actions'][0], item_url, item_code, sku_file,
                    color_file, size_file, scrapling_config
                )

            return {'item_code': color_code_search, 'url': item_url, 'sku': sku_file}

        except Exception as e:
            log_util.error(f"[uniqlo-static] 抓取异常: {e}")
            return None  # 异常 → 让 sprider 记录失败

    return None


def process_uniqlo_color_size_static(tree, action_l_1, item_url, item_code, sku_file,
                                     color_file, size_file, scrapling_config):
    """处理 Uniqlo 颜色/尺码/l2s API/stock API（参照 process_size_actions_static）"""
    try:
        paths = list(action_l_1['path'].values())
        size_path = paths[0]    # size-id-value
        color_path = paths[1]   # color-id-value
        price_path = paths[2]   # price

        # 匹配颜色
        color_elements = tree.xpath(color_path)
        if not color_elements:
            return {'item_code': item_code, 'url': '商品color获取失败', 'sku': sku_file}

        color = None
        color_code = None
        color_item_code_list = []
        for color_elem in color_elements:
            cid = color_elem.get('id', '').split('-')[0].replace(' ', '')
            color_item_code_list.append(cid)
            if cid in color_file:
                color = cid
                color_code = color_elem.get('value')
                break

        if not color:
            log_util.info(f"[uniqlo-static] 颜色未匹配 - 目标color_file: {color_file}, 网页颜色集合: {color_item_code_list}")
            return {'item_code': item_code, 'url': f'商品color不匹配，根据数据文件SKU解析color:{color_file}', 'sku': sku_file}

        item_data = {'item_code': item_code, 'url': item_url, 'color': color}

        # 匹配尺码
        size_code = None
        size = None
        if size_file:
            size_elements = tree.xpath(size_path)
            if not size_elements:
                return {'item_code': item_code, 'url': '商品size获取失败', 'sku': sku_file}

            # 清理前缀
            size_clean = size_file.replace('WOMEN', '').replace('MEN', '').replace('KIDS', '').replace('BABY', '')
            normalized_target = size_utils.normalize_size(size_clean)
            
            # ===== 调试 log：打印每个 size button 完整属性 =====
            log_util.info(f"[uniqlo-static] 目标size='{size_file}'→clean='{size_clean}'→norm='{normalized_target}'")
            for e in size_elements:
                attrs = dict(e.attrib)
                text = (e.text or '').strip()
                child_texts = [c.text.strip() for c in e.iter() if c.text and c.text.strip()]
                log_util.info(f"[uniqlo-static]   ATTRS={attrs} text='{text}' children='{child_texts}'")
            
            for size_elem in size_elements:
                sid = size_elem.get('id', '').split('-')[0]
                if size_utils.normalize_size(sid) == normalized_target:
                    size = sid
                    size_code = size_elem.get('value')
                    break

            if not size:
                return {'item_code': item_code, 'url': f'商品size不匹配，根据数据文件SKU解析size:{size_file}', 'sku': sku_file}
            item_data['size'] = size

        # 价格
        try:
            price_elems = tree.xpath(price_path)
            item_data['price'] = price_elems[0].text.strip() if price_elems else ''
        except Exception:
            item_data['price'] = ''

        # l2s API
        if 'actions' not in action_l_1 or not action_l_1['actions']:
            return item_data
        action_l_2 = action_l_1['actions'][0]

        products_code = item_url.split("products/")[1].split("/")[0]
        price_group_code = item_url.split("?")[0].split("/")[-1]
        l2_id_url = action_l_2['url'].replace('%code%', products_code).replace('%code2%', price_group_code)

        log_util.info(f"[uniqlo-static] l2s API: {l2_id_url}")
        html_l2 = crawler_util.fetch_with_scrapling(l2_id_url, config=scrapling_config)
        if not html_l2:
            item_data['l2Id'] = 'l2Id数据无法获取'
            return item_data

        # l2s API 返回纯 JSON，直接解析（不要用 etree.HTML，会把 JSON 解析成空 HTML 树）
        l2_id_json = json.loads(html_l2.decode('utf-8') if isinstance(html_l2, bytes) else html_l2)

        l2_id = None
        if l2_id_json.get('status') == 'ok':
            for l2 in l2_id_json.get('result', {}).get('l2s', []):
                if color_code == l2['color']['displayCode']:
                    if not size_code or size_code == l2['size']['displayCode']:
                        l2_id = l2['l2Id']
                        break

        if not l2_id:
            item_data['l2Id'] = 'l2Id数据无法解析'
            log_util.error(f"[uniqlo-static] l2s 未匹配 - color_code={color_code}, size_code={size_code}")
            return item_data

        item_data['l2Id'] = str(l2_id)

        # stock API
        if 'actions' in action_l_2 and action_l_2['actions']:
            action_l_3 = action_l_2['actions'][0]
            stock_url = action_l_3['url'].replace('%l2Id%', str(l2_id))
            log_util.info(f"[uniqlo-static] stock API: {stock_url}")

            html_stock = crawler_util.fetch_with_scrapling(stock_url, config=scrapling_config)
            if not html_stock:
                for shop_name in shop.UNIQLO_SHOP_DICT.values():
                    item_data[shop_name] = '网页无法获取stock数据'
                return item_data

            # stock API 也返回纯 JSON，直接解析
            stock_json = json.loads(html_stock.decode('utf-8') if isinstance(html_stock, bytes) else html_stock)

            if stock_json.get('status') == 'ok':
                stores = stock_json.get('result', {}).get('stores', [])
                for key, value in shop.UNIQLO_SHOP_DICT.items():
                    item_data[value] = '网页没有匹配到店铺ID'
                    for store in stores:
                        if store['storeId'] == key and store['storeName'] == value:
                            item_data[store['storeName']] = store['stockStatus']
                            break
            else:
                for shop_name in shop.UNIQLO_SHOP_DICT.values():
                    item_data[shop_name] = 'stock API返回异常'

        return item_data

    except Exception as e:
        log_util.error(f"[uniqlo-static] 颜色/尺码/API 处理异常: {e}")
        return None


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
                            log_util.info(f"商品{sku_file}脚本processing")

                            # 完全用 scrapling 静态抓取（参照 patagonia）
                            result = fetch_uniqlo_stock_static(item_code, sku_file)

                            if result is not None:
                                if isinstance(result, list):
                                    output_data_list.extend(result)
                                else:
                                    output_data_list.append(result)
                                log_util.info(f"商品{sku_file}脚本processed")
                            else:
                                log_util.error(f"[uniqlo-static] 静态抓取返回 None，数据无法获取: {sku_file}")
                                output_data_list.append(
                                    {'item_code': common_utils.convert_sku_to_code_color(item_code),
                                     'url': '静态抓取失败，数据无法获取', 'sku': sku_file}
                                )

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
            # crawler_util.close_driver(driver)
            crawler_util.close_undetected_driver(driver)
        log_util.info(json.dumps(output_data_list, indent=4, ensure_ascii=False))