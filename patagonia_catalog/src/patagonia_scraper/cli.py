from __future__ import annotations

import argparse
import logging
import shutil
import time
from pathlib import Path

from .constants import DEFAULT_CATEGORY_URL
from .excel import ExcelOutput, timestamped_path
from .fetcher import FetchConfig
from .models import dedupe_rows
from .scraper import PatagoniaScraper, ScraperConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape the Patagonia Japan womens catalogue into Excel.")
    parser.add_argument("--url", help="Category URL to crawl (overrides --input-file)")
    parser.add_argument(
        "--input-file",
        type=Path,
        default=Path("input_url.txt"),
        help="Text file with category URLs to crawl, one per line (# lines ignored)",
    )
    parser.add_argument("--url-file", help="Optional workbook containing product URLs in column A")
    parser.add_argument("--output", type=Path, help="Exact output .xlsx path")
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--max-pages", type=int, default=20)
    parser.add_argument("--max-products", type=int)
    parser.add_argument("--delay-min", type=float, default=1.0)
    parser.add_argument("--delay-max", type=float, default=2.5)
    parser.add_argument("--timeout", type=int, default=60_000, help="Request timeout in milliseconds")
    parser.add_argument("--proxy", help="Optional proxy URL passed to Chrome")
    parser.add_argument("--user-data-dir", help="Chrome profile directory (defaults to ./.chrome-profile)")
    parser.add_argument("--chrome-path", help="Path to the Google Chrome executable")
    parser.add_argument("--remote-port", type=int, default=9222, help="Chrome remote-debugging port")
    parser.add_argument(
        "--cdp-url",
        help="Attach to an already-running Chrome DevTools WebSocket (ws://...) instead of launching one",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Number of product pages fetched in parallel (extra tabs in the warm session). 3 is a safe default; higher (up to ~5) is faster but risks re-triggering Akamai on large runs.",
    )
    parser.add_argument("--headful", action="store_true", help="Show Chrome (default; headless is riskier vs Akamai)")
    parser.add_argument("--headless", action="store_true", help="Launch Chrome headless (may be blocked by Akamai)")
    parser.add_argument(
        "--fresh-profile",
        action="store_true",
        help="Delete the Chrome profile before launching (drops a stuck/blocked Akamai session)",
    )
    parser.add_argument(
        "--max-retries", type=int, default=3, help="Attempts per URL when Akamai returns 404 (default 3)"
    )
    parser.add_argument(
        "--no-block-resources",
        action="store_true",
        help="Download images/fonts too (default blocks their bytes to save bandwidth, esp. behind a proxy)",
    )
    parser.add_argument("--no-warmup", action="store_true", help="Skip the homepage warm-up navigation")
    parser.add_argument("--no-resume", action="store_true", help="Ignore any checkpoint and scrape everything again")
    parser.add_argument(
        "--resume-max-age-hours",
        type=float,
        default=24.0,
        help="Only resume from a checkpoint newer than this many hours; older ones are discarded and re-scraped fresh (default 24)",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Keep previous output files in output/ instead of moving them to output/history/",
    )
    parser.add_argument(
        "--flush-every", type=int, default=5, help="Write the partial (_part) workbook every N completed products"
    )
    parser.add_argument(
        "--stock-cap",
        type=int,
        default=5,
        help="Cap the quantity column at this value (the site's dropdown max); 0 = report the real ATS. Default 5.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser


def read_category_urls(path: Path) -> list[str]:
    """Category URLs from a text file, one per line; blank and # lines ignored."""
    if not path.exists():
        return []
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    if args.url:
        category_urls = [args.url]
    else:
        category_urls = read_category_urls(args.input_file)
        if not category_urls:
            logging.warning("%s not found or empty; using default %s", args.input_file, DEFAULT_CATEGORY_URL)
            category_urls = [DEFAULT_CATEGORY_URL]
    config = ScraperConfig(
        category_urls=category_urls,
        max_pages=max(1, args.max_pages),
        max_products=args.max_products,
        url_file=args.url_file,
        output_dir=args.output_dir,
        resume=not args.no_resume,
        resume_max_age_hours=max(0.0, args.resume_max_age_hours),
        flush_every=max(1, args.flush_every),
        stock_cap=max(0, args.stock_cap),
        fetch=FetchConfig(
            cdp_url=args.cdp_url,
            chrome_path=args.chrome_path,
            remote_port=args.remote_port,
            user_data_dir=args.user_data_dir,
            headless=args.headless,
            fresh_profile=args.fresh_profile,
            block_resources=not args.no_block_resources,
            max_retries=max(1, args.max_retries),
            timeout_ms=args.timeout,
            wait_after_load_ms=2_500,
            warmup=not args.no_warmup,
            concurrency=max(1, args.concurrency),
            delay_min=max(0, args.delay_min),
            delay_max=max(args.delay_min, args.delay_max),
            proxy=args.proxy,
        ),
    )
    started = time.monotonic()
    result = PatagoniaScraper(config).scrape()
    elapsed = time.monotonic() - started

    if result.discovery_failed:
        logging.error("============== 抓取未开始 ==============")
        logging.error("未发现任何商品 URL —— 极可能被 Akamai 临时拦截（今天运行多次会触发 IP 限流）。")
        logging.error("已保留断点（%s 个已抓商品），未改动任何输出文件。请按顺序尝试：", result.done)
        logging.error("  1) 等 10~30 分钟后再重跑同样命令（限流通常是临时的）；")
        logging.error("  2) 换全新浏览器身份重跑：  python main.py --fresh-profile")
        logging.error("  3) 降低并发：              python main.py --concurrency 3")
        logging.error("  4) 先用你自己的 Chrome 手动打开 https://www.patagonia.jp/shop/womens ，确认是否连人也被挡。")
        logging.error("=======================================")
        return 2

    rows, removed = dedupe_rows(result.rows)

    if result.complete:
        output = args.output if args.output else timestamped_path(args.output_dir)
        writer = ExcelOutput(output)
        writer.append(rows)
        writer.save()
        # Clean up the resume artifacts now that the job finished.
        for stale in (result.partial_path, result.partial_path.with_name(result.partial_path.stem + "_summary.txt")):
            try:
                stale.unlink()
            except OSError:
                pass
        result.checkpoint.remove()
        # Move earlier completed outputs into output/history/ so only the latest stays on top.
        if not args.output and not args.no_archive:
            moved = _archive_previous_outputs(Path(args.output_dir), output)
            if moved:
                logging.info("已归档 %s 个历史文件到 %s", moved, Path(args.output_dir) / "history")
    else:
        output = result.partial_path  # already written by the scraper

    _write_summary(result, rows, removed, elapsed, output)
    return 0 if result.complete else 1


def _archive_previous_outputs(output_dir: Path, keep: Path) -> int:
    """Move earlier completed outputs (and their _summary.txt) into output/history/.

    The just-written ``keep`` file and its summary stay in place; ``_part`` resume
    artifacts are left alone. Returns how many files were moved.
    """
    history = output_dir / "history"
    keep_names = {keep.name, keep.with_name(keep.stem + "_summary.txt").name}
    moved = 0
    for path in sorted(output_dir.glob("patagonia_output_*")):
        if not path.is_file():
            continue
        if path.name in keep_names or "_part" in path.name or path.suffix not in {".xlsx", ".txt"}:
            continue
        history.mkdir(parents=True, exist_ok=True)
        target = history / path.name
        try:
            if target.exists():
                target.unlink()
            shutil.move(str(path), str(target))
            moved += 1
        except OSError as exc:
            logging.warning("归档 %s 失败: %s", path.name, exc)
    return moved


def _format_duration(seconds: float) -> str:
    total = int(seconds)
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}小时{minutes}分{secs}秒"
    if minutes:
        return f"{minutes}分{secs}秒"
    return f"{secs}秒"


