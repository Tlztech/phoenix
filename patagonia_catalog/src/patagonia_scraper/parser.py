from __future__ import annotations

import json
import re
from html import unescape
from pathlib import PurePosixPath
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

from .models import ColorVariant, ProductPageData


MODEL_RE = re.compile(r"/(\d+)\.html(?:$|[?#])")


def normalize_space(value: str | None) -> str:
    return " ".join((value or "").split())


def model_from_url(url: str) -> str:
    match = MODEL_RE.search(url)
    return match.group(1) if match else ""


def canonical_product_url(url: str, base_url: str = "https://www.patagonia.jp") -> str:
    absolute = urljoin(base_url, unescape(url))
    parts = urlsplit(absolute)
    kept = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.startswith("dwvar_") and key.endswith("_color")
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), ""))


def discover_product_urls(page: Any, base_url: str) -> list[str]:
    """Return one representative URL per master model from a category page."""
    output: dict[str, str] = {}
    for href in page.css('a[href*="/product/"]::attr(href)').getall():
        url = canonical_product_url(href, base_url)
        model = model_from_url(url)
        if model:
            output.setdefault(model, url)
    return list(output.values())


def next_page_url(page: Any, base_url: str) -> str:
    href = page.css('a[data-action="next"]::attr(href)').get()
    if not href:
        href = page.css('.pagination__next::attr(href)').get()
    return urljoin(base_url, href) if href else ""


