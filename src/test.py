import sys
import os

sys.path.append(os.path.abspath('.'))

import requests
import re
from lxml import etree
from util import log_util, crawler_util, common_utils, mail_util

from cloudscraper import CloudScraper

output_mail_list = [
    {
        "url": "https://item.rakuten.co.jp/kagamicrystal/tps370-2943-ab/",
        "官网库存": "有货"
    },
    {
        "url": "https://item.rakuten.co.jp/kagamicrystal/t577-2944-ccb/",
        "官网库存": "有货"
    }
]
byte_data = common_utils.generate_excel_friendly_csv(common_utils.transform_dict_to_list(output_mail_list))
mail_util.send_csv_attachment("补货检查", byte_data)
exit(0)

# output_mail_list = [
#     {
#         "item_code": "prod9090070",
#         "url": "https://www.lululemon.co.jp/ja-jp/p/%E3%83%95%E3%83%BC%E3%83%89%E4%BB%98%E3%81%8D-define-%E3%82%B8%E3%83%A3%E3%82%B1%E3%83%83%E3%83%88-%E3%83%A1%E3%83%83%E3%82%B7%E3%83%A5%E3%83%99%E3%83%B3%E3%83%88-nulu/prod9090070.html?dwvar_prod9090070_color=0001",
#         "color": "Black",
#         "size": "18 (JP 5XL)",
#         "price": "17800",
#         "Osaka Shinsaibashi Daimaru": "",
#         "Midosuji": "",
#         "Tokyo Shinjuku Marui": "",
#         "Tokyo Azabudai Hills": "",
#         "Tokyo SIX HARAJUKU TERRACE": "",
#         "sku": "prod9090070-Black-18",
#         "price_last": 20000
#     }
# ]
# print(common_utils.generate_excel_friendly_csv(common_utils.transform_dict_to_list(output_mail_list)))
# exit(0)
# json_data = {"action":"Product-Variation","queryString":"dwvar_75095_color=SMDB&dwvar_75095_size=0&pid=75095&quantity=1","locale":"ja_JP","product":{"uuid":"51d01930e285e0fa9082ebfab1","id":"194187423926","productName":"ウィメンズ・スタンドアップ・クロップド・オーバーオール","masterID":"75095","productType":"variant","pdpSwatches":{},"selectedColor":{"color":"Smolder Blue (SMDB)","colorText":"Smolder Blue","colorCode":"SMDB"},"selectedSize":"0","isOneSize":False,"bisnEnabled":True,"hasSaleVariants":False,"price":{"sales":{"value":19800,"currency":"JPY","formatted":"¥ 19,800","decimalPrice":"19800","valueMinorUnits":19800},"list":None,"html":""},"renderedPrice":"       \u003Cdiv class=\"price\"\u003E\n        \n        \n\n\u003Cspan\u003E\n    \n    \n    \n    \n    \n    \n        \n    \n    \n    \n\n    \n\n    \n\n    \n    \u003Cmeta itemprop=\"priceCurrency\" content=\"JPY\" /\u003E\n    \u003Cspan class=\"sales \"\u003E\n        \n            \n            \n\n            \u003Cspan class=\"value\" itemprop=\"price\" content=\"19800\"\u003E\n                \n\n    &yen; 19,800\n\n\n            \u003C/span\u003E\n        \n    \u003C/span\u003E\n\n    \n\u003C/span\u003E\n\n    \u003C/div\u003E\n\n\n","discountPercent":{"value":0,"resourceMsg":"","displayPercentOff":True},"availability":{"messages":"","errorMessages":"","showMessage":False,"showNotifyMe":False,"displayBackOrderRange":False,"inStockDate":None,"inStockDateFormatted":None,"endInStockDate":None,"stockStatus":"在庫あり","status":"IN_STOCK","ATS":38,"stockLevel":38,"SKUCoverage":1,"resourceMsg":{"instockDate":"入荷予定日：None"},"isPriceValid":True,"alwaysDisplayInStockDate":True},"available":True,"online":True,"pdpAccessible":True,"readyToOrder":True,"variationAttributes":[{"attributeId":"color","displayName":"カラー","id":"color","swatchable":True,"values":[{"id":"SMDB","displayValue":"Smolder Blue (SMDB)","value":"SMDB","selected":True,"selectable":True,"orderable":True,"bisnEnabled":True,"pid":"","attrStockMatrix":{"instockArr":[],"oosArr":[],"oosObj":{},"waitlistArr":[]},"seasonDisplay":"Spring 2025","url":"https://www.patagonia.jp/on/demandware.store/Sites-patagonia-jp-Site/ja_JP/Product-Variation?dwvar_75095_color=&dwvar_75095_size=0&pid=75095&quantity=1"},{"id":"ORTN","displayValue":"Oar Tan (ORTN)","value":"ORTN","selected":False,"selectable":True,"orderable":True,"bisnEnabled":True,"pid":"","attrStockMatrix":{"instockArr":[],"oosArr":[],"oosObj":{},"waitlistArr":[]},"seasonDisplay":"Spring 2025","url":"https://www.patagonia.jp/on/demandware.store/Sites-patagonia-jp-Site/ja_JP/Product-Variation?dwvar_75095_color=ORTN&dwvar_75095_size=0&pid=75095&quantity=1"},{"id":"SINY","displayValue":"Sienna Clay (SINY)","value":"SINY","selected":False,"selectable":True,"orderable":True,"bisnEnabled":True,"pid":"","attrStockMatrix":{"instockArr":[],"oosArr":[],"oosObj":{},"waitlistArr":[]},"seasonDisplay":"Spring 2024","url":"https://www.patagonia.jp/on/demandware.store/Sites-patagonia-jp-Site/ja_JP/Product-Variation?dwvar_75095_color=SINY&dwvar_75095_size=0&pid=75095&quantity=1"}],"resetUrl":"https://www.patagonia.jp/on/demandware.store/Sites-patagonia-jp-Site/ja_JP/Product-Variation?dwvar_75095_color=&dwvar_75095_size=0&pid=75095&quantity=1"},{"attributeId":"size","displayName":"サイズ","id":"size","swatchable":False,"values":[{"id":"0","displayValue":"0","value":"0","selected":True,"selectable":False,"orderable":True,"bisnEnabled":True,"pid":"194187423926","inStock":True,"attrStockMatrix":{"instockArr":[],"oosArr":[],"oosObj":{},"waitlistArr":[]},"url":"https://www.patagonia.jp/on/demandware.store/Sites-patagonia-jp-Site/ja_JP/Product-Variation?dwvar_75095_color=SMDB&dwvar_75095_size=&pid=75095&quantity=1"},{"id":"2","displayValue":"2","value":"2","selected":False,"selectable":False,"orderable":True,"bisnEnabled":True,"pid":"194187423933","inStock":True,"attrStockMatrix":{"instockArr":[],"oosArr":[],"oosObj":{},"waitlistArr":[]},"url":"https://www.patagonia.jp/on/demandware.store/Sites-patagonia-jp-Site/ja_JP/Product-Variation?dwvar_75095_color=SMDB&dwvar_75095_size=2&pid=75095&quantity=1"},{"id":"4","displayValue":"4","value":"4","selected":False,"selectable":False,"orderable":True,"bisnEnabled":True,"pid":"194187423940","inStock":True,"attrStockMatrix":{"instockArr":[],"oosArr":[],"oosObj":{},"waitlistArr":[]},"url":"https://www.patagonia.jp/on/demandware.store/Sites-patagonia-jp-Site/ja_JP/Product-Variation?dwvar_75095_color=SMDB&dwvar_75095_size=4&pid=75095&quantity=1"},{"id":"6","displayValue":"6","value":"6","selected":False,"selectable":False,"orderable":True,"bisnEnabled":True,"pid":"194187423957","inStock":True,"attrStockMatrix":{"instockArr":[],"oosArr":[],"oosObj":{},"waitlistArr":[]},"url":"https://www.patagonia.jp/on/demandware.store/Sites-patagonia-jp-Site/ja_JP/Product-Variation?dwvar_75095_color=SMDB&dwvar_75095_size=6&pid=75095&quantity=1"},{"id":"8","displayValue":"8","value":"8","selected":False,"selectable":False,"orderable":True,"bisnEnabled":True,"pid":"194187423964","inStock":True,"attrStockMatrix":{"instockArr":[],"oosArr":[],"oosObj":{},"waitlistArr":[]},"url":"https://www.patagonia.jp/on/demandware.store/Sites-patagonia-jp-Site/ja_JP/Product-Variation?dwvar_75095_color=SMDB&dwvar_75095_size=8&pid=75095&quantity=1"},{"id":"10","displayValue":"10","value":"10","selected":False,"selectable":False,"orderable":False,"bisnEnabled":True,"pid":"","attrStockMatrix":{"instockArr":[],"oosArr":[],"oosObj":{},"waitlistArr":[]},"url":"https://www.patagonia.jp/on/demandware.store/Sites-patagonia-jp-Site/ja_JP/Product-Variation?dwvar_75095_color=SMDB&dwvar_75095_size=10&pid=75095&quantity=1"}],"resetUrl":"https://www.patagonia.jp/on/demandware.store/Sites-patagonia-jp-Site/ja_JP/Product-Variation?dwvar_75095_color=SMDB&dwvar_75095_size=&pid=75095&quantity=1"}],"orderableState":"add-to-bag","wishlist":{"variationGroupID":"75095-SMDB","tealiumData":{"product_id":"75095-SMDB","product_name":"ウィメンズ・スタンドアップ・クロップド・オーバーオール","product_plm_category":"One Pieces","product_plm_class":"Overalls/Jumpsuits/Rompers","product_plm_team":"W's Sportswear"}},"agePopupEnabled":False,"availableForInStorePickup":False,"availableForViewInStoreInventory":True,"availableAtSelectedStore":False,"directURL":"https://www.patagonia.jp/product/womens-stand-up-canvas-cropped-overalls/194187423926.html"},"resources":{"info_selectforstock":"在庫を確認するには、スタイルを選択してください","quickadd":"カートに追加","selectSize":"サイズを選択"},"clientData":{"loginUrl":"https://www.patagonia.jp/account/login/?rurl=13&pid=194187423926"},"payInFourPrice":"¥ 4,950"}
# print(common_utils.deep_key_check(json_data, ["product", "price", "sales", "valueMinorUnits"]))
# exit(0)

