import copy
import json
import traceback
import re
import random
import time
from lxml import etree

from constant import brand, shop, excel
from util import excel_util, log_util, crawler_util, env_util, yaml_util, common_utils

from exception.TemplateError import TemplateError


def fetch_patagonia_stock_static(item_code, sku_file):
    """使用 scrapling.Fetcher 静态抓取Patagonia商品库存数据（反爬优化版）"""
    code = common_utils.convert_sku_to_code(item_code)
    color_code = copy.deepcopy(common_utils.convert_sku_to_code_color(item_code))

    if color_code == code:
        return {'item_code': color_code, 'url': '商品sku无效', 'sku': sku_file}

    # 获取配置（从 yaml 文件）
    actions = yaml_util.get_object_price_actions_top(brand=brand.PATAGONIA_BRAND, host='patagonia')
    
    # 获取 base_url 用于相对路径转换
    base_url = "https://www.patagonia.jp"
    try:
        for data in yaml_util._dict:
            if data.get('brand') == brand.PATAGONIA_BRAND:
                for target in data.get('targets', []):
                    if target.get('host') == 'patagonia' and target.get('url'):
                        base_url = target['url'].rstrip('/')
                        break
                break
        log_util.info(f"使用 base_url: {base_url}")
    except Exception as e:
        log_util.error(f"获取 base_url 失败，使用默认值: {e}")
    
    # 创建 scrapling 配置
    scrapling_config = {
        "base_url": base_url,
        "home_url": f"{base_url}/home/",
        "recycle_every": 25,
        "delay_between": 1.5,
        "failover_min_len": 30000,
        "warmup_timeout": 30000,
    }

    for action in actions:
        if action['action_type'] == 'dynamic':
            try:
                # 1. 获取搜索页面
                search_url = action['url'].replace('%item_code%', str(color_code))
                log_util.info(f"静态抓取: {search_url}")
                html_content = crawler_util.fetch_with_scrapling(search_url, config=scrapling_config)

                if not html_content:
                    log_util.error(f"搜索页面获取失败: {search_url}")
                    return {'item_code': color_code, 'url': '搜索页面无法获取', 'sku': sku_file}

                tree = etree.HTML(html_content)

                # 检查商品是否存在
                try:
                    check_path = action['path']['check-product-exists']
                    if tree.xpath(check_path):
                        return {'item_code': color_code, 'url': '商品无货', 'sku': sku_file}
                except Exception:
                    pass

                # 2. 提取颜色元素
                color_path = list(action['path'].values())[0]
                color_elements = tree.xpath(color_path)
                find_color = False

                for color_elem in color_elements:
                    item_code_color = color_elem.get(list(action['path'].keys())[0])
                    if item_code_color == color_code:
                        find_color = True
                        break

                if not find_color and color_elements:
                    return {'item_code': color_code, 'url': '商品color无货', 'sku': sku_file}

                # 3. 获取商品链接
                item_url_path = action['path']['item_url'].replace('%color%', color_code.replace(code+'-', ''))
                item_urls = tree.xpath(item_url_path + '/@href')

                # 循环判断item_urls包含code+'.html'
                item_url = None
                for url in item_urls:
                    if code + '.html' in url:
                        item_url = url
                        break

                if not item_url:
                    return {'item_code': color_code, 'url': '商品链接未找到', 'sku': sku_file}

                # 4. 获取商品详情页
                html_content = crawler_util.fetch_with_scrapling(item_url, config=scrapling_config)

                if not html_content:
                    return {'item_code': color_code, 'url': '详情页无法获取', 'sku': sku_file}

                tree = etree.HTML(html_content)

                # 5. 处理子actions（尺码、价格、库存）
                if 'actions' in action and action['actions']:
                    for action_l_1 in action['actions']:
                        return process_size_actions_static(tree, action_l_1, color_code, item_url, sku_file, code)

                return {'item_code': color_code, 'url': item_url, 'sku': sku_file}

            except Exception as e:
                log_util.error(f"静态抓取失败: {e}")
                return None  # 返回None表示需要回退到Playwright

    return None


