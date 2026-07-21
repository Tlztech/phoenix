from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import parse_qs, urlsplit

from .models import ColorVariant, ProductPageData
from .parser import clean_image_url, extract_image_urls, model_from_url, normalize_space


def _json_objects(page: Any) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    texts = page.css('script[type="application/ld+json"]::text').getall()
    texts += page.css('script[type="application/json"]::text').getall()
    for text in texts:
        try:
            value = json.loads(text)
        except (TypeError, ValueError):
            continue
        stack = value if isinstance(value, list) else [value]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                objects.append(item)
                for child in item.values():
                    if isinstance(child, (dict, list)):
                        stack.extend(child if isinstance(child, list) else [child])
            elif isinstance(item, list):
                stack.extend(item)
    return objects


def _first_text(page: Any, selectors: list[str]) -> str:
    for selector in selectors:
        value = page.css(selector).get()
        if value:
            return normalize_space(value)
    return ""


def parse_generic_product_page(page: Any, url: str) -> ProductPageData:
    objects = _json_objects(page)
    group = next((obj for obj in objects if obj.get("@type") in {"ProductGroup", "Product"}), {})
    products = [obj for obj in objects if obj.get("@type") == "Product"]
    raw_model = str(group.get("productGroupID") or group.get("mpn") or model_from_url(url))
    model_match = re.search(r"\d{4,7}", raw_model)
    model = model_match.group(0) if model_match else raw_model
    title = normalize_space(group.get("name")) or _first_text(page, ["h1", "[data-testid='product-title']"])
    description = normalize_space(group.get("description")) or _first_text(page, ["[itemprop='description']", ".product-description"])
    brand = group.get("brand") or "patagonia"
    if isinstance(brand, dict):
        brand = brand.get("name", "patagonia")
    dimension = ""
    for table in page.css("table"):
        markup = table.get() or ""
        if any(token in markup for token in ("身幅", "身丈", "ウエスト", "サイズ", "Size")):
            dimension = markup
            break
    dimension = dimension or page.css("table").get() or ""
    body_text = normalize_space(" ".join(page.css("body ::text").getall()))
    material = ""
    for match in re.finditer(r"(?:素材|material)\s*[:：]?\s*([^。]{1,300})", body_text, re.I):
        material = normalize_space(match.group(1))
        break
    weight_match = re.search(r"(?:重量|weight)\s*[:：]?\s*([0-9.,]+\s*(?:g|kg|グラム))", body_text, re.I)
    weight = weight_match.group(1) if weight_match else ""
    by_color: dict[str, ColorVariant] = {}
    for item in products or [group]:
        sku = str(item.get("sku") or item.get("mpn") or "")
        parts = sku.split("-")
        color = str(item.get("color") or (parts[1] if len(parts) > 2 else ""))
        size = str(item.get("size") or (parts[2] if len(parts) > 2 else ""))
        if not color:
            color = parse_qs(urlsplit(url).query).get(f"dwvar_{model}_color", [""])[0]
        color = color or "default"
        variant = by_color.setdefault(color, ColorVariant(code=color, name=color, sizes=[]))
        if size and size not in variant.sizes:
            variant.sizes.append(size)
        if sku and size:
            variant.sku_by_size[size] = sku
        gtin = str(item.get("gtin13") or item.get("gtin12") or item.get("gtin") or "")
        if gtin and size:
            variant.upc_by_size[size] = gtin
        offer = item.get("offers") or {}
        if isinstance(offer, list):
            offer = offer[0] if offer else {}
        variant.offer_price = offer.get("price") or variant.offer_price
        list_price = offer.get("highPrice") or item.get("listPrice")
        variant.msrp = list_price or variant.offer_price
        variant.discounted_price = variant.offer_price if list_price and str(list_price) != str(variant.offer_price) else None
        variant.url = str(offer.get("url") or url)
        image = item.get("image")
        if isinstance(image, list):
            image = image[0] if image else ""
        variant.main_image = clean_image_url(str(image or ""))
    if not by_color:
        by_color["default"] = ColorVariant(code="", name="", sizes=[])
    sizes = [normalize_space(x) for x in page.css("input[name='size']::attr(value), select[name='size'] option::attr(value)").getall() if normalize_space(x)]
    for variant in by_color.values():
        for size in sizes:
            if size not in variant.sizes:
                variant.sizes.append(size)
        if not variant.sizes:
            variant.sizes = [""]
        if not variant.main_image:
            variant.main_image = extract_image_urls(page)[0] if extract_image_urls(page) else ""
    return ProductPageData(title, model, str(brand).lower(), description, dimension, material, weight, list(by_color.values()))