# scraper = CloudScraper()
# url = 'https://www.lululemon.co.jp/ja-jp/search?q=prod11520444&lang=ja_JP&searchType=manualSearch'
# response = scraper.get(url)
# print(response.text)
# print(response.status_code)
# exit(0)


# headers = {
#     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
#     'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
#     'Accept-Language': 'zh-CN,zh;q=0.9,ja;q=0.8,en-US;q=0.7,en;q=0.6',
#     'authority': 'www.lululemon.co.jp'
# }
# cookies = {'lll-intl-correlation-id': '50550b58-82da-866b-19b6-ae9295ec551d',
#            'dwanonymous_f3cf7850d51118b6aca36868d498cd1e': 'adsUbtELcDW7rNWSKaqFliMEDf', '__cq_dnt': '1'
#     , 'dw_dnt': '1', 'sat_track': 'true', 'AMCVS_A92B3BC75245B1030A490D4D%40AdobeOrg': '1',
#            '_gcl_au': '1.1.414334959.1739960818', 's_ecid': 'MCMID%7C41921180834441857083207999515084955155',
#            's_cc': 'true', '_yjsu_yjad': '1739960818.08506f4b-d8b2-4763-938c-50b7bc52313e', 'UsrCountry': 'JP',
#            '_ga': 'GA1.1.1671205498.1739960819', 'kampyle_userid': '8a5f-d8d9-8f88-6c92-d708-a7e9-1ada-d2a7',
#            'isDynamicData': 'false',
#            'QuantumMetricUserID': '76130313407cbf562a1afb142008436c',
#            'BVBRANDID': 'fb05b622-0243-4405-966e-047b47c943a0', 'dontShowEmailPopup': 'true',
#            'sid': 'DV5EFi_habKcD_CsBC1i5zVzf_S4aHz3Nd0',
#            'dwsid': 'MOMoyuK4eXOJ6NwiBQJLyAjOEyh1MWw2IDpGxo_0NHmlcR3ipg8lTeNvKESq2wLmuuHGzWyUpZ2Qt0EOb3Yddg==',
#            'AMCV_A92B3BC75245B1030A490D4D%40AdobeOrg': '179643557%7CMCIDTS%7C20141%7CMCMID%7C41921180834441857083207999515084955155%7CMCAAMLH-1740733786%7C11%7CMCAAMB-1740733786%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1740136186s%7CNONE%7CMCAID%7CNONE%7CvVersion%7C5.5.0',
#            'tfpsi': 'f36945d0-f5ba-41ca-ae21-f24c4947567d',
#            'searchTerm': 'prod9820425', 's_sq': '%5B%5BB%5D%5D',
#            '__cf_bm': 'US.qxWANUNh01G0nVZt4D5dp38QByKmFYlkNeWxtvoI-1740135309-1.0.1.1-TGCGKA4ajDE0hZWStZ703ksp9pe1TuTWmofSPMt9Ce8V8mQ3rnlsFGWhRGyFNgyU5nsvT6L6SjVY7U5wgvY_dg',
#            'QuantumMetricSessionID': 'e9a13df44c4d2e2b688bdd3014134ceb',
#            '_td': '7d60ac73-c9dc-49ab-85b0-80d49a3b6ed4', '_uetsid': '0cb50690eeac11efa364b7e319bcc26f',
#            '_uetvid': '0cb586f0eeac11efa4d20746febe36ec',
#            'cto_bundle': 'JqlYoF80Q1ZpRkN5S1ptWVJ6dUNyOTclMkY1enpHRU10YVFPNTh2b2dsb05qdUpJdDJhNFp6WWdWY1kyR2Z4QmhkWTlTRVIweDdzWVVCbVptU2hKeld2cEJERGZ4OE9lVWRxODNsMThBMDc4RGYwZXNkNE9BckowZGtMbm13SjI2cFBqYmRiYkpCREJoYlRDWiUyRjdZaVBwUGxOcGZEcyUyRlFhS05kQnpUam9wZGVPayUyRkpkYyUzRA',
#            '__rtbh.uid': '%7B%22eventType%22%3A%22uid%22%2C%22id%22%3A%22unknown%22%2C%22expiryDate%22%3A%222026-02-21T11%3A04%3A42.796Z%22%7D',
#            '__rtbh.lid': 'GA1.3.77320556.1740135883',
#            '_gid': 'GA1.3.148037503.1740135883; _ga_57BWEJEVG9=GS1.1.1740134151.9.1.1740135904.0.0.0',
#            'kampyleUserSession': '1740135904446', 'kampyleUserSessionsCount': '21', 'kampyleSessionPageCounter': '1'}
# 目标URL
# url = "https://webshop.montbell.jp/goods/list_search.php?top_sk=1102488"
url = "https://item.rakuten.co.jp/kagamicrystal/t755-2971-wug/"
# url = "https://www.himaraya.co.jp/search?q=1102488"