def _write_summary(result, rows, removed, elapsed: float, output: Path) -> None:
    from datetime import datetime

    skus = sum(1 for r in rows if r.sku)
    status = "全部完成" if result.complete else f"未完成（{result.done}/{result.total}），重跑同样命令可续爬"
    lines = [
        "================ 运行汇总 ================",
        f"完成时间      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"状态          : {status}",
        f"用时          : {_format_duration(elapsed)}",
        f"发现商品URL   : {result.total} 个",
        f"成功抓取商品  : {result.done} 个",
        f"获取SKU变体行 : {len(rows)} 个（去重后）",
        f"其中有效SKU   : {skus} 个",
        f"去除重复行    : {removed} 个",
        f"输出文件      : {output}",
    ]
    if result.failed_categories:
        lines.append(f"被拦截的类别  : {len(result.failed_categories)} 个（这些类别本次未抓到）")
        for cat in result.failed_categories:
            lines.append(f"  - {cat}")
    if not result.complete:
        lines.append("部分结果(_part)已保存；补齐剩余商品请重跑同样的命令。")
    lines.append("=========================================")

    for line in lines:
        logging.info(line)

    # Write the same summary next to the output workbook as a .txt log.
    summary_path = output.with_name(output.stem + "_summary.txt")
    try:
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logging.info("汇总已写入    : %s", summary_path)
    except OSError as exc:
        logging.warning("写汇总文件失败: %s", exc)


if __name__ == "__main__":
    raise SystemExit(main())
