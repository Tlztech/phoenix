import time

import requests
import chardet
import html
import undetected_chromedriver as uc

from util import log_util
from lxml import etree
from requests import RequestException, HTTPError, Timeout, TooManyRedirects, URLRequired

from selenium import webdriver
# from seleniumwire import webdriver
from selenium.common import TimeoutException, ElementNotInteractableException
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC


def fetch_data_static(action):
    try:
        # 发送HTTP GET请求
        response = requests.get(action['url'])
        detected_encoding = chardet.detect(response.content)['encoding']
        response.encoding = detected_encoding
        response.raise_for_status()  # 如果响应状态码不是200，将抛出HTTPError

        # 检查请求是否成功
        if response.status_code == 200:
            result = {}
            # 解析HTML内容
            tree = etree.HTML(html.unescape(response.content.decode(detected_encoding)))
            for key, value in action['path'].items():
                result.update({key: tree.xpath(value)})
        return result
    except RequestException as e:
        log_util.error(f"请求发生错误: {e}")
    except HTTPError as e:
        log_util.error(f"HTTP错误: {e}")
    except ConnectionError as e:
        log_util.error(f"连接错误: {e}")
    except Timeout as e:
        log_util.error(f"请求超时: {e}")
    except TooManyRedirects as e:
        log_util.error(f"重定向次数过多: {e}")
    except URLRequired as e:
        log_util.error(f"未提供URL: {e}")
    except Exception as e:
        log_util.error(f"发生未知错误: {e}")


def fetch_data_api(action):
    try:
        # 发送HTTP GET请求
        response = requests.get(action['url'])

        # 检查请求是否成功
        if response.status_code == 200:
            # 解析JSON数据
            result = response.json()

            # # 处理解析后的数据
            # print("获取到的数据:", result)

            return result
    except RequestException as e:
        log_util.error(f"请求发生错误: {e}")
    except HTTPError as e:
        log_util.error(f"HTTP错误: {e}")
    except ConnectionError as e:
        log_util.error(f"连接错误: {e}")
    except Timeout as e:
        log_util.error(f"请求超时: {e}")
    except TooManyRedirects as e:
        log_util.error(f"重定向次数过多: {e}")
    except URLRequired as e:
        log_util.error(f"未提供URL: {e}")
    except Exception as e:
        log_util.error(f"发生未知错误: {e}")


def get_driver(mode='DEBUG'):
    options = Options()
    if mode != "DEBUG":
        options.add_argument('--headless')  # 无头模式运行浏览器
    options.add_argument(
        f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36')
    options.add_argument("--disable-blink-features=AutomationControlled")  # 禁用自动化控制特征:ml-citation{ref="4,7" data="citationList"}
    # options.add_argument("--disable-blink-features")  # 关闭Blink引擎自动化标记:ml-citation{ref="1,7" data="citationList"}
    # options.add_argument("--no-sandbox")  # 禁用沙盒模式减少特征暴露:ml-citation{ref="5" data="citationList"}
    options.add_experimental_option("excludeSwitches", ["enable-automation"])  # 移除"自动化控制"提示:ml-citation{ref="1,8" data="citationList"}
    # options.add_experimental_option("useAutomationExtension", False)  # 禁用自动化扩展:ml-citation{ref="4,8" data="citationList"}
    # options.add_argument('--disable-dev-shm-usage')
    # options.add_argument('--disable-gpu')

# # 禁用非必要资源加载（加速页面渲染）
    # options.add_experimental_option("prefs", {
    #     "profile.managed_default_content_settings.images": 2,  # 禁用图片
    #     "profile.managed_default_content_settings.javascript": 1  # 启用JS
    # })
    options.set_capability("webdriver:useBidi", True)
    # options.add_argument("--incognito")
    # options.add_argument("--disable-application-cache")
    options.add_argument("start-maximized")
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    driver.implicitly_wait(10)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
    )  # 彻底隐藏webdriver属性:ml-citation{ref="7,8" data="citationList"}
    # driver.execute_cdp_cmd("Network.setUserAgentOverride", {
    #     "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    # })
    return driver


def close_driver(driver: webdriver):
    driver.quit()