def process_size_actions_static(tree, action_l_1, color_code, item_url, sku_file, code):
    """处理尺码相关的静态数据"""
    try:
        # 获取颜色
        color_path = list(action_l_1['path'].values())[2]
        color_elems = tree.xpath(color_path)
        if color_elems:
            color = color_elems[0].get(list(action_l_1['path'].keys())[2])
        else:
            color = ''

        # 获取尺码列表
        size_path = list(action_l_1['path'].values())[0]
        size_elements = tree.xpath(size_path)
        size_url_list = []

        for size_elem in size_elements:
            size = size_elem.get(list(action_l_1['path'].keys())[0])
            sku_url = size_elem.get(list(action_l_1['path'].keys())[1])
            size_url_list.append({'size': size, 'sku_url': sku_url})

        # 查找匹配的尺码
        find_flg = False
        matched_sku_url = None  # 存储匹配尺码的 URL
        for size_url in size_url_list:
            size = size_url.get('size')
            current_sku_url = size_url.get('sku_url')

            if size == 'ALL':
                if sku_file == color_code:
                    sku = sku_file
                    item_data = {'item_code': color_code, 'url': item_url, 'size': size, 'color': color, 'sku': sku}
                    matched_sku_url = current_sku_url
                    find_flg = True
                else:
                    return {'item_code': color_code, 'url': '商品无size属性，sku无效', 'sku': sku_file}
            else:
                sku = f"{color_code}-{size.replace('/', '-')}"
                if sku_file == sku:
                    item_data = {'item_code': color_code, 'url': item_url, 'size': size, 'color': color, 'sku': sku}
                    matched_sku_url = current_sku_url
                    find_flg = True

        if not find_flg:
            return {'item_code': color_code, 'url': '商品size无货', 'sku': sku_file}

        # 获取价格和库存
        if 'actions' in action_l_1 and action_l_1['actions']:
            # 使用匹配尺码的 URL
            if not matched_sku_url:
                log_util.error(f"未找到匹配尺码的 URL: {sku_file}")
                return item_data
            
            # 获取 base_url 用于配置
            base_url = "https://www.patagonia.jp"
            try:
                for data in yaml_util._dict:
                    if data.get('brand') == brand.PATAGONIA_BRAND:
                        for target in data.get('targets', []):
                            if target.get('host') == 'patagonia' and target.get('url'):
                                base_url = target['url'].rstrip('/')
                                break
                        break
            except Exception as e:
                log_util.error(f"获取 base_url 失败: {e}")
            
            scrapling_config = {
                "base_url": base_url,
                "home_url": f"{base_url}/home/",
                "recycle_every": 25,
                "delay_between": 1.5,
                "failover_min_len": 30000,
                "warmup_timeout": 30000,
            }
            
            for action_l_2 in action_l_1['actions']:
                log_util.info(f"获取 SKU 数据: {matched_sku_url}")
                sku_data = crawler_util.fetch_with_scrapling(matched_sku_url, config=scrapling_config)
                if sku_data:
                    try:
                        # 直接解析JSON响应（API返回的是纯JSON，不是HTML）
                        sku_json = json.loads(sku_data)
                        log_util.info("成功解析JSON数据")

                        # 解析价格
                        if common_utils.deep_key_check(sku_json, ["product", "price", "sales", "decimalPrice"]):
                            price = sku_json['product']['price']['sales']['decimalPrice']
                            item_data['price'] = price
                            log_util.info(f"提取价格: {price}")
                        else:
                            item_data['price'] = 'price数据无法获取'
                            log_util.error("无法提取价格数据")

                        # 解析库存
                        if common_utils.deep_key_check(sku_json, ["product", "id"]):
                            sku_id = sku_json['product']['id']
                            log_util.info(f"SKU ID: {sku_id}")
                            if 'actions' in action_l_2 and action_l_2['actions']:
                                for action_l_3 in action_l_2['actions']:
                                    stock_url = action_l_3['url'].replace('%sku_id%', str(sku_id))
                                    log_util.info(f"获取库存数据: {stock_url}")
                                    stock_html = crawler_util.fetch_with_scrapling(stock_url, config=scrapling_config)
                                    if stock_html:
                                        stock_tree = etree.HTML(stock_html)
                                        parent_path = action_l_3['path']['parent']
                                        parent_elements = stock_tree.xpath(parent_path)

                                        for parent_elem in parent_elements:
                                            stock_id_path = action_l_3['path'][list(action_l_3['path'].keys())[1]]
                                            stock_id_elem = parent_elem.xpath(stock_id_path)
                                            if stock_id_elem:
                                                stock_id = stock_id_elem[0].get(list(action_l_3['path'].keys())[1])

                                                for key, value in shop.PATAGONIA_SHOP_DICT.items():
                                                    if stock_id == key:
                                                        store_name_path = action_l_3['path']['store-name']
                                                        stock_value_path = action_l_3['path']['stock-value']

                                                        store_name_elem = parent_elem.xpath(store_name_path)
                                                        stock_value_elem = parent_elem.xpath(stock_value_path)

                                                        if store_name_elem and stock_value_elem:
                                                            # lxml 使用 .text 获取文本，不是 .text_content()
                                                            # 处理编码问题，防止乱码
                                                            store_name_raw = store_name_elem[0].text or ''
                                                            stock_value_raw = stock_value_elem[0].text or ''
                                                            
                                                            # 处理可能的双重编码问题（UTF-8被错误解码为ISO-8859-1）
                                                            def fix_encoding(text):
                                                                if isinstance(text, bytes):
                                                                    text = text.decode('utf-8', errors='replace')
                                                                # 尝试修复双重编码：将错误解码的字符串重新编码为ISO-8859-1，再解码为UTF-8
                                                                try:
                                                                    return text.encode('iso-8859-1').decode('utf-8')
                                                                except (UnicodeEncodeError, UnicodeDecodeError):
                                                                    return text
                                                            
                                                            store_name = fix_encoding(store_name_raw).strip()
                                                            stock_value = fix_encoding(stock_value_raw).strip()
                                                            
                                                            item_data[store_name] = stock_value
                                                            log_util.info(f"库存: {store_name} = {stock_value}")

                    except Exception as e:
                        log_util.error(f"解析SKU数据失败: {e}")

        return item_data

    except Exception as e:
        log_util.error(f"处理尺码数据失败: {e}")
        return None