def _json_attr(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _ordered_union(*values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for group in values:
        for value in group:
            value = str(value)
            if value not in seen:
                seen.add(value)
                result.append(value)
    return result


def clean_image_url(url: str | None) -> str:
    """Remove resize parameters while keeping the image format used by the sample."""
    if not url:
        return ""
    raw = unescape(url).strip()
    parts = urlsplit(raw)
    if "edge.dis.commercecloud.salesforce.com" not in parts.netloc:
        return raw
    params = dict(parse_qsl(parts.query, keep_blank_values=True))
    query = urlencode({"sfrm": params.get("sfrm", "png")})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def extract_image_urls(page: Any) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for node in page.css("img, source"):
        candidates: list[str] = []
        for key in ("src", "data-src"):
            value = node.attrib.get(key)
            if value:
                candidates.append(value)
        for key in ("srcset", "data-srcset"):
            value = node.attrib.get(key)
            if value:
                candidates.extend(part.strip().split()[0] for part in value.split(",") if part.strip())
        for candidate in candidates:
            if "edge.dis.commercecloud.salesforce.com" not in candidate:
                continue
            cleaned = clean_image_url(candidate)
            if cleaned not in seen:
                seen.add(cleaned)
                urls.append(cleaned)
    return urls


def image_basename(url: str) -> str:
    return PurePosixPath(urlsplit(url).path).name


def find_hero_image(urls: Iterable[str], model: str, color: str) -> str:
    """The colour's hero shot, named ``{model}_{color}.jpg``."""
    target = f"{model}_{color}.jpg".lower()
    for url in urls:
        if image_basename(url).lower() == target:
            return url
    return ""


def order_gallery(urls: Iterable[str]) -> list[str]:
    """Reference ordering: shared ``_000_`` lifestyle shots first, then the rest,
    each group sorted by filename."""
    unique = list(dict.fromkeys(urls))
    lifestyle = [u for u in unique if "_000_" in image_basename(u)]
    rest = [u for u in unique if "_000_" not in image_basename(u)]
    return sorted(lifestyle, key=image_basename) + sorted(rest, key=image_basename)


def images_for_color(urls: Iterable[str], model: str, color: str, main_image: str) -> list[str]:
    result: list[str] = []
    seen = {main_image}
    color_prefix = f"{model}_{color}_".lower()
    lifestyle_prefix = f"{model}_000_".lower()
    for url in urls:
        filename = PurePosixPath(urlsplit(url).path).name.lower()
        if not (filename.startswith(color_prefix) or filename.startswith(lifestyle_prefix)):
            continue
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


def parse_product_schema(page: Any) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    raw = page.css("script#product-schema::text").get()
    if not raw:
        candidates = page.css('script[type="application/ld+json"]::text').getall()
        raw = next((item for item in candidates if "ProductGroup" in item), "")
    if not raw:
        raise ValueError("product JSON-LD not found")
    parsed = json.loads(raw)
    objects = parsed if isinstance(parsed, list) else [parsed]
    group = next((item for item in objects if item.get("@type") == "ProductGroup"), None)
    if not group:
        raise ValueError("ProductGroup JSON-LD not found")
    variants: dict[str, dict[str, Any]] = {}
    model = str(group.get("productGroupID") or str(group.get("@id", "")).lstrip("#"))
    for item in objects:
        if item.get("@type") != "Product":
            continue
        mpn = str(item.get("mpn") or item.get("sku") or "")
        prefix = f"{model}-"
        code = normalize_space(item.get("color"))
        if not code:
            suffix = mpn[len(prefix) :] if mpn.startswith(prefix) else mpn.rsplit("-", 1)[-1]
            code = suffix.split("-", 1)[0]
        if code:
            variants[code] = item
    return group, variants


def _joined_text(selection: Any, separator: str = "\n") -> str:
    values = [normalize_space(value) for value in selection.getall()]
    return separator.join(value for value in values if value)


def clean_weight(value: str) -> str:
    """Keep only the metric weight the reference workbook stores, e.g. ``142 g``.

    The page renders ``142 g (5 oz)``; the reference drops the imperial part.
    """
    match = re.search(r"([\d.,]+)\s*(kg|g|グラム)", value or "", re.I)
    return f"{match.group(1)} {match.group(2)}" if match else normalize_space(value)


def material_text(page: Any) -> str:
    """Material composition only — everything before the care-instructions heading."""
    segments: list[str] = []
    for raw in page.css("#collapsible-2 ::text").getall():
        text = normalize_space(raw)
        if not text:
            continue
        if text.startswith("お手入れ方法"):
            break
        segments.append(text)
    return "".join(segments)


def _dimension_cell_text(cell: Any) -> str:
    # Strip ASCII whitespace only, preserving the full-width space (U+3000)
    # used for the empty top-left corner in the reference markup.
    text = "".join(cell.css("::text").getall())
    return text.strip(" \t\r\n")


def clean_dimension_table(page: Any) -> str:
    """Rebuild the size chart as the reference stores it.

    The page table carries ``width``/``border``/``style``/``class`` attributes and
    a ``<tbody>``; the reference keeps a bare ``<table>`` with only ``bgcolor`` on
    the header row. We reconstruct that minimal markup from the cell values.
    """
    table = page.css("#collapsible-0 table")
    if not table:
        return ""
    rows_html: list[str] = []
    for tr in table.css("tr"):
        cells = tr.css("td")
        if not cells:
            continue
        tds = "".join(f"<td>{_dimension_cell_text(td)}</td>" for td in cells)
        bg = tr.attrib.get("bgcolor")
        open_tag = f'<tr bgcolor="{bg}">' if bg else "<tr>"
        rows_html.append(f"{open_tag}{tds}</tr>")
    return f"<table>{''.join(rows_html)}</table>" if rows_html else ""


def parse_product_page(page: Any, page_url: str) -> ProductPageData:
    group, schema_variants = parse_product_schema(page)
    model = str(group.get("productGroupID") or str(group.get("@id", "")).lstrip("#"))
    title = normalize_space(group.get("name"))
    description = normalize_space(group.get("description"))
    brand_data = group.get("brand") or {}
    brand = normalize_space(brand_data.get("name") if isinstance(brand_data, dict) else str(brand_data)).lower()
    brand = brand or "patagonia"
    body_text = normalize_space(" ".join(page.css("body ::text").getall()))
    page_price_match = re.search(r"[¥￥]\s*[0-9][0-9,]*(?:\.\d+)?", body_text)
    page_price = page_price_match.group(0).replace("￥", "¥") if page_price_match else ""

    dimension = clean_dimension_table(page)
    material = material_text(page)
    weight = _joined_text(
        page.xpath(
            '//h3[contains(@class,"content-feature__heading") and normalize-space()="重さ"]'
            "/following-sibling::*[1]//text()"
        ),
        separator=" ",
    )
    if not weight:
        body_text = normalize_space(" ".join(page.css("body ::text").getall()))
        weight_match = re.search(r"(?:重量|weight)\s*[:：]?\s*([0-9.,]+\s*(?:g|kg|グラム))", body_text, re.I)
        weight = weight_match.group(1) if weight_match else ""
    weight = clean_weight(weight)

    fallback_sizes = page.css('input[name="size"]::attr(value)').getall()
    colors: list[ColorVariant] = []
    seen_colors: set[str] = set()
    for swatch in page.css("button.product-swatch[data-color]"):
        code = str(swatch.attrib.get("data-color") or swatch.attrib.get("data-attr-value") or "")
        if not code or code in seen_colors:
            continue
        seen_colors.add(code)
        in_stock = [str(value) for value in _json_attr(swatch.attrib.get("data-size-stock"), [])]
        out_of_stock_map = {
            str(key): str(value)
            for key, value in _json_attr(swatch.attrib.get("data-product-oos"), {}).items()
        }
        out_sizes = [str(value) for value in _json_attr(swatch.attrib.get("data-size-oos"), [])]
        sizes = _ordered_union(fallback_sizes, in_stock, out_sizes, out_of_stock_map.keys())
        schema = schema_variants.get(code, {})
        offer = schema.get("offers") or {}
        price_spec = offer.get("priceSpecification") or {}
        if isinstance(price_spec, list):
            price_spec = price_spec[0] if price_spec else {}
        list_price = price_spec.get("price") or schema.get("listPrice")
        sale_price = offer.get("price") or page_price
        colors.append(
            ColorVariant(
                code=code,
                name=normalize_space(swatch.attrib.get("data-caption") or schema.get("color")),
                sizes=sizes or [""],
                in_stock_sizes=set(in_stock),
                out_of_stock_upcs=out_of_stock_map,
                main_image=clean_image_url(schema.get("image") or offer.get("image")),
                url=canonical_product_url(offer.get("url") or page_url),
                offer_price=sale_price,
                msrp=list_price or sale_price,
                discounted_price=sale_price if list_price and str(list_price) != str(sale_price) else None,
                alt_assets_url=urljoin(page_url, swatch.attrib.get("data-reload-altassets") or ""),
            )
        )
        schema_size = normalize_space(schema.get("size"))
        if schema_size:
            variant_sku = normalize_space(schema.get("sku") or schema.get("mpn"))
            if variant_sku:
                colors[-1].sku_by_size[schema_size] = variant_sku
            gtin = normalize_space(schema.get("gtin13") or schema.get("gtin12") or schema.get("gtin"))
            if gtin:
                colors[-1].upc_by_size[schema_size] = gtin

    if not colors:
        for code, schema in schema_variants.items():
            offer = schema.get("offers") or {}
            price_spec = offer.get("priceSpecification") or {}
            if isinstance(price_spec, list):
                price_spec = price_spec[0] if price_spec else {}
            list_price = price_spec.get("price") or schema.get("listPrice")
            sale_price = offer.get("price") or page_price
            colors.append(
                ColorVariant(
                    code=code,
                    name=normalize_space(schema.get("color")),
                    sizes=fallback_sizes or [""],
                    main_image=clean_image_url(schema.get("image") or offer.get("image")),
                    url=canonical_product_url(offer.get("url") or page_url),
                    offer_price=sale_price,
                    msrp=list_price or sale_price,
                    discounted_price=sale_price if list_price and str(list_price) != str(sale_price) else None,
                )
            )

    variation_endpoint = ""
    data_url = page.css('[data-url*="Product-Variation"]::attr(data-url)').get()
    if data_url:
        variation_endpoint = unescape(data_url).split("?", 1)[0]

    return ProductPageData(
        title=title,
        model=model,
        brand=brand,
        description=description,
        dimension=dimension,
        material=material,
        weight=weight,
        colors=colors,
        variation_endpoint=variation_endpoint,
    )


def format_yen(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        return f"¥ {int(float(value)):,}"
    except (TypeError, ValueError):
        return str(value)


def parse_browser_json(page: Any) -> dict[str, Any]:
    raw = page.css("pre::text").get()
    if not raw:
        raw = "".join(page.css("body ::text").getall()).strip()
    if not raw:
        body = page.body.decode("utf-8", "replace") if isinstance(page.body, bytes) else str(page.body)
        raw = body.strip()
    return json.loads(raw)
