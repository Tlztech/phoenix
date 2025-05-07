import requests
import chardet
import html

from util import log_util
from lxml import etree
from requests import RequestException, HTTPError, Timeout, TooManyRedirects, URLRequired

from selenium import webdriver
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
    return driver


def close_driver(driver: webdriver):
    driver.quit()