def sprider(item_codes, targets, object='stock'):
    output_data_list = []
    page = None
    context = None
    browser = None

    try:
        if item_codes and targets:
            patagonia_hosts = yaml_util.get_brand_hosts(brand.PATAGONIA_BRAND)

            for target in targets:
                if target in patagonia_hosts:
                    if target == 'patagonia':
                        log_util.info(f"网站{target}脚本processing")

                        if object == 'stock':
                            for item_code in item_codes:
                                sku_file = copy.deepcopy(item_code)
                                log_util.info(f"商品{sku_file}脚本processing")

                                # 先尝试静态抓取
                                result = fetch_patagonia_stock_static(item_code, sku_file)

                                if result is not None:
                                    output_data_list.append(result)
                                else:
                                    # 静态抓取失败，回退到Playwright
                                    log_util.info("静态抓取失败，回退到Playwright")
                                    result = fetch_patagonia_stock_playwright(item_code, sku_file, page, context, browser)
                                    output_data_list.append(result)

                                # 商品间延迟
                                time.sleep(random.uniform(8, 15))
                                log_util.info(f"商品{sku_file}脚本processed")

                        elif object == 'replenish':
                            # replenish模式保持Playwright
                            for item_code in item_codes:
                                actions = yaml_util.get_object_actions_top(brand=brand.PATAGONIA_BRAND, host=target, o=object)
                                item_data_list = []
                                log_util.info(f"商品{item_code}脚本processing")

                                for action in actions:
                                    if action['action_type'] == 'dynamic':
                                        if not page:
                                            page, context, browser = crawler_util.get_playwright_driver("INFO")
                                        context.clear_cookies()
                                        action['url'] = item_code
                                        crawler_util.safe_goto(page, item_code)
                                        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")

                                        if action['action'] == "get":
                                            try:
                                                current_path = action['path']['modal-close']
                                                element = page.wait_for_selector(f"xpath={current_path}", timeout=10000)
                                                element.click()
                                            except Exception:
                                                pass

                                            try:
                                                current_path = action['path']['stock']
                                                element = page.wait_for_selector(f"xpath={current_path}", timeout=10000)
                                                stock = element.text_content()
                                                if '在庫なし' in stock:
                                                    stock = '在庫なし'
                                                else:
                                                    stock = '在庫あり'
                                            except Exception:
                                                stock = ''

                                            item_data = {'url': item_code, '官网库存': stock}
                                            item_data_list.append(copy.deepcopy(item_data))

                            output_data_list.extend(item_data_list)
                            time.sleep(random.uniform(8, 15))
                            log_util.info(f"商品{item_code}脚本processed")

                        log_util.info(f"网站{target}脚本processed")

                    elif target == 'localsonlytcg':
                        # localsonlytcg保持原有逻辑
                        log_util.info(f"网站{target}脚本processing")
                        if object == 'stock':
                            for item_code in item_codes:
                                log_util.info(f"商品{item_code}脚本processing")
                                sku_file = copy.deepcopy(item_code)
                                item_code = common_utils.convert_sku_to_code(item_code)
                                item_data_list = []
                                item_data = {'item_code': item_code, 'sku': sku_file}
                                actions = yaml_util.get_object_price_actions_top(brand=brand.PATAGONIA_BRAND, host=target)

                                for action in actions:
                                    if action['action_type'] == 'static':
                                        action['url'] = action['url'].replace('%item_code%', str(item_code))
                                        result = crawler_util.fetch_data_static(action)

                                        if result and 'search_result' in result and result['search_result']:
                                            text = result['search_result'][0].text
                                            match = re.search(r'(\d+)\s*件', text)
                                            if match:
                                                count = int(match.group(1))
                                                if count > 0:
                                                    item_data.update({'检索有无': '有'})
                                                else:
                                                    item_data.update({'检索有无': '无'})
                                            else:
                                                item_data.update({'检索有无': '无法提取数量'})
                                                log_util.error(f"无法从文本中提取数量。{text}")

                                            item_data_list.append(copy.deepcopy(item_data))
                                        else:
                                            item_data_list.append(copy.deepcopy(item_data))
                                            log_util.error(f"检索商品网址{action['url']}请求数据出错")
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
        log_util.info(json.dumps(output_data_list, indent=4, ensure_ascii=False))
        if page:
            crawler_util.close_playwright_driver(page, context, browser)


