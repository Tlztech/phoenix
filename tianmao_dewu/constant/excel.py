# TIANMAO_COLUMN_INDEX = {"title": 0, "model": 1, "sku": 2, "upc_barcode_ean": 3, "brand": 4, "size": 5, "url": 6,
#                         "msrp": 7, "discounted_price": 8, "product_main_image": 9, "product_other_image": 10,
#                         "description": 11, "product_spec": 12, "material": 13, "weight": 14, "dimension": 15,
#                         "color": 16, "stock_status": 17, "quantity": 18, "92折扣价": 19, "结果": 20
#                         }
TIANMAO_COLUMN_INDEX = {"model": 0, "size": 1, "msrp": 2, "discounted_price": 3, "color": 4, "quantity": 5, "结果": 6}
TIANMAO_COLUMN_REVERSE_INDEX = {v: k for k, v in TIANMAO_COLUMN_INDEX.items()}
DEWU_COLUMN_INDEX = {"出价ID": 0, "商品图片": 1, "SPU ID": 2, "SKU ID": 3, "三级类目": 4, "品牌": 5, "条形码": 6, "商品名称": 7, "货号": 8,
                     "规格": 9, "在售数量": 10, "发货时效（天）": 11, "我的出价(JPY)": 12, "采购成本(JPY)": 13, "经营成本(JPY)": 14,
                     "预计收入(JPY)": 15, "预计毛利(JPY)": 16, "预计净利(JPY)": 17, "消费者是否可见": 18, "*修改后发货时效（天）": 19,
                     "*修改后出价(JPY)": 20, "*修改后库存": 21, "价格(JPY)": 22, "预计收入(JPY)-全球最低价": 23, "预计毛利(JPY)-全球最低价": 24,
                     "预计净利(JPY)-全球最低价": 25,
                     "预计30天销量": 26, "近30日全球销量": 27, "近30日全球成交均价": 28, "近30日全球最高成交价": 29, "近30日全球最低成交价": 30, "结果": 31
                     }
DEWU_COLUMN_REVERSE_INDEX = {v: k for k, v in DEWU_COLUMN_INDEX.items()}
