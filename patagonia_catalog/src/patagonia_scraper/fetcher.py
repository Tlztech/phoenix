from __future__ import annotations

import logging
import os
import random
import shutil
import socket
import subprocess
import threading
import time
import urllib.request
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from scrapling import Selector

LOGGER = logging.getLogger(__name__)

HOME_URL = "https://www.patagonia.jp/home/"

# Third-party analytics / ads / session-replay hosts. Blocking them saves a lot of
# bandwidth (they are the bulk of non-HTML traffic) and never touches the product
# data, images CDN, or the Akamai bot sensor (all first-party / Salesforce).
_TRACKING_HOSTS = (
    "google-analytics.com", "googletagmanager.com", "googleadservices.com",
    "googlesyndication.com", "doubleclick.net", "pagead2", "adservice.google",
    "connect.facebook.net", "facebook.com/tr", "facebook.com/plugins",
    "bat.bing.com", "clarity.ms",
    "analytics.tiktok.com", "ads.tiktok.com", "business-api.tiktok",
    "fullstory.com", "hotjar.com", "mouseflow.com",
    "cdn.segment.com", "api.segment.io",
    "abtasty.com", "optimizely.com",
    "criteo.com", "criteo.net",
    "ct.pinterest.com", "s.pinimg.com/ct",
    "yjtag.jp", "yads.yahoo.co.jp", "ads-twitter.com", "analytics.twitter.com",
    "cdn.cookielaw.org", "onetrust.com", "geolocation.onetrust",
    "amazon-adsystem.com", "scorecardresearch.com", "quantserve.com",
    "braze.com", "klaviyo.com", "cdn.evgnet.com", "evergage.com",
    "sc-static.net", "tr.snapchat.com", "bounceexchange.com",
    "demdex.net", "omtrdc.net", "2o7.net", "everesttech.net",
    "rlcdn.com", "bluekai.com", "krxd.net", "adsrvr.org",
)

# Windows install locations for Google Chrome, checked in order.
_CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]


@dataclass(slots=True)
class FetchConfig:
    """Configuration for the Patagonia fetcher.

    Patagonia's shop is protected by Akamai Bot Manager, which serves a hard
    ``404`` (``Server: AkamaiNetStorage``) to every ``/shop/*`` and
    ``/product/*`` request that does not carry a validated ``_abck`` sensor
    cookie. Neither the HTTP impersonation fetcher nor a Playwright-*launched*
    browser (``navigator.webdriver == true``) can obtain that cookie.

    The reliable route is to attach over the Chrome DevTools Protocol to a
    genuine Chrome that was started from the command line (so
    ``navigator.webdriver == false``) and to warm up on the marketing homepage
    first. After that the Akamai sensor validates and the commerce paths return
    ``200``. This config drives that flow.
    """

    # Attach to an already-running Chrome instead of launching one.
    cdp_url: str | None = None
    # When launching Chrome ourselves.
    chrome_path: str | None = None
    remote_port: int = 9222
    user_data_dir: str | None = None  # defaults to a dedicated profile under the cwd
    headless: bool = False  # Akamai is far more permissive with a headed browser
    fresh_profile: bool = False  # delete the profile dir before launching (drops stale cookies)
    # Behaviour.
    timeout_ms: int = 60_000
    wait_after_load_ms: int = 2_500
    ajax_wait_ms: int = 250  # wait for scroll=False JSON/AJAX fetches (Product-Variation, alt-assets)
    scroll_on_fetch: bool = True  # trigger lazy-loaded images/content before capture
    block_resources: bool = True  # abort image/font/media downloads (we only need their URLs)
    max_retries: int = 3  # attempts per URL when Akamai returns 404
    block_abort_threshold: int = 18  # consecutive 404s → abort the run (let the caller cool down)
    warmup: bool = True
    concurrency: int = 1  # product pages fetched in parallel via extra tabs in the warm context
    delay_min: float = 1.0
    delay_max: float = 2.5
    proxy: str | None = None


class FetchedPage:
    """Adapts a rendered HTML string to the interface the parser expects.

    The parsing code written against Scrapling calls ``.css``/``.xpath`` and
    reads ``.status``/``.text``. A :class:`scrapling.Selector` provides the
    former; this thin wrapper adds the response metadata.
    """

    __slots__ = ("_selector", "status", "text", "url")

    def __init__(self, html: str, status: int, url: str) -> None:
        self._selector = Selector(html or "")
        self.status = status
        self.text = html or ""
        self.url = url

    def css(self, *args: Any, **kwargs: Any) -> Any:
        return self._selector.css(*args, **kwargs)

    def xpath(self, *args: Any, **kwargs: Any) -> Any:
        return self._selector.xpath(*args, **kwargs)

    def get_all_text(self, *args: Any, **kwargs: Any) -> str:
        return self._selector.get_all_text(*args, **kwargs)

    @property
    def body(self) -> bytes:
        return self.text.encode("utf-8", "ignore")


