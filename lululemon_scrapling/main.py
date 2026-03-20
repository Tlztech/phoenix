from __future__ import annotations

import argparse
import gc
import hashlib
import json
import sys
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from html import unescape
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from openpyxl import Workbook
from scrapling.fetchers import StealthySession


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SEED_FILE = SCRIPT_DIR / "lululemon_url.txt"
RAW_LOG_FILE_TEMPLATE = "lululemon_log_raw_{timestamp}.txt"
SUMMARY_LOG_FILE_TEMPLATE = "lululemon_log_summary_{timestamp}.txt"
OUTPUT_COLUMNS = [
    "type",
    "title",
    "model",
    "u_model",
    "url",
    "brand",
    "color",
    "size",
    "msrp",
    "discounted_price",
    "stock_status",
    "quantity",
]
URL_OUTPUT_COLUMNS = ["seed_url", "product_url"]
CANNOT_OPEN_COLUMNS = ["url", "error"]
PRICE_PATTERN = re.compile(r"(?:\u00A5|\uFFE5)?\s*([\d,]+)")
SKU_PATTERN = re.compile(r"SKU:\s*([A-Za-z0-9_-]+)", re.IGNORECASE)
DIGITAL_DATA_PATTERN = re.compile(
    r"digitalData\.product\.push\((\{.*?\})\);",
    re.DOTALL,
)
JSON_LD_PATTERN = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
PRODUCT_LINK_PATTERN = re.compile(
    r'<a[^>]+class="[^"]*search-results-product-name[^"]*"[^>]+href="([^"]+)"',
    re.IGNORECASE,
)
NEXT_PAGE_PATTERN = re.compile(
    r'class="[^"]*see-more-button[^"]*"[^>]+data-url="([^"]+)"',
    re.IGNORECASE,
)
IMAGE_PATTERN_TEMPLATE = r'https://images\.lululemon\.com/is/image/lululemon/([A-Za-z0-9]+)_{color}_[^"\'?<\s]+'
FALLBACK_IMAGE_PATTERN = re.compile(
    r'https://images\.lululemon\.com/is/image/lululemon/([A-Za-z0-9]+)_[^"\'?<\s]+'
)
BREADCRUMB_NAV_PATTERN = re.compile(
    r"<(?:nav|ol)[^>]*\bbreadcrumb\b[^>]*>(.*?)</(?:nav|ol)>",
    re.IGNORECASE | re.DOTALL,
)
BREADCRUMB_LINK_PATTERN = re.compile(
    r'href=["\']([^"\']*/ja-jp/c/[^"\']+)["\']',
    re.IGNORECASE,
)
STEALTH_OPTIONS = {
    "headless": True,
    "network_idle": True,
    "humanize": True,
    "os_randomize": True,
    "solve_cloudflare": True,
    "google_search": True,
}
LIST_RECYCLE_EVERY = 12
DETAIL_RECYCLE_EVERY = 40
PROGRESS_SAVE_EVERY = 25
RAW_LOG_FILE_PATH: Path | None = None
SUMMARY_LOG_FILE_PATH: Path | None = None
ORIGINAL_STDOUT = sys.stdout
ORIGINAL_STDERR = sys.stderr


class TeeStream:
    def __init__(self, primary: Any, log_path: Path) -> None:
        self.primary = primary
        self.log_path = log_path
        self.encoding = getattr(primary, "encoding", "utf-8")

    def write(self, data: str) -> int:
        written = self.primary.write(data)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(data)
        return written

    def flush(self) -> None:
        self.primary.flush()

    def isatty(self) -> bool:
        return bool(getattr(self.primary, "isatty", lambda: False)())


@dataclass(slots=True)
class ProductRow:
    type: str
    title: str
    model: str
    u_model: str
    url: str
    brand: str
    color: str
    size: str
    msrp: str
    discounted_price: str
    stock_status: str
    quantity: str


@dataclass(slots=True)
class UrlRow:
    seed_url: str
    product_url: str


@dataclass(slots=True)
class FailedUrlRow:
    url: str
    error: str


@dataclass(slots=True)
class CheckpointPaths:
    base_dir: Path
    urls_path: Path
    products_path: Path
    progress_output_path: Path


class SeedFetchError(RuntimeError):
    pass