# 发送HTTP GET请求
# response = requests.get(url)

# response = requests.get(url, headers=headers, cookies=cookies)
response = requests.get(url)
# print(response.headers)  # 查看响应头信息
print(response.text)  # 查看响应体内容，可能会有更详细的错误信息或说明为什么被禁止访问。
# print(response.status_code)

# 检查请求是否成功
if response.status_code == 200:
    # 解析HTML内容
    tree = etree.HTML(response.content)

    # 编写XPath表达式以提取特定<a>标签的href属性
    # xpath_expression = "//*[@id='maindataCont']/div[2]/div[2]/table[1]/tr/td/text()"
    # xpath_expression = "//div[@id='goodsList']/div[position()>1]/div/div[2]/div[1]/p[6]/a/@href"
    # xpath_expression = "//*[@class='categoryList-List']/div[contains(@class, 'categoryList-List-content')]//p[@class='categoryList-List--info-price-sale']/text()"
    xpath_expression = "//div[text()='この商品は売り切れです']"

    # 执行XPath查询并提取结果
    href_result = tree.xpath(xpath_expression)

    print(href_result)
    for href in href_result:
        print(href)
    # print(href_result[0])
    exit(0)

    pattern = r'¥(\d+,\d+|\d+)'
    match = re.search(pattern, href_result[0])
    if match:
        # 提取匹配的数字部分，并去除逗号（如果需要的话）
        number_with_commas = match.group(1)
        number_without_commas = number_with_commas.replace(',', '')
        print("提取的数字部分（带逗号）:", number_with_commas)
        print("提取的数字部分（去逗号）:", number_without_commas)
    else:
        print("未找到匹配的数字部分")

    # 打印结果
    for href in href_result:
        print(href)
else:
    print(f"Failed to retrieve the webpage. Status code: {response.status_code}")
    pattern = r'¥|￥(\d+,\d+|\d+)'
    match = re.search(pattern, '￥37,180 ')
    if match:
        # 提取匹配的数字部分，并去除逗号（如果需要的话）
        number_with_commas = match.group(1)
        number_without_commas = number_with_commas.replace(',', '')
        print("提取的数字部分（带逗号）:", number_with_commas)
        print("提取的数字部分（去逗号）:", number_without_commas)
    else:
        print("未找到匹配的数字部分")
