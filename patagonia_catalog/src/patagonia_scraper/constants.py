from __future__ import annotations

DEFAULT_CATEGORY_URL = "https://www.patagonia.jp/shop/womens"
# patagonia.jp displays 税込 prices but its JSON-LD carries tax-exclusive values.
JP_TAX_RATE = 1.10
OUTPUT_COLUMNS = [
    "title",
    "model",
    "sku",
    "upc_barcode_ean",
    "brand",
    "size",
    "url",
    "color",
    "msrp",
    "discounted_price",
    "product_main_image",
    "product_other_image",
    "dimension",
    "description",
    "product_spec",
    "material",
    "weight",
    "stock_status",
    "quantity",
]