class BrowserClient:
    def __init__(self, stage: str, recycle_every: int) -> None:
        self.stage = stage
        self.recycle_every = recycle_every
        self.session: StealthySession | None = None
        self.request_count = 0

    def __enter__(self) -> BrowserClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def configure(self, *, stage: str | None = None, recycle_every: int | None = None) -> None:
        if stage is not None:
            self.stage = stage
        if recycle_every is not None:
            self.recycle_every = recycle_every

    def close(self) -> None:
        if self.session is not None:
            try:
                self.session.close()
            finally:
                self.session = None
                gc.collect()

    def restart(self) -> None:
        if self.session is not None:
            print_progress(f"[{self.stage}] Recycling browser session after {self.request_count} requests")
        self.close()

    def _ensure_session(self) -> None:
        if self.session is None:
            print_progress(f"[{self.stage}] Launching browser session")
            self.session = StealthySession(**STEALTH_OPTIONS)
            self.session.start()

    def fetch_html(self, url: str, *, solve_cloudflare: bool = True, **fetch_kwargs: Any) -> str:
        if self.recycle_every > 0 and self.request_count > 0 and self.request_count % self.recycle_every == 0:
            self.restart()
        self._ensure_session()
        assert self.session is not None
        response = self.session.fetch(url, solve_cloudflare=solve_cloudflare, **fetch_kwargs)
        self.request_count += 1
        status = getattr(response, "status", 0)
        if status >= 400:
            raise RuntimeError(f"Request failed with status={status}")
        body = getattr(response, "body", b"")
        if isinstance(body, bytes) and body:
            return body.decode("utf-8", errors="ignore")
        text = getattr(response, "text", "")
        if isinstance(text, str) and text:
            return text
        raise RuntimeError("Fetched page is empty")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect lululemon product URLs from category/search pages and scrape product details."
    )
    parser.add_argument(
        "--output-dir",
        default=str(SCRIPT_DIR),
        help="Directory where Excel, checkpoint, and error files will be saved",
    )
    parser.add_argument(
        "--seed-file",
        default=str(DEFAULT_SEED_FILE),
        help="Text file that contains one lululemon category/search URL per line",
    )
    parser.add_argument(
        "--seed-limit",
        type=int,
        default=None,
        help="Only process the first N seed URLs. Useful for testing the full flow.",
    )
    parser.add_argument(
        "--detail-limit",
        type=int,
        default=None,
        help="Only scrape the first N collected product URLs. Useful for testing the full flow.",
    )
    parser.add_argument(
        "--seed-url",
        action="append",
        dest="seed_urls",
        help="Optional custom seed URL. Can be passed multiple times. If used, the seed file is ignored.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore existing checkpoints and start this seed set from scratch.",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="When resuming, retry product URLs that previously failed.",
    )
    return parser.parse_args()


def current_timestamp() -> str:
    return datetime.now().strftime('%Y%m%d%H%M%S')


def configure_log_files(output_dir: Path, timestamp: str) -> tuple[Path, Path]:
    global RAW_LOG_FILE_PATH, SUMMARY_LOG_FILE_PATH
    output_dir.mkdir(parents=True, exist_ok=True)
    RAW_LOG_FILE_PATH = output_dir / RAW_LOG_FILE_TEMPLATE.format(timestamp=timestamp)
    SUMMARY_LOG_FILE_PATH = output_dir / SUMMARY_LOG_FILE_TEMPLATE.format(timestamp=timestamp)
    RAW_LOG_FILE_PATH.write_text("", encoding="utf-8")
    SUMMARY_LOG_FILE_PATH.write_text("", encoding="utf-8")
    return RAW_LOG_FILE_PATH, SUMMARY_LOG_FILE_PATH


def log_message(message: str, *, stderr: bool = False) -> None:
    stream = ORIGINAL_STDERR if stderr else ORIGINAL_STDOUT
    print(message, file=stream)
    if SUMMARY_LOG_FILE_PATH is not None:
        with SUMMARY_LOG_FILE_PATH.open("a", encoding="utf-8") as handle:
            handle.write(f"{message}\n")


def enable_stream_logging(log_path: Path) -> None:
    sys.stdout = TeeStream(ORIGINAL_STDOUT, log_path)
    sys.stderr = TeeStream(ORIGINAL_STDERR, log_path)


def disable_stream_logging() -> None:
    sys.stdout = ORIGINAL_STDOUT
    sys.stderr = ORIGINAL_STDERR