def _find_chrome(explicit: str | None) -> str:
    if explicit and Path(explicit).exists():
        return explicit
    which = shutil.which("chrome") or shutil.which("chrome.exe")
    if which:
        return which
    for candidate in _CHROME_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    raise RuntimeError(
        "Google Chrome was not found. Install it or pass --chrome-path / --cdp-url."
    )


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _ws_endpoint(port: int, timeout: float = 20.0) -> str:
    """Resolve the browser-level WebSocket debugger URL for a CDP port."""
    deadline = time.time() + timeout
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["webSocketDebuggerUrl"]
        except Exception as exc:  # Chrome may still be starting up
            last_err = exc
            time.sleep(0.4)
    raise RuntimeError(f"Chrome DevTools endpoint on port {port} did not come up: {last_err}")


class PatagoniaFetcher:
    """Fetch Patagonia pages through a genuine, CDP-attached Chrome.

    A single browser page is reused for the whole run so the Akamai cookies
    obtained during warm-up persist across every request.
    """

    def __init__(self, config: FetchConfig | None = None) -> None:
        self.config = config or FetchConfig()
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._ws: str | None = None
        self._proc: subprocess.Popen | None = None
        self._launched = False
        self._warmed = False
        self._first = True
        self._warm_lock = threading.Lock()
        self._last_rewarm = 0.0
        self._failure_lock = threading.Lock()
        self._failure_streak = 0
        self._abort = threading.Event()

    # -- lifecycle ---------------------------------------------------------
    def _default_profile(self) -> str:
        return str((Path.cwd() / ".chrome-profile").resolve())

    def _launch_chrome(self) -> str:
        chrome = _find_chrome(self.config.chrome_path)
        port = self.config.remote_port
        if _port_open("127.0.0.1", port):
            LOGGER.info("Reusing Chrome already listening on CDP port %s", port)
            return _ws_endpoint(port)
        profile = self.config.user_data_dir or self._default_profile()
        if self.config.fresh_profile and Path(profile).exists():
            LOGGER.info("Deleting profile for a fresh start: %s", profile)
            shutil.rmtree(profile, ignore_errors=True)
        Path(profile).mkdir(parents=True, exist_ok=True)
        args = [
            chrome,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-features=Translate",
        ]
        if self.config.headless:
            # "new" headless keeps a realistic fingerprint; still riskier than headed.
            args.append("--headless=new")
        if self.config.proxy:
            args.append(f"--proxy-server={self.config.proxy}")
        args.append("about:blank")
        LOGGER.info("Launching Chrome: %s (profile %s)", chrome, profile)
        self._proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self._launched = True
        return _ws_endpoint(port)

    def _ensure_page(self) -> Any:
        if self._page is not None:
            return self._page
        from playwright.sync_api import sync_playwright

        ws = self.config.cdp_url or self._launch_chrome()
        self._ws = ws
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.connect_over_cdp(ws)
        # Reuse the existing default context so the warmed Akamai cookies apply.
        self._context = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
        self._context.set_default_timeout(self.config.timeout_ms)
        pages = [p for p in self._context.pages if not p.is_closed()]
        self._page = pages[0] if pages else self._context.new_page()
        self._apply_resource_blocking(self._page)
        if self.config.warmup:
            self._warmup()
        return self._page

    def _warmup(self) -> None:
        if self._warmed:
            return
        page = self._page
        try:
            LOGGER.info("Warming up Akamai session on %s", HOME_URL)
            page.goto(HOME_URL, wait_until="domcontentloaded", timeout=self.config.timeout_ms)
            page.wait_for_timeout(5_000)
            for offset in (600, 1200, 1800, 900):
                page.mouse.move(200 + offset % 240, 180 + offset % 160)
                page.mouse.wheel(0, offset)
                page.wait_for_timeout(800)
        except Exception as exc:
            LOGGER.warning("Warm-up navigation failed (continuing): %s", exc)
        self._warmed = True

    # -- fetching ----------------------------------------------------------
    def _sleep(self) -> None:
        if not self._first:
            time.sleep(random.uniform(self.config.delay_min, self.config.delay_max))
        self._first = False

    def _render(
        self,
        page: Any,
        url: str,
        scroll: bool = True,
        page_action: Callable[[Any], None] | None = None,
    ) -> FetchedPage:
        response = page.goto(url, wait_until="domcontentloaded", timeout=self.config.timeout_ms)
        status = response.status if response is not None else 0
        # Full pages need time for JS to render; AJAX/JSON calls (scroll=False, e.g.
        # Product-Variation and alt-assets) are complete on load, so barely wait.
        page.wait_for_timeout(self.config.wait_after_load_ms if scroll else self.config.ajax_wait_ms)
        if scroll and self.config.scroll_on_fetch and page_action is None and status < 400:
            self._lazy_scroll(page)
        if page_action is not None:
            try:
                page_action(page)
            except Exception as exc:
                LOGGER.warning("page_action failed for %s: %s", url, exc)
        html = page.content()
        return FetchedPage(html, status, page.url)

    def _recover(self, page: Any, attempt: int) -> None:
        """React to a 404 (Akamai block): coordinated re-warm + backoff.

        Only one tab actually re-warms within a short window (others reuse the
        freshly validated session). When blocks come in a wave, a circuit-breaker
        cooldown pauses every tab so we stop hammering a rate-limited endpoint.
        """
        with self._warm_lock:
            if time.time() - self._last_rewarm > 8:
                try:
                    LOGGER.warning("Got 404 (Akamai block); clearing cookies + re-warming")
                    if self._context is not None:
                        self._context.clear_cookies()
                    page.goto(HOME_URL, wait_until="domcontentloaded", timeout=self.config.timeout_ms)
                    page.wait_for_timeout(5_000)
                    page.mouse.move(260, 240)
                    page.mouse.wheel(0, 1_500)
                    page.wait_for_timeout(1_500)
                except Exception as exc:
                    LOGGER.warning("Re-warm failed: %s", exc)
                self._last_rewarm = time.time()
        with self._failure_lock:
            streak = self._failure_streak
        # Circuit breaker: a sustained block means the IP is rate-limited; back off
        # hard so the limit window can pass instead of failing every remaining URL.
        if streak and streak % 6 == 0:
            cooldown = min(180, 30 * (streak // 6))
            LOGGER.warning("连续 %s 次被拦截，冷却 %ss 让 IP 降温…", streak, cooldown)
            time.sleep(cooldown)
        else:
            time.sleep(min(20.0, 4.0 * attempt) + random.uniform(0, 2))

    def force_rewarm(self, clear_cookies: bool = False) -> None:
        """Re-establish the Akamai session, optionally shedding stale cookies first.

        Used by category discovery when a page is blocked: clearing cookies drops a
        poisoned ``_abck`` so the fresh warm-up can mint a valid one (helps when the
        block is session/cookie state rather than an IP rate-limit).
        """
        page = self._ensure_page()
        with self._warm_lock:
            try:
                if clear_cookies and self._context is not None:
                    LOGGER.info("Clearing cookies before re-warm (drop stale Akamai session)")
                    self._context.clear_cookies()
                LOGGER.info("Re-warming session (forced)")
                page.goto(HOME_URL, wait_until="domcontentloaded", timeout=self.config.timeout_ms)
                page.wait_for_timeout(6_000)
                for offset in (700, 1_400, 2_100):
                    page.mouse.move(240, 220)
                    page.mouse.wheel(0, offset)
                    page.wait_for_timeout(900)
                self._last_rewarm = time.time()
            except Exception as exc:
                LOGGER.warning("Forced re-warm failed: %s", exc)

    def _fetch_with_retry(
        self, page: Any, url: str, scroll: bool, page_action: Callable[[Any], None] | None
    ) -> FetchedPage:
        attempts = max(1, self.config.max_retries)
        result = self._render(page, url, scroll=scroll, page_action=page_action)
        for attempt in range(1, attempts):
            if result.status != 404:
                break
            with self._failure_lock:
                self._failure_streak += 1
                streak = self._failure_streak
            # Sustained block: stop the run so the caller can do a real cooldown
            # instead of slowly failing every remaining URL.
            if streak >= self.config.block_abort_threshold:
                self._abort.set()
            self._recover(page, attempt)
            result = self._render(page, url, scroll=scroll, page_action=page_action)
        if result.status != 404:
            with self._failure_lock:
                self._failure_streak = 0
        return result

    def _apply_resource_blocking(self, page: Any) -> None:
        """Abort image/font/media byte downloads — we read image URLs from the DOM,
        not the pixels, so this saves a lot of bandwidth (important behind a metered
        proxy) and speeds up page loads. Scripts/XHR are left intact so the Akamai
        sensor and JSON endpoints still work."""
        if not self.config.block_resources:
            return
        blocked = {"image", "media", "font"}

        def _handler(route: Any) -> None:
            try:
                request = route.request
                url = request.url
                if request.resource_type in blocked or any(host in url for host in _TRACKING_HOSTS):
                    route.abort()
                else:
                    route.continue_()
            except Exception:
                try:
                    route.continue_()
                except Exception:
                    pass

        try:
            page.route("**/*", _handler)
        except Exception as exc:
            LOGGER.warning("Resource blocking setup failed: %s", exc)

    def _bound_fetch(self, page: Any) -> Callable[..., FetchedPage]:
        def _fetch(url: str, scroll: bool = True, page_action: Callable[[Any], None] | None = None) -> FetchedPage:
            return self._fetch_with_retry(page, url, scroll=scroll, page_action=page_action)

        return _fetch

    def fetch(self, url: str, page_action: Callable[[Any], None] | None = None) -> FetchedPage:
        page = self._ensure_page()
        self._sleep()
        return self._fetch_with_retry(page, url, scroll=(page_action is None), page_action=page_action)

    def run_pool(self, urls: list[str], handler: Callable[[Callable[..., FetchedPage], str], Any]) -> list[Any]:
        """Process ``urls`` with ``handler(fetch_fn, url)``, optionally in parallel.

        With ``concurrency > 1`` each worker opens its own tab through a separate
        CDP connection to the *same* warmed Chrome, so every tab shares the
        validated Akamai cookies. ``fetch_fn`` is bound to that tab.
        """
        self._ensure_page()  # launch + warm the shared context first
        self._abort.clear()
        with self._failure_lock:
            self._failure_streak = 0
        if self.config.concurrency <= 1 or len(urls) <= 1:
            fetch_fn = self._bound_fetch(self._page)
            results: list[Any] = []
            for url in urls:
                if self._abort.is_set():
                    LOGGER.warning("持续被拦截，提前结束本批（已完成的保留，稍后冷却续爬）")
                    break
                self._sleep()
                try:
                    results.append(handler(fetch_fn, url))
                except Exception:
                    LOGGER.exception("Failed processing %s", url)
                    results.append(None)
            return results

        import queue
        import threading
        from playwright.sync_api import sync_playwright

        task_q: "queue.Queue[tuple[int, str]]" = queue.Queue()
        for index, url in enumerate(urls):
            task_q.put((index, url))
        results = [None] * len(urls)
        ws = self._ws

        def worker() -> None:
            pw = sync_playwright().start()
            browser = pw.chromium.connect_over_cdp(ws)
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
            page.set_default_timeout(self.config.timeout_ms)
            self._apply_resource_blocking(page)
            fetch_fn = self._bound_fetch(page)
            try:
                while True:
                    if self._abort.is_set():
                        break
                    try:
                        index, url = task_q.get_nowait()
                    except queue.Empty:
                        break
                    try:
                        results[index] = handler(fetch_fn, url)
                    except Exception:
                        LOGGER.exception("Failed processing %s", url)
                        results[index] = None
                    finally:
                        time.sleep(random.uniform(self.config.delay_min, self.config.delay_max))
                        task_q.task_done()
            finally:
                for closer in (page.close, browser.close, pw.stop):
                    try:
                        closer()
                    except Exception:
                        pass

        n_workers = min(self.config.concurrency, len(urls))
        LOGGER.info("Fetching %s products with %s parallel tabs", len(urls), n_workers)
        threads = [threading.Thread(target=worker, daemon=True) for _ in range(n_workers)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return results

    @staticmethod
    def _lazy_scroll(page: Any) -> None:
        """Scroll down and back up so lazy-loaded product imagery renders."""
        try:
            for _ in range(8):
                page.mouse.wheel(0, 2_400)
                page.wait_for_timeout(350)
            page.mouse.wheel(0, -20_000)
            page.wait_for_timeout(400)
        except Exception:
            pass

    def close(self) -> None:
        try:
            if self._browser is not None:
                self._browser.close()
        except Exception:
            pass
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception:
            pass
        # Only terminate Chrome if we started it.
        if self._launched and self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
        self._pw = self._browser = self._context = self._page = None
