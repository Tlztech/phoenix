from __future__ import annotations

from dataclasses import asdict, dataclass, field


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


def dedupe_rows(rows: "list[ProductRow]") -> "tuple[list[ProductRow], int]":
    """Drop duplicate variant rows by SKU (keep first). Returns (unique, removed).

    Rows with an empty SKU are always kept (nothing reliable to dedupe on).
    """
    seen: set[str] = set()
    unique: list[ProductRow] = []
    removed = 0
    for row in rows:
        key = row.sku
        if key and key in seen:
            removed += 1
            continue
        if key:
            seen.add(key)
        unique.append(row)
    return unique, removed


@dataclass(slots=True)
class ProductRow:
    title: str = ""
    model: str = ""
    sku: str = ""
    upc_barcode_ean: str = ""
    brand: str = "patagonia"
    size: str = ""
    url: str = ""
    color: str = ""
    msrp: str = ""
    discounted_price: str = ""
    product_main_image: str = ""
    product_other_image: str = ""
    dimension: str = ""
    description: str = ""
    product_spec: str = ""
    material: str = ""
    weight: str = ""
    stock_status: str = ""
    quantity: str = "0"

    def values(self) -> list[str]:
        data = asdict(self)
        return [data[column] for column in OUTPUT_COLUMNS]


@dataclass(slots=True)
class ColorVariant:
    code: str
    name: str = ""
    sizes: list[str] = field(default_factory=list)
    in_stock_sizes: set[str] = field(default_factory=set)
    out_of_stock_upcs: dict[str, str] = field(default_factory=dict)
    main_image: str = ""
    url: str = ""
    offer_price: float | int | None = None
    alt_assets_url: str = ""
    msrp: float | int | str | None = None
    discounted_price: float | int | str | None = None
    upc_by_size: dict[str, str] = field(default_factory=dict)
    sku_by_size: dict[str, str] = field(default_factory=dict)
    stock_by_size: dict[str, int | str] = field(default_factory=dict)
    variant_urls: dict[str, str] = field(default_factory=dict)
    other_images: list[str] = field(default_factory=list)
    product_spec: str = ""


@dataclass(slots=True)
class ProductPageData:
    title: str
    model: str
    brand: str
    description: str
    dimension: str
    material: str
    weight: str
    colors: list[ColorVariant]
    variation_endpoint: str = ""  # SFCC Product-Variation URL base for per-size stock
