import copy
import json

from constant import shop, brand, stock
from util import log_util, yaml_util, common_utils, crawler_util, date_util, env_util


def sprider(item_codes, targets):
    output_data_list = []
    if item_codes and targets:
        montbell_hosts = yaml_util.get_brand_hosts(brand.MONTBELL_BRAND)
        for target in targets:
            if target in montbell_hosts:
                log_util.info(f"网站{target}脚本processing")
                for item_code in item_codes:
                    item_code = str(common_utils.convert_sku_to_code(str(item_code)))
                    actions = yaml_util.get_object_price_actions_top(brand=brand.MONTBELL_BRAND, host=target)
                    log_util.info(f"商品{item_code}脚本processing")
                    item_data_list = []
                    item_data = {'item_code': item_code}
                    for action in actions:
                        if action['action_type'] == 'static':
                            action['url'] = action['url'].replace('%item_code%', str(item_code))
                            # montbell 检索商品
                            result = crawler_util.fetch_data_static(action)
                            if 'actions' in action and action['actions']:
                                # montbell 商品详细数据
                                if result and 'item_list' in result and result['item_list']:
                                    for list_value in result['item_list']:
                                        if 'actions' in action and action['actions']:
                                            actions_l_1 = copy.deepcopy(action['actions'])
                                            for action_l_1 in actions_l_1:
                                                if action_l_1['action_type'] == 'static':
                                                    action_l_1['url'] = action_l_1['url'].replace('%list_value%', list_value)
                                                    result_l_1 = crawler_util.fetch_data_static(action_l_1)
                                                    item_data.update({'url': action_l_1['url']})
                                                    if result_l_1 and 'price' in result_l_1 and result_l_1['price']:
                                                        price = common_utils.prices_formatter(result_l_1['price'][0])
                                                        item_data.update({'price': price})
                                                    else:
                                                        item_data.update({'price': ''})
                                                        item_data.update({'size': ''})
                                                        item_data.update({'color': ''})
                                                        for shop_name in shop.MONBELL_SHOP_DICT.values():
                                                            item_data.update({shop_name: ''})
                                                        item_data.update({'Official website': ''})
                                                        item_data_list.append(copy.deepcopy(item_data))
                                                        log_util.error(f"商品网址{action_l_1['url']}请求数据出错")
                                                        break
                                                    if 'actions' in action_l_1 and action_l_1['actions']:
                                                        actions_l_2 = copy.deepcopy(action_l_1['actions'])
                                                        for action_l_2 in actions_l_2:
                                                            if action_l_2['action_type'] == 'api':
                                                                if 'size' in result_l_1 and result_l_1['size'] and len(result_l_1['size']) > 0:
                                                                    for size in result_l_1['size']:
                                                                        item_data.update({'size': size})
                                                                        action_color = copy.deepcopy(action_l_1)
                                                                        action_color['path']['color'] = action_color['path']['color'].replace('%size%', size)
                                                                        action_color['path']['official_website_stock'] = action_color['path']['official_website_stock'].replace('%size%', size)
                                                                        result_l_1 = crawler_util.fetch_data_static(action_color)
                                                                        if 'color' in result_l_1 and result_l_1['color'] and len(result_l_1['color']) > 0:
                                                                            for index, color in enumerate(result_l_1['color']):
                                                                                item_data.update({'color': color, 'sku': f"{item_code.strip()}-{color.strip()}-{size.strip()}", 'Official website': result_l_1['official_website_stock'][index]})
                                                                                action_l_2_url = copy.deepcopy(action_l_2['url'])
                                                                                action_l_2['url'] = action_l_2['url'].replace('%item_code%', str(item_code))
                                                                                action_l_2['url'] = action_l_2['url'].replace('%size%', size)
                                                                                action_l_2['url'] = action_l_2['url'].replace('%color%', color)
                                                                                timestamp = date_util.get_timestamp()
                                                                                action_l_2['url'] = action_l_2['url'].replace('%timestamp%', str(timestamp))
                                                                                result_l_2 = crawler_util.fetch_data_api(action_l_2)
                                                                                action_l_2['url'] = copy.deepcopy(action_l_2_url)
                                                                                for shop_name in shop.MONBELL_SHOP_DICT.values():
                                                                                    item_data.update({shop_name: ''})
                                                                                if result_l_2:
                                                                                    for result_stock in result_l_2:
                                                                                        for key in action_l_2['path'].keys():
                                                                                            if int(result_stock['shop_no']) == key:
                                                                                                if result_stock[action_l_2['path'][key]].isdigit() and stock.MONBELL_STOCK_STATUS_HAVING == int(result_stock[action_l_2['path'][key]]):
                                                                                                    stock_status = "在庫あり"
                                                                                                elif result_stock[action_l_2['path'][key]].isdigit() and stock.MONBELL_STOCK_STATUS_ONLY == int(result_stock[action_l_2['path'][key]]):
                                                                                                    stock_status = "在庫わずか"
                                                                                                else:
                                                                                                    stock_status = ""
                                                                                                item_data[shop.MONBELL_SHOP_DICT[key]] = stock_status
                                                                                elif result_l_2 is None:
                                                                                    for key in action_l_2['path'].keys():
                                                                                        item_data[shop.MONBELL_SHOP_DICT[key]] = "检索商品库存数据出错"
                                                                                    log_util.error(f"商品库存网址{action_l_2['url']}，item_code{item_code}，size{size}，color{color}，timestamp{timestamp}请求数据出错")
                                                                                else:
                                                                                    log_util.info(f"商品库存网址{action_l_2['url']}，item_code{item_code}，size{size}，color{color}，timestamp{timestamp}请求数据返回[]")
                                                                                item_data_list.append(copy.deepcopy(item_data))
                                                                        else:
                                                                            item_data.update({'color': ''})
                                                                            for shop_name in shop.MONBELL_SHOP_DICT.values():
                                                                                item_data.update({shop_name: ''})
                                                                            item_data_list.append(copy.deepcopy(item_data))
                                                                            log_util.error(f"商品color解析出错")
                                                                            break
                                                                else:
                                                                    size = ''
                                                                    item_data.update({'size': size})
                                                                    if 'color_no_size' in result_l_1 and result_l_1['color_no_size'] and len(result_l_1['color_no_size']) > 0:
                                                                        for index, color in enumerate(result_l_1['color_no_size']):
                                                                            item_data.update({'color': color, 'sku': f"{item_code.strip()}-{color.strip()}", 'Official website': result_l_1['official_website_stock_no_size'][index]})
                                                                            action_l_2_url = copy.deepcopy(action_l_2['url'])
                                                                            action_l_2['url'] = action_l_2['url'].replace('%item_code%', str(item_code))
                                                                            action_l_2['url'] = action_l_2['url'].replace('%size%', size)
                                                                            action_l_2['url'] = action_l_2['url'].replace('%color%', color)
                                                                            timestamp = date_util.get_timestamp()
                                                                            action_l_2['url'] = action_l_2['url'].replace('%timestamp%', str(timestamp))
                                                                            result_l_2 = crawler_util.fetch_data_api(action_l_2)
                                                                            action_l_2['url'] = copy.deepcopy(action_l_2_url)
                                                                            for shop_name in shop.MONBELL_SHOP_DICT.values():
                                                                                item_data.update({shop_name: ''})
                                                                            if result_l_2:
                                                                                for result_stock in result_l_2:
                                                                                    for key in action_l_2['path'].keys():
                                                                                        if int(result_stock['shop_no']) == key:
                                                                                            if result_stock[action_l_2['path'][key]].isdigit() and stock.MONBELL_STOCK_STATUS_HAVING == int(result_stock[action_l_2['path'][key]]):
                                                                                                stock_status = "在庫あり"
                                                                                            elif result_stock[action_l_2['path'][key]].isdigit() and stock.MONBELL_STOCK_STATUS_ONLY == int(result_stock[action_l_2['path'][key]]):
                                                                                                stock_status = "在庫わずか"
                                                                                            else:
                                                                                                stock_status = ""
                                                                                            item_data[shop.MONBELL_SHOP_DICT[key]] = stock_status
                                                                            elif result_l_2 is None:
                                                                                for key in action_l_2['path'].keys():
                                                                                    item_data[shop.MONBELL_SHOP_DICT[key]] = "检索商品库存数据出错"
                                                                                log_util.error(f"商品库存网址{action_l_2['url']}，item_code{item_code}，size{size}，color{color}，timestamp{timestamp}请求数据出错")
                                                                            else:
                                                                                log_util.info(f"商品库存网址{action_l_2['url']}，item_code{item_code}，size{size}，color{color}，timestamp{timestamp}请求数据返回[]")
                                                                            item_data_list.append(copy.deepcopy(item_data))
                                                                    else:
                                                                        item_data.update({'color': ''})
                                                                        for shop_name in shop.MONBELL_SHOP_DICT.values():
                                                                            item_data.update({shop_name: ''})
                                                                        item_data_list.append(copy.deepcopy(item_data))
                                                                        log_util.error(f"商品color解析出错")
                                                                        break
                                else:
                                    item_data.update({'url': ''})
                                    item_data.update({'price': ''})
                                    item_data.update({'size': ''})
                                    item_data.update({'color': ''})
                                    item_data.update({'Official website': ''})
                                    for shop_name in shop.MONBELL_SHOP_DICT.values():
                                        item_data.update({shop_name: ''})
                                    item_data_list.append(copy.deepcopy(item_data))
                                    log_util.error(f"检索商品网址{action['url']}请求数据出错")
                                    break
                    output_data_list.extend(item_data_list)
                    log_util.info(f"商品{item_code}脚本processed")
                log_util.info(f"网站{target}脚本processed")
            else:
                log_util.info(f"{brand.MONTBELL_BRAND}品牌没有{target}网站脚本定义")
    else:
        log_util.info(f"{env_util.get_env('EXCEL_INPUT_FILE')}文件数据不完整，数据处理停止")
    log_util.info(json.dumps(output_data_list, indent=4, ensure_ascii=False))
    return output_data_list