def format_log_prefix(level: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"[{now}] [{level}]"


def log_event(message: str, *, level: str = "INFO", stderr: bool = False) -> None:
    log_message(f"{format_log_prefix(level)} {message}", stderr=stderr)


def print_progress(message: str) -> None:
    log_event(message)


def log_section(title: str) -> None:
    border = "=" * 18
    log_event(f"{border} {title} {border}")


def format_duration(seconds: float) -> str:
    return f"{seconds:.2f}s"


def normalize_url(url: str) -> str:
    return url.replace('&amp;', '&').strip()


def load_seed_urls_from_file(seed_file: Path) -> list[str]:
    if not seed_file.exists():
        raise FileNotFoundError(f"Seed URL file not found: {seed_file}")
    seed_urls: list[str] = []
    for line in seed_file.read_text(encoding="utf-8").splitlines():
        value = line.strip().lstrip("\ufeff")
        if not value or value.startswith("#"):
            continue
        seed_urls.append(value)
    if not seed_urls:
        raise ValueError(f"Seed URL file is empty: {seed_file}")
    return seed_urls


def seed_signature(seed_urls: list[str]) -> str:
    payload = "\n".join(seed_urls).encode("utf-8")
    return hashlib.md5(payload, usedforsecurity=False).hexdigest()[:12]


def build_checkpoint_paths(output_dir: Path, seed_urls: list[str]) -> CheckpointPaths:
    signature = seed_signature(seed_urls)
    base_dir = output_dir / ".lululemon_cache" / signature
    return CheckpointPaths(
        base_dir=base_dir,
        urls_path=base_dir / "urls_checkpoint.json",
        products_path=base_dir / "products_checkpoint.json",
        progress_output_path=base_dir / "lululemon_output_progress_latest.xlsx",
    )


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def create_urls_checkpoint(seed_urls: list[str]) -> dict[str, Any]:
    return {
        "seed_urls": seed_urls,
        "completed_seeds": [],
        "url_rows": [],
    }


def create_products_checkpoint(seed_urls: list[str]) -> dict[str, Any]:
    return {
        "seed_urls": seed_urls,
        "completed_products": {},
        "failed_products": {},
    }


def load_urls_checkpoint(paths: CheckpointPaths, seed_urls: list[str], resume: bool) -> dict[str, Any]:
    if not resume:
        checkpoint = create_urls_checkpoint(seed_urls)
        write_json(paths.urls_path, checkpoint)
        return checkpoint
    checkpoint = read_json(paths.urls_path, create_urls_checkpoint(seed_urls))
    if checkpoint.get("seed_urls") != seed_urls:
        checkpoint = create_urls_checkpoint(seed_urls)
        write_json(paths.urls_path, checkpoint)
    return checkpoint


def load_products_checkpoint(paths: CheckpointPaths, seed_urls: list[str], resume: bool) -> dict[str, Any]:
    if not resume:
        checkpoint = create_products_checkpoint(seed_urls)
        write_json(paths.products_path, checkpoint)
        return checkpoint
    checkpoint = read_json(paths.products_path, create_products_checkpoint(seed_urls))
    if checkpoint.get("seed_urls") != seed_urls:
        checkpoint = create_products_checkpoint(seed_urls)
        write_json(paths.products_path, checkpoint)
    return checkpoint


def fetch_html_with_retry(client: BrowserClient, url: str, retries: int = 2, *, solve_cloudflare: bool = True, **fetch_kwargs: Any) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return client.fetch_html(url, solve_cloudflare=solve_cloudflare, **fetch_kwargs)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt < retries:
                print_progress(f"[{client.stage}] Retry {attempt + 1}/{retries} for {url}: {exc}")
                client.restart()
    assert last_error is not None
    raise RuntimeError(str(last_error)) from last_error


def is_cloudflare_challenge_html(html: str) -> bool:
    lowered = html.lower()
    return any(
        marker in lowered
        for marker in (
            '<title>just a moment...</title>',
            'verifying you are human',
            'cf-turnstile',
            'challenge-platform',
            'attention required!',
        )
    )


def fetch_product_html_with_retry(client: BrowserClient, url: str, retries: int = 2) -> str:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            html = client.fetch_html(url, solve_cloudflare=False, network_idle=False, load_dom=False)
            if is_cloudflare_challenge_html(html):
                raise RuntimeError('Cloudflare challenge page detected without solver')
            return html
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            try:
                print_progress(f"[{client.stage}] Switching to Cloudflare solver for {url}: {exc}")
                html = client.fetch_html(url, solve_cloudflare=True)
                if is_cloudflare_challenge_html(html):
                    raise RuntimeError('Cloudflare challenge persisted after solver')
                return html
            except Exception as solver_exc:  # noqa: BLE001
                last_error = solver_exc
                if attempt < retries:
                    print_progress(f"[{client.stage}] Retry {attempt + 1}/{retries} for {url}: {solver_exc}")
                    client.restart()
    assert last_error is not None
    raise RuntimeError(str(last_error)) from last_error


def clean_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    normalized = unescape(without_tags)
    return re.sub(r"\s+", " ", normalized).strip()


def decode_value(value: str) -> str:
    return clean_text(unquote(value))


def extract_product_links(html: str, base_url: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for match in PRODUCT_LINK_PATTERN.finditer(html):
        link = normalize_url(match.group(1))
        absolute = urljoin(base_url, link)
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)
    return links


def extract_next_page_url(html: str, base_url: str) -> str | None:
    match = NEXT_PAGE_PATTERN.search(html)
    if not match:
        return None
    return urljoin(base_url, normalize_url(match.group(1)))


def collect_urls_from_seed(client: BrowserClient, seed_url: str) -> list[UrlRow]:
    collected: list[UrlRow] = []
    seen_products: set[str] = set()
    next_url: str | None = seed_url
    page_count = 0

    while next_url:
        try:
            html = fetch_html_with_retry(client, next_url, retries=0, network_idle=False)
        except Exception as exc:  # noqa: BLE001
            raise SeedFetchError(f"Failed to open list URL {next_url}: {exc}") from exc

        page_count += 1
        links = extract_product_links(html, next_url)
        for link in links:
            if link in seen_products:
                continue
            seen_products.add(link)
            collected.append(UrlRow(seed_url=seed_url, product_url=link))

        upcoming = extract_next_page_url(html, next_url)
        if upcoming == next_url:
            break
        next_url = upcoming

    if page_count == 0:
        raise SeedFetchError(f"No pages were collected for seed URL: {seed_url}")
    return collected


def write_error_file(output_dir: Path, timestamp: str, message: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"lululemon_error_{timestamp}.txt"
    path.write_text(message, encoding="utf-8")
    return path


def write_excel_rows(path: Path, columns: list[str], rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "lululemon"
    sheet.append(columns)
    for row in rows:
        sheet.append([row.get(column, "") for column in columns])
    workbook.save(path)
    return path


def write_url_excel(url_rows: list[UrlRow], output_dir: Path, timestamp: str) -> Path:
    return write_excel_rows(
        output_dir / f"lululemon_url_{timestamp}.xlsx",
        URL_OUTPUT_COLUMNS,
        [asdict(row) for row in url_rows],
    )


def write_cannot_open_excel(rows: list[FailedUrlRow], output_dir: Path, timestamp: str) -> Path | None:
    if not rows:
        return None
    return write_excel_rows(
        output_dir / f"lululemon_cannotopenurl_{timestamp}.xlsx",
        CANNOT_OPEN_COLUMNS,
        [asdict(row) for row in rows],
    )


def write_product_excel(rows: list[ProductRow], output_dir: Path, timestamp: str) -> Path:
    return write_excel_rows(
        output_dir / f"lululemon_output_{timestamp}.xlsx",
        OUTPUT_COLUMNS,
        [asdict(row) for row in rows],
    )


def write_progress_excel(rows: list[ProductRow], checkpoint_paths: CheckpointPaths) -> Path:
    return write_excel_rows(
        checkpoint_paths.progress_output_path,
        OUTPUT_COLUMNS,
        [asdict(row) for row in rows],
    )


def extract_query_color_code(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    product_id_match = re.search(r"/(prod[0-9A-Za-z]+)\.html", parsed.path)
    if product_id_match:
        key = f"dwvar_{product_id_match.group(1)}_color"
        values = query.get(key)
        if values:
            return values[0]
    for key, values in query.items():
        if key.endswith("_color") and values:
            return values[0]
    return ""


def extract_title(html: str) -> str:
    match = re.search(r"<h1[^>]*>\s*(.*?)\s*</h1>", html, re.IGNORECASE | re.DOTALL)
    if match:
        return clean_text(match.group(1))
    match = re.search(r"<title[^>]*>\s*(.*?)\s*</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        return clean_text(match.group(1))
    return ""


def extract_model(html: str, url: str, product_data: dict[str, Any] | None) -> str:
    if product_data:
        product_id = product_data.get("productInfo", {}).get("productID")
        if isinstance(product_id, str) and product_id.strip():
            return product_id.strip()
    sku_match = SKU_PATTERN.search(html)
    if sku_match:
        return sku_match.group(1).strip()
    url_match = re.search(r"/(prod[0-9A-Za-z]+)\.html", url)
    if url_match:
        return url_match.group(1)
    return ""


def extract_u_model(html: str, color_code: str) -> str:
    if color_code:
        pattern = re.compile(IMAGE_PATTERN_TEMPLATE.format(color=re.escape(color_code)))
        match = pattern.search(html)
        if match:
            return match.group(1)
    match = FALLBACK_IMAGE_PATTERN.search(html)
    return match.group(1) if match else ""


def extract_product_data(html: str) -> dict[str, Any] | None:
    match = DIGITAL_DATA_PATTERN.search(html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Failed to parse digitalData.product payload: {exc}") from exc


def extract_json_ld_variants(html: str, model: str) -> list[dict[str, Any]]:
    variants: list[dict[str, Any]] = []
    for match in JSON_LD_PATTERN.finditer(html):
        try:
            payload = json.loads(unescape(match.group(1)))
        except json.JSONDecodeError:
            continue
        products = payload if isinstance(payload, list) else [payload]
        for product in products:
            if not isinstance(product, dict):
                continue
            if product.get("@type") != "Product":
                continue
            url_value = str(product.get("offers", {}).get("url", ""))
            if model and model not in url_value:
                continue
            variants.append(product)
    return variants


def extract_category_type_from_url(url: str) -> str:
    parsed = urlparse(urljoin("https://www.lululemon.co.jp", url))
    parts = [part for part in parsed.path.split("/") if part]
    for index, part in enumerate(parts):
        if part == "c" and index + 1 < len(parts):
            return parts[index + 1].strip().lower()
    return ""


def extract_breadcrumb_type_from_json_ld(html: str) -> str:
    for match in JSON_LD_PATTERN.finditer(html):
        try:
            payload = json.loads(unescape(match.group(1)))
        except json.JSONDecodeError:
            continue
        entries = payload if isinstance(payload, list) else [payload]
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("@type") != "BreadcrumbList":
                continue
            item_list = entry.get("itemListElement", [])
            if not isinstance(item_list, list):
                continue
            for item in item_list:
                if not isinstance(item, dict):
                    continue
                candidate = item.get("item")
                if isinstance(candidate, dict):
                    candidate = candidate.get("@id") or candidate.get("id") or candidate.get("url")
                category_type = extract_category_type_from_url(str(candidate or ""))
                if category_type:
                    return category_type
    return ""


def extract_breadcrumb_type_from_html(html: str) -> str:
    nav_match = BREADCRUMB_NAV_PATTERN.search(html)
    if nav_match:
        for link_match in BREADCRUMB_LINK_PATTERN.finditer(nav_match.group(1)):
            category_type = extract_category_type_from_url(link_match.group(1))
            if category_type:
                return category_type
    for link_match in BREADCRUMB_LINK_PATTERN.finditer(html):
        category_type = extract_category_type_from_url(link_match.group(1))
        if category_type:
            return category_type
    return ""


def extract_product_type(html: str) -> str:
    return extract_breadcrumb_type_from_json_ld(html) or extract_breadcrumb_type_from_html(html)


def normalize_price(value: Any) -> str:
    if isinstance(value, (int, float)):
        return str(int(value))
    if isinstance(value, str):
        match = PRICE_PATTERN.search(value)
        if match:
            return match.group(1).replace(",", "")
        digits = re.sub(r"[^\d]", "", value)
        return digits
    if isinstance(value, dict):
        for key in ("displayRegularPrice", "displayPrice", "price", "value"):
            if key in value:
                price = normalize_price(value[key])
                if price:
                    return price
    return ""


def availability_to_stock_status(value: str) -> str:
    lowered = value.lower()
    if lowered.endswith("/instock") or lowered == "instock":
        return "in-stock"
    if lowered.endswith("/outofstock") or lowered == "outofstock":
        return "out-of-stock"
    return value


def derive_quantity(stock_status: str) -> str:
    normalized = stock_status.strip().lower()
    if normalized == "in-stock":
        return "6"
    if normalized == "low-stock":
        return "3"
    if normalized == "out-of-stock":
        return "0"
    return ""


def build_rows_from_digital_data(
    product_type: str,
    product_data: dict[str, Any],
    fallback_title: str,
    model: str,
    u_model: str,
    url: str,
) -> list[ProductRow]:
    product_info = product_data.get("productInfo", {})
    price_info = product_data.get("price", {})
    title = decode_value(str(product_info.get("productName", ""))) or fallback_title
    msrp = normalize_price(price_info.get("displayRegularPrice") or price_info)
    display_price = normalize_price(price_info.get("displayPrice") or price_info)
    discounted_price = display_price if display_price and display_price != msrp else ""

    linked_products = product_data.get("linkedProduct", [])
    rows: list[ProductRow] = []
    for variant in linked_products:
        if not isinstance(variant, dict):
            continue
        variant_info = variant.get("productInfo", {})
        attributes = variant.get("attributes", {})
        stock_status = str(attributes.get("stockStatus", "")).strip()
        rows.append(
            ProductRow(
                type=product_type,
                title=decode_value(str(variant_info.get("productName", ""))) or title,
                model=model,
                u_model=u_model,
                url=url,
                brand="lululemon",
                color=clean_text(str(variant_info.get("color", "")).strip()),
                size=clean_text(str(variant_info.get("size", "")).strip()),
                msrp=msrp,
                discounted_price=discounted_price,
                stock_status=stock_status,
                quantity=derive_quantity(stock_status),
            )
        )
    return deduplicate_rows(rows)


def build_rows_from_json_ld(
    product_type: str,
    variants: list[dict[str, Any]],
    fallback_title: str,
    model: str,
    u_model: str,
    url: str,
) -> list[ProductRow]:
    rows: list[ProductRow] = []
    for variant in variants:
        offers = variant.get("offers", {})
        msrp = normalize_price(offers.get("price") or variant.get("price"))
        stock_status = availability_to_stock_status(str(offers.get("availability", "")).strip())
        rows.append(
            ProductRow(
                type=product_type,
                title=clean_text(str(variant.get("name", ""))) or fallback_title,
                model=model,
                u_model=u_model,
                url=url,
                brand="lululemon",
                color=clean_text(str(variant.get("color", "")).strip()),
                size=clean_text(str(variant.get("size", "")).strip()),
                msrp=msrp,
                discounted_price="",
                stock_status=stock_status,
                quantity=derive_quantity(stock_status),
            )
        )
    return deduplicate_rows(rows)


def deduplicate_rows(rows: list[ProductRow]) -> list[ProductRow]:
    result: list[ProductRow] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (row.color, row.size, row.stock_status)
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def build_rows(url: str, html: str) -> list[ProductRow]:
    product_type = extract_product_type(html)
    fallback_title = extract_title(html)
    product_data = extract_product_data(html)
    model = extract_model(html, url, product_data)
    color_code = extract_query_color_code(url)
    u_model = extract_u_model(html, color_code)

    if product_data:
        rows = build_rows_from_digital_data(product_type, product_data, fallback_title, model, u_model, url)
        if rows:
            return rows

    variants = extract_json_ld_variants(html, model)
    if variants:
        rows = build_rows_from_json_ld(product_type, variants, fallback_title, model, u_model, url)
        if rows:
            return rows

    return [
        ProductRow(
            type=product_type,
            title=fallback_title,
            model=model,
            u_model=u_model,
            url=url,
            brand="lululemon",
            color="",
            size="",
            msrp="",
            discounted_price="",
            stock_status="",
            quantity="",
        )
    ]


def resolve_seed_urls(args: argparse.Namespace) -> list[str]:
    if args.seed_urls:
        seed_urls = list(args.seed_urls)
    else:
        seed_urls = load_seed_urls_from_file(Path(args.seed_file))
    if args.seed_limit is not None:
        seed_urls = seed_urls[: args.seed_limit]
    return seed_urls


def product_row_from_dict(payload: dict[str, str]) -> ProductRow:
    normalized = {column: str(payload.get(column, "")) for column in OUTPUT_COLUMNS}
    return ProductRow(**normalized)


def scrape_product_urls(
    client: BrowserClient,
    seed_urls: list[str],
    checkpoint_paths: CheckpointPaths,
    resume: bool,
) -> list[UrlRow]:
    stage_started_at = perf_counter()
    checkpoint = load_urls_checkpoint(checkpoint_paths, seed_urls, resume)
    completed_seeds = set(checkpoint.get("completed_seeds", []))
    url_rows = [UrlRow(**row) for row in checkpoint.get("url_rows", [])]
    seen_urls = {row.product_url for row in url_rows}

    total = len(seed_urls)
    for index, seed_url in enumerate(seed_urls, start=1):
        if seed_url in completed_seeds:
            print_progress(f"[Seed {index}/{total}] Reusing cached URL collection for {seed_url} (elapsed={format_duration(0.0)})")
            continue
        seed_started_at = perf_counter()
        print_progress(f"[Seed {index}/{total}] Collecting product URLs from {seed_url}")
        rows = collect_urls_from_seed(client, seed_url)
        for row in rows:
            if row.product_url in seen_urls:
                continue
            seen_urls.add(row.product_url)
            url_rows.append(row)
        completed_seeds.add(seed_url)
        checkpoint["completed_seeds"] = sorted(completed_seeds)
        checkpoint["url_rows"] = [asdict(row) for row in url_rows]
        write_json(checkpoint_paths.urls_path, checkpoint)
        seed_elapsed = perf_counter() - seed_started_at
        print_progress(
            f"[Seed {index}/{total}] Collected {len(rows)} URLs from current seed; "
            f"total unique URLs={len(url_rows)}; elapsed={format_duration(seed_elapsed)}"
        )
    stage_elapsed = perf_counter() - stage_started_at
    log_event(f"[list] URL collection stage finished in {format_duration(stage_elapsed)}", level="SUMMARY")
    return url_rows


def scrape_products(
    client: BrowserClient,
    product_urls: list[str],
    detail_limit: int | None,
    checkpoint_paths: CheckpointPaths,
    seed_urls: list[str],
    resume: bool,
    retry_failed: bool,
) -> tuple[list[ProductRow], list[FailedUrlRow], int]:
    stage_started_at = perf_counter()
    checkpoint = load_products_checkpoint(checkpoint_paths, seed_urls, resume)
    completed_products: dict[str, list[dict[str, str]]] = checkpoint.get("completed_products", {})
    failed_products: dict[str, str] = checkpoint.get("failed_products", {})

    if detail_limit is not None:
        product_urls = product_urls[:detail_limit]

    total = len(product_urls)
    processed_now = 0
    for index, product_url in enumerate(product_urls, start=1):
        if product_url in completed_products:
            print_progress(f"[Detail {index}/{total}] Reusing cached product result: {product_url} (elapsed={format_duration(0.0)})")
            continue
        if product_url in failed_products and not retry_failed:
            print_progress(
                f"[Detail {index}/{total}] Skipping previously failed product without retry: "
                f"{product_url} (elapsed={format_duration(0.0)})"
            )
            continue
        detail_started_at = perf_counter()
        print_progress(f"[Detail {index}/{total}] Fetching product detail: {product_url}")
        try:
            html = fetch_product_html_with_retry(client, product_url, retries=2)
            rows = build_rows(product_url, html)
            completed_products[product_url] = [asdict(row) for row in rows]
            failed_products.pop(product_url, None)
            processed_now += 1
            detail_elapsed = perf_counter() - detail_started_at
            print_progress(
                f"[Detail {index}/{total}] Success: produced {len(rows)} rows; "
                f"elapsed={format_duration(detail_elapsed)}"
            )
        except Exception as exc:  # noqa: BLE001
            failed_products[product_url] = str(exc)
            processed_now += 1
            detail_elapsed = perf_counter() - detail_started_at
            print_progress(
                f"[Detail {index}/{total}] Failed after retries: {exc}; "
                f"elapsed={format_duration(detail_elapsed)}"
            )
        checkpoint["completed_products"] = completed_products
        checkpoint["failed_products"] = failed_products
        write_json(checkpoint_paths.products_path, checkpoint)

        should_write_progress = (
            processed_now > 0
            and (
                processed_now % PROGRESS_SAVE_EVERY == 0
                or index == total
            )
        )
        if should_write_progress:
            partial_rows = [
                product_row_from_dict(row)
                for url in product_urls
                for row in completed_products.get(url, [])
            ]
            write_progress_excel(partial_rows, checkpoint_paths)

    final_rows: list[ProductRow] = []
    final_failed: list[FailedUrlRow] = []
    for product_url in product_urls:
        row_payloads = completed_products.get(product_url, [])
        final_rows.extend(product_row_from_dict(row) for row in row_payloads)
        if product_url in failed_products:
            final_failed.append(FailedUrlRow(url=product_url, error=failed_products[product_url]))
    stage_elapsed = perf_counter() - stage_started_at
    log_event(
        f"[detail] Product detail stage finished in {format_duration(stage_elapsed)}; "
        f"processed_now={processed_now}; success={len(completed_products)}; failed={len(final_failed)}",
        level="SUMMARY",
    )
    return final_rows, final_failed, processed_now


def main() -> None:
    global RAW_LOG_FILE_PATH, SUMMARY_LOG_FILE_PATH
    run_started_at = perf_counter()
    args = parse_args()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = SCRIPT_DIR / output_dir
    timestamp = current_timestamp()
    raw_log_file_path, summary_log_file_path = configure_log_files(output_dir, timestamp)
    enable_stream_logging(raw_log_file_path)
    try:
        seed_urls = resolve_seed_urls(args)
        checkpoint_paths = build_checkpoint_paths(output_dir, seed_urls)
        resume = not args.no_resume

        log_section("Run Start")
        print_progress(f"Starting run with {len(seed_urls)} seed URLs. Resume mode={resume}")
        print_progress(f"Seed URL file: {args.seed_file}")
        print_progress(f"Raw log file: {raw_log_file_path}")
        print_progress(f"Summary log file: {summary_log_file_path}")

        try:
            with BrowserClient(stage="list", recycle_every=LIST_RECYCLE_EVERY) as client:
                log_section("List Stage")
                list_started_at = perf_counter()
                url_rows = scrape_product_urls(client, seed_urls, checkpoint_paths, resume=resume)
                url_excel_path = write_url_excel(url_rows, output_dir, timestamp)
                list_elapsed = perf_counter() - list_started_at
                log_event(
                    f"URL collection complete. Total unique product URLs={len(url_rows)}; "
                    f"elapsed={format_duration(list_elapsed)}",
                    level="SUMMARY",
                )

                product_urls = [row.product_url for row in url_rows]
                client.configure(stage="detail", recycle_every=DETAIL_RECYCLE_EVERY)
                log_section("Detail Stage")
                detail_started_at = perf_counter()
                product_rows, failed_urls, processed_now = scrape_products(
                    client,
                    product_urls,
                    args.detail_limit,
                    checkpoint_paths,
                    seed_urls,
                    resume=resume,
                    retry_failed=args.retry_failed,
                )
                detail_elapsed = perf_counter() - detail_started_at
        except SeedFetchError as exc:
            error_path = write_error_file(output_dir, timestamp, str(exc))
            log_event(f"Seed URL collection failed. Details saved to {error_path}", level="ERROR", stderr=True)
            raise SystemExit(1) from exc

        log_section("Finalize")
        finalize_started_at = perf_counter()
        final_excel_path = write_product_excel(product_rows, output_dir, timestamp)
        progress_excel_path = write_progress_excel(product_rows, checkpoint_paths)
        cannot_open_path = write_cannot_open_excel(failed_urls, output_dir, timestamp)
        finalize_elapsed = perf_counter() - finalize_started_at
        total_elapsed = perf_counter() - run_started_at

        log_event(f"Saved {len(url_rows)} product URLs to {url_excel_path}", level="OUTPUT")
        log_event(f"Saved {len(product_rows)} product rows to {final_excel_path}", level="OUTPUT")
        log_event(f"Progress Excel: {progress_excel_path}", level="OUTPUT")
        log_event(f"Checkpoint directory: {checkpoint_paths.base_dir}", level="OUTPUT")
        log_event(f"Raw log file: {raw_log_file_path}", level="OUTPUT")
        log_event(f"Summary log file: {summary_log_file_path}", level="OUTPUT")
        log_section("Run Summary")
        log_event(
            f"Run timing summary: list={format_duration(list_elapsed)}, "
            f"detail={format_duration(detail_elapsed)}, finalize={format_duration(finalize_elapsed)}, "
            f"total={format_duration(total_elapsed)}",
            level="SUMMARY",
        )
        if processed_now == 0 and resume:
            log_event("Resume mode reused cached detail results; no new product pages were fetched.", level="SUMMARY")
        if cannot_open_path:
            log_event(f"Saved {len(failed_urls)} failed product URLs to {cannot_open_path}", level="WARN")
    finally:
        disable_stream_logging()


if __name__ == "__main__":
    main()