def fetch_patagonia_stock_playwright(item_code, sku_file, page, context, browser):
    """使用Playwright抓取Patagonia商品库存（回退方案）"""
    code = common_utils.convert_sku_to_code(item_code)
    color_code = copy.deepcopy(common_utils.convert_sku_to_code_color(item_code))

    if color_code == code:
        return {'item_code': color_code, 'url': '商品sku无效', 'sku': sku_file}

    try:
        if not page:
            page, context, browser = crawler_util.get_playwright_driver(env_util.get_env('DRIVER_MODE'))

        actions = yaml_util.get_object_price_actions_top(brand=brand.PATAGONIA_BRAND, host='patagonia')

        for action in actions:
            if action['action_type'] == 'dynamic':
                if action['url']:
                    crawler_util.safe_goto(page, action['url'].replace('%item_code%', str(color_code)))

                if action['action'] == "click and get":
                    try:
                        current_path = action['path']['check-product-exists']
                        page.wait_for_selector(f"xpath={current_path}", timeout=10000)
                        return {'item_code': color_code, 'url': '商品无货', 'sku': sku_file}
                    except Exception:
                        pass

                    # color遍历
                    current_path = list(action['path'].values())[0]
                    color_elements = page.query_selector_all(f"xpath={current_path}")
                    find_color = False

                    for color_element in color_elements:
                        item_code_color = color_element.get_attribute(list(action['path'].keys())[0])
                        if item_code_color == color_code:
                            find_color = True
                            break

                    if not find_color and color_elements:
                        return {'item_code': color_code, 'url': '商品color无货', 'sku': sku_file}

                    # 商品检索
                    crawler_util.random_delay(2, 4)
                    current_path = action['path']['item_url'].replace('%color%', color_code.replace(code+'-', ''))
                    element = page.query_selector(f"xpath={current_path}")
                    item_url = element.get_attribute('href')
                    item_data = {'item_code': color_code, 'url': item_url}

                    if 'actions' in action and action['actions']:
                        for action_l_1 in action['actions']:
                            item_data.update({'size': '', 'color': ''})
                            crawler_util.safe_goto(page, item_url)

                            current_path = list(action_l_1['path'].values())[2]
                            color_element = page.wait_for_selector(f"xpath={current_path}", timeout=10000)
                            color = color_element.get_attribute(list(action_l_1['path'].keys())[2])
                            item_data = {'item_code': color_code, 'url': item_url, 'color': color}

                            current_path = list(action_l_1['path'].values())[0]
                            size_elements = page.query_selector_all(f"xpath={current_path}")
                            size_url_list = []

                            for size_element in size_elements:
                                size = size_element.get_attribute(list(action_l_1['path'].keys())[0])
                                sku_url = size_element.get_attribute(list(action_l_1['path'].keys())[1])
                                size_url_list.append({'size': size, 'sku_url': sku_url})

                            find_flg = False
                            for size_url in size_url_list:
                                if find_flg:
                                    break

                                size = size_url.get('size')
                                if size == 'ALL':
                                    if sku_file == color_code:
                                        sku = sku_file
                                        item_data = {'item_code': color_code, 'url': item_url, 'size': size, 'color': color, 'sku': sku}
                                        find_flg = True
                                    else:
                                        return {'item_code': color_code, 'url': '商品无size属性，sku无效', 'sku': sku_file}
                                else:
                                    sku = f"{color_code}-{size.replace('/', '-')}"
                                    if sku_file == sku:
                                        item_data = {'item_code': color_code, 'url': item_url, 'size': size, 'color': color, 'sku': sku}
                                        find_flg = True

                            if not find_flg:
                                return {'item_code': color_code, 'url': '商品size无货', 'sku': sku_file}

                            if 'actions' in action_l_1 and action_l_1['actions']:
                                sku_url = size_url.get('sku_url')
                                for action_l_2 in action_l_1['actions']:
                                    crawler_util.safe_goto(page, sku_url)
                                    html_sku = page.content()
                                    tree = etree.HTML(html_sku)

                                    if tree is not None:
                                        try:
                                            sku_json = json.loads(tree.xpath(action_l_2['path']['sku'])[0])

                                            if common_utils.deep_key_check(sku_json, ["product", "price", "sales", "decimalPrice"]):
                                                price = sku_json['product']['price']['sales']['decimalPrice']
                                                item_data['price'] = price
                                            else:
                                                item_data['price'] = 'price数据无法获取'

                                            if common_utils.deep_key_check(sku_json, ["product", "id"]):
                                                sku_id = sku_json['product']['id']
                                                if 'actions' in action_l_2 and action_l_2['actions']:
                                                    for action_l_3 in action_l_2['actions']:
                                                        crawler_util.safe_goto(page, action_l_3['url'].replace('%sku_id%', str(sku_id)))
                                                        current_path = action_l_3['path']['parent']
                                                        parent_elements = page.query_selector_all(f"xpath={current_path}")

                                                        for parent_element in parent_elements:
                                                            current_path = action_l_3['path'][list(action_l_3['path'].keys())[1]]
                                                            stock_id_element = parent_element.query_selector(f"xpath={current_path}")
                                                            stock_id = stock_id_element.get_attribute(list(action_l_3['path'].keys())[1])

                                                            for key, value in shop.PATAGONIA_SHOP_DICT.items():
                                                                if stock_id == key:
                                                                    current_path = action_l_3['path']['store-name']
                                                                    stock_name_element = parent_element.query_selector(f"xpath={current_path}")
                                                                    current_path = action_l_3['path']['stock-value']
                                                                    stock_value_element = parent_element.query_selector(f"xpath={current_path}")

                                                                    if stock_name_element.text_content() == value:
                                                                        item_data[stock_name_element.text_content()] = stock_value_element.text_content()
                                        except Exception as parse_error:
                                            log_util.error(f"解析SKU数据失败: {parse_error}")

                            return item_data

        return {'item_code': color_code, 'url': '数据获取失败', 'sku': sku_file}

    except Exception as e:
        log_util.error(f"Playwright抓取失败: {e}")
        return {'item_code': color_code, 'url': f'抓取失败: {str(e)}', 'sku': sku_file}