def full_reset(driver, mode='DEBUG'):
    """完全重置浏览器到初始状态"""
    close_driver(driver)
    new_driver = get_driver(mode)  # 创建新实例
    return new_driver


def get_undetected_driver(mode='DEBUG'):
    import random
    options = uc.ChromeOptions()

    # 1. 设置真实的 User-Agent（使用固定版本避免随机问题）
    # options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.7827.104 Safari/537.36")

    # 2. 配置语言
    options.add_argument("--lang=en-JP")

    # 3. 禁用自动化特征标识
    options.add_argument("--disable-blink-features=AutomationControlled")

    # 4. 必要的运行选项
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")

    # 5. 设置窗口大小
    options.add_argument("--window-size=1920,1080")

    # 使用 webdriver_manager 获取与当前Chrome版本匹配的驱动路径
    driver_path = ChromeDriverManager().install()

    # 使用undetected_chromedriver创建驱动
    driver = uc.Chrome(driver_executable_path=driver_path, options=options)

    # 隐藏更多浏览器指纹
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
                Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
                Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 4 });
            """
        }
    )

    # 设置额外的CDP配置
    driver.execute_cdp_cmd("Network.enable", {})
    driver.execute_cdp_cmd(
        "Network.setExtraHTTPHeaders",
        {"headers": {"Accept-Language": "en-US,en;q=0.9,ja;q=0.8"}}
    )

    # 模拟真实用户行为：添加随机延迟
    time.sleep(random.uniform(2, 5))

    return driver


def close_undetected_driver(driver):
    try:
        driver.quit()
    except Exception as e:
        pass
    finally:
        try:
            driver.service.stop()
        except Exception as e:
            # 服务可能已经停止，忽略连接关闭错误
            pass


def get_playwright_driver(mode='DEBUG'):
    """使用Playwright创建浏览器驱动，提供更强的反检测能力"""
    from playwright.sync_api import sync_playwright
    import random
    import time
    
    playwright = sync_playwright().start()
    
    # 启动浏览器，添加更多反检测参数
    browser = playwright.chromium.launch(
        headless=(mode != 'DEBUG'),
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--hide-scrollbars",
            "--mute-audio",
            "--disable-web-security",
            "--allow-running-insecure-content",
            "--disable-site-isolation-trials",
            "--disable-features=VizDisplayCompositor",
            "--disable-features=RendererCodeIntegrity",
            "--start-maximized",
            f"--window-size={random.randint(1200, 1920)},{random.randint(700, 1080)}",
        ],
        ignore_default_args=["--enable-automation"],
    )
    
    # 创建上下文，配置用户代理和视图大小
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.7827.104 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.7827.155 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.7827.104 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.7780.101 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.7827.104 Safari/537.36"
    ]
    
    context = browser.new_context(
        user_agent=random.choice(user_agents),
        viewport={"width": random.randint(1200, 1920), "height": random.randint(700, 1080)},
        locale="en-JP",
        timezone_id="Asia/Tokyo",
        geolocation={"latitude": 35.6762, "longitude": 139.6503},  # 东京坐标
        permissions=["geolocation"],
        extra_http_headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Ch-Ua": '"Chromium";v="149", "Not;A=Brand";v="24", "Google Chrome";v="149"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
    )
    
    # 添加完整的反检测脚本
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en', 'ja'] });
        Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
        Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
        Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => Math.floor(Math.random() * 4) + 4 });
        Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 0 });
        Object.defineProperty(window, 'chrome', {
            value: {
                runtime: { id: '' }
            },
            writable: true
        });
        Object.defineProperty(navigator, 'vendor', { get: () => 'Google Inc.' });
        Object.defineProperty(navigator, 'product', { get: () => 'Gecko' });
        Object.defineProperty(navigator, 'productSub', { get: () => '20030107' });
        Object.defineProperty(navigator, 'appVersion', { get: () => '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.7827.104 Safari/537.36' });
        Object.defineProperty(navigator, 'userAgent', { get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.7827.104 Safari/537.36' });
        
        // 模拟真实的WebGL指纹
        const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) { // WEBGL_debug_renderer_info
                return 'Google Inc. (NVIDIA)';
            }
            if (parameter === 37446) {
                return 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060/PCIe/SSE2, OpenGL 4.5.0)';
            }
            return originalGetParameter.call(this, parameter);
        };
        
        // 清除webdriver痕迹
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_;
        delete window.__driver_evaluate;
        delete window.__webdriver_evaluate;
        delete window.__selenium_evaluate;
        delete window.__driver_unwrapped;
        delete window.__webdriver_unwrapped;
        delete window.__selenium_unwrapped;
        delete window.__fxdriver_evaluate;
        delete window.__driver_script_func;
        delete window.__webdriver_script_func;
        delete window.__selenium_script_func;
        delete window.__fxdriver_script_func;
        delete window._phantom;
        delete window.callPhantom;
        delete window._selenium;
        delete window.Selenium;
        delete window.webdriver;
        delete window.$cdc_asdjflasutopfhvcZLmcfl_;
    """)
    
    page = context.new_page()
    
    # 设置页面加载超时
    page.set_default_timeout(120000)
    
    # 启用网络拦截，添加随机延迟
    page.route("**/*", lambda route: route.continue_())
    
    # 模拟真实用户的初始延迟
    time.sleep(random.uniform(3, 6))
    
    # 返回一个元组，包含page, context, browser供后续关闭使用
    return page, context, browser


