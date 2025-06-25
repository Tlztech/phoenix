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


