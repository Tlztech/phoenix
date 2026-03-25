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
    driver = uc.Chrome(headless=False if mode == "DEBUG" else True)
    return driver


def close_undetected_driver(driver):
    try:
        driver.quit()
    except Exception as e:
        pass
    finally:
        driver.service.stop()

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