def random_delay(min_seconds=2, max_seconds=5):
    """添加随机延迟，模拟真实用户行为"""
    import random
    import time
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)
    return delay


def simulate_human_behavior(page):
    """模拟真实用户行为：鼠标移动、滚动、点击等"""
    import random
    import time
    
    try:
        # 模拟鼠标随机移动
        viewport = page.viewport_size
        if viewport:
            x = random.randint(100, viewport['width'] - 100)
            y = random.randint(100, viewport['height'] - 100)
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.5, 1.5))
            
            # 模拟鼠标滚动
            scroll_amount = random.randint(100, 500)
            page.evaluate(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(0.3, 1.0))
            
            # 随机滚动回顶部
            if random.random() > 0.7:
                page.evaluate("window.scrollTo(0, 0);")
                time.sleep(random.uniform(0.5, 1.0))
    except Exception:
        pass


def safe_goto(page, url, max_retries=3, delay_between_retries=5):
    """安全跳转页面，支持重试机制"""
    import random
    import time
    from playwright._impl._api_types import TimeoutError as PlaywrightTimeoutError
    
    for attempt in range(max_retries):
        try:
            page.goto(url, wait_until='networkidle', timeout=120000)
            # 添加随机延迟
            time.sleep(random.uniform(3, 7))
            # 模拟用户行为
            simulate_human_behavior(page)
            return True
        except PlaywrightTimeoutError:
            log_util.error(f"页面加载超时，第{attempt+1}次尝试")
            if attempt < max_retries - 1:
                time.sleep(delay_between_retries * (attempt + 1))
        except Exception as e:
            log_util.error(f"页面跳转失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(delay_between_retries * (attempt + 1))
    return False


# ======== scrapling[fetchers] 支持函数 ========

# StealthySession 全局实例（避免重复创建）
_browser_session = None
_browser_count = 0
_browser_warmed = False
_current_base_url = None  # 当前会话的基础URL

# 默认配置（可被调用方覆盖）
DEFAULT_CONFIG = {
    "recycle_every": 25,
    "delay_between": 1.5,
    "failover_min_len": 30000,
    "base_url": "https://www.patagonia.jp",
    "home_url": "https://www.patagonia.jp/home/",
    "warmup_timeout": 30000,
}


def _is_failover(html: str, min_len: int = 30000) -> bool:
    """检测 failover 页面（反爬拦截）
    
    Args:
        html: 页面内容
        min_len: 最小长度阈值，小于此长度可能是failover页面
        
    Returns:
        True 如果检测到failover特征，False 否则
    """
    # 如果内容为空，肯定是失败
    if not html:
        return True
    
    # 记录调试信息
    log_util.info(f"页面长度: {len(html)} 字节")
    
    # 检测 failover 特征字符串（更严格的检测）
    lowered = html[:5000].lower()
    has_failover = "spa-sitefailover" in lowered or "botfailover" in lowered or "sit tight" in lowered
    
    if has_failover:
        log_util.info(f"检测到 failover 特征: spa-sitefailover={('spa-sitefailover' in lowered)}, botfailover={('botfailover' in lowered)}, sit tight={('sit tight' in lowered)}")
        return True
    
    # 对于 API 响应（如 JSON），长度可能很小，不应该被判定为 failover
    # 只对 HTML 页面应用长度检测
    if len(html) < min_len:
        # 检查是否是 HTML 页面
        if html.strip().startswith("<!DOCTYPE") or html.strip().startswith("<html"):
            log_util.info(f"HTML页面长度 {len(html)} < {min_len}，判定为 failover")
            return True
        else:
            # 可能是 API 响应（JSON等），不判定为 failover
            log_util.info(f"非HTML响应，长度 {len(html)}，不判定为 failover")
            return False
    
    return False


def _ensure_browser(config: dict = None):
    """确保浏览器会话已初始化并预热"""
    global _browser_session, _browser_count, _browser_warmed, _current_base_url
    from scrapling.fetchers import StealthySession
    import time
    
    # 使用默认配置或传入的配置
    cfg = config or DEFAULT_CONFIG
    
    if _browser_session is None:
        log_util.info("初始化 StealthySession...")
        _browser_session = StealthySession(
            headless=False,          # 必须使用有头模式（反爬检测）
            network_idle=True,
            humanize=True,
            os_randomize=True,
            google_search=True,      # referer 设置为 Google
            disable_resources=False, # 加载所有资源
            timeout=60000,           # 超时时间（60秒）
        )
        _browser_session.start()
        _browser_warmed = False
        _browser_count = 0
        _current_base_url = cfg["base_url"]
    
    if not _browser_warmed:
        home_url = cfg.get("home_url", f"{cfg['base_url']}/home/")
        warmup_timeout = cfg.get("warmup_timeout", 30000)
        delay_between = cfg.get("delay_between", 1.5)
        log_util.info(f"预热会话 ({home_url})")
        try:
            log_util.info(f"开始预热，超时时间: {warmup_timeout}ms")
            _browser_session.fetch(
                home_url, 
                network_idle=True, 
                wait=5000,           # 减少等待时间
                timeout=warmup_timeout  # 预热超时
            )
            log_util.info("预热完成")
            _browser_warmed = True
            time.sleep(delay_between)
        except Exception as e:
            log_util.error(f"预热失败（继续）: {e}")
            _browser_warmed = True


def _recycle_browser():
    """回收浏览器会话（防止长时间访问被封）"""
    global _browser_session, _browser_warmed, _browser_count, _current_base_url
    
    if _browser_session is not None:
        log_util.info(f"处理 {_browser_count} 件后回收会话")
        try:
            _browser_session.close()
        finally:
            _browser_session = None
            _browser_warmed = False
            _browser_count = 0
            _current_base_url = None


def _maybe_recycle(recycle_every: int = 25):
    """检查是否需要回收会话"""
    global _browser_count
    if recycle_every > 0 and _browser_count > 0 and _browser_count % recycle_every == 0:
        _recycle_browser()


def _get_html(response) -> str:
    """从响应中提取 HTML 内容"""
    body = getattr(response, "body", b"")
    if isinstance(body, bytes) and body:
        return body.decode("utf-8", "ignore")
    text = getattr(response, "text", "")
    return text if isinstance(text, str) else ""


def fetch_with_scrapling(url, retries=3, config: dict = None):
    """
    使用 scrapling.fetchers.StealthySession 获取网页内容（反爬优化版）
    参照 patagonia_scrapling/main.py 实现

    Args:
        url (str): 目标网页的URL（支持相对路径，会自动转换为完整URL）。
        retries (int): 请求失败时的重试次数。
        config (dict): 可选配置字典，包含以下键：
            - base_url: 网站基础URL（用于相对路径转换）
            - home_url: 首页URL（用于会话预热）
            - recycle_every: 会话回收间隔（默认25）
            - delay_between: 请求间隔（默认1.5秒）
            - failover_min_len: failover检测最小长度（默认30000）
            - warmup_timeout: 预热超时（默认30000ms）

    Returns:
        bytes: 网页的HTML内容（字节串），如果失败则返回 None。
    """
    global _browser_count
    import time
    from urllib.parse import urljoin
    
    # 使用默认配置或传入的配置
    cfg = config or DEFAULT_CONFIG
    
    last_html = ""
    
    # 将相对路径转换为完整URL
    base_url = cfg.get("base_url", "https://www.patagonia.jp")
    if url.startswith("/"):
        url = urljoin(base_url, url)
        log_util.info(f"转换相对路径: {url}")
    
    for attempt in range(retries + 1):
        _ensure_browser(cfg)
        
        try:
            log_util.info(f"获取页面 ({attempt+1}/{retries+1}): {url}")
            response = _browser_session.fetch(url, network_idle=True)
            
            html = _get_html(response)
            
            failover_min_len = cfg.get("failover_min_len", 30000)
            if not _is_failover(html, failover_min_len):
                _browser_count += 1
                recycle_every = cfg.get("recycle_every", 25)
                _maybe_recycle(recycle_every)
                delay_between = cfg.get("delay_between", 1.5)
                time.sleep(delay_between)
                return html.encode("utf-8")
            
            last_html = html
            log_util.error(f"检测到 failover 页面，重试 ({attempt+1}/{retries+1})")
            
            # failover 后回收会话并等待
            _recycle_browser()
            delay_between = cfg.get("delay_between", 1.5)
            time.sleep(delay_between * (attempt + 2))
            
        except Exception as e:
            log_util.error(f"请求异常 ({attempt+1}/{retries+1}): {e}")
            _recycle_browser()
            delay_between = cfg.get("delay_between", 1.5)
            time.sleep(delay_between * 2)
    
    return last_html.encode("utf-8") if last_html else None


def close_playwright_driver(page, context, browser):
    """关闭Playwright浏览器资源"""
    try:
        if page:
            page.close()
    except Exception:
        pass
    try:
        if context:
            context.close()
    except Exception:
        pass
    try:
        if browser:
            browser.close()
    except Exception:
        pass


BLOCK_KEYWORDS = [
    "执行安全验证",
    "セキュリティ検証",
    "Security Verification",
    "Verify you are human",
    "Checking your browser",
    "Access Denied",
]

def is_blocked_page(driver):
    try:
        # 获取页面源码（速度较快）
        source = driver.page_source.lower()

        # 检查是否包含任何封锁关键词
        for keyword in BLOCK_KEYWORDS:
            if keyword.lower() in source:
                return True

        # 也可以检查 title (有时 title 会直接显示 "Security Check")
        title = driver.title.lower()
        for keyword in BLOCK_KEYWORDS:
            if keyword.lower() in title:
                return True

        return False
    except Exception:
        # 如果无法获取源码，保守起见认为正常，或者根据具体报错处理
        return False

def wait_for_stable_chips(driver, xpath_str, timeout=15):
    end_time = time.time() + timeout
    last_count = -1
    stable_count = 0
    required_stable_times = 2 # 连续2次数量一致视为稳定
    check_interval = 0.5

    while time.time() < end_time:
        try:
            # 查找元素
            elements = driver.find_elements(By.XPATH, xpath_str)
            current_count = len(elements)

            if current_count == 0:
                time.sleep(check_interval)
                continue

            # 打印调试信息 (可选)
            # print(f"当前找到: {current_count}, 上次: {last_count}, 稳定计数: {stable_count}")

            if current_count == last_count:
                stable_count += 1
                if stable_count >= required_stable_times:
                    print(f"✅ 加载稳定！共找到 {current_count} 个选项。")
                    return elements
            else:
                stable_count = 0
                last_count = current_count

            time.sleep(check_interval)

        except Exception as e:
            time.sleep(check_interval)

    # 超时返回
    final_elements = driver.find_elements(By.XPATH, xpath_str)
    print(f"⚠️ 等待超时，最终返回 {len(final_elements)} 个元素。")
    return final_elements