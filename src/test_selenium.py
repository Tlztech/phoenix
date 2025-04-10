import sys
import os

sys.path.append(os.path.abspath('.'))  # 添加当前目录到 sys.path
from selenium import webdriver
from selenium.common import TimeoutException, ElementNotInteractableException
from selenium.webdriver import Keys, ActionChains
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from lxml import etree
from util import crawler_util
import time
import json


def wait_for_stability(driver, timeout=10):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState === 'complete'")
    )


driver = crawler_util.get_driver()
driver.get('https://item.rakuten.co.jp/kagamicrystal/tps370-2943-ab/')
element = driver.find_element(By.XPATH, "//div[text()='この商品は売り切れです']")
print(element.text)
exit(0)

try:
    element = driver.find_element(By.XPATH, "//*[@id='countrySelectorModal']/div/div/div[1]/button")
    if element.is_displayed():
        element.click()
        time.sleep(1)

    element = driver.find_element(By.XPATH, "//*[@id='global-search-field']")
    element.send_keys("prod9750541")
    time.sleep(0.5)
    element.send_keys(Keys.RETURN)

    # driver.get("https://www.lululemon.co.jp/on/demandware.store/Sites-JP-Site/ja_JP/Product-Variation?dwvar_prod9750541_color=12826&dwvar_prod9750541_size=8&pid=prod9750541&quantity=1")
    # print(driver.page_source)
    # tree = etree.HTML(driver.page_source)
    # print(json.loads(tree.xpath("//pre/text()")[0]))
    # driver.quit()
    # exit(0)
    # 等待元素出现
    color_elements = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@class, 'swatchAnchor')]"))
    )
    for color_element in color_elements:
        url = color_element.get_attribute("data-swatch-url")
        print(f"url:{url}")
        color_title = color_element.get_attribute("title")
        print(f"color:{color_title}")
        # driver.get(url)
        # # 等待元素出现
        # total_size_elements = len(WebDriverWait(driver, 10).until(
        #     EC.presence_of_all_elements_located((By.XPATH, "//div[@id='size']/div/span/input[contains(@class, 'options-select') and not(contains(@class, 'disabled'))]"))
        # ))
        # element = WebDriverWait(driver, 10).until(
        #     EC.presence_of_element_located((By.XPATH, "//a[@id='bisn-size-sold-out-link']"))
        # )
        # ActionChains(driver).scroll_to_element(element).perform()
        # time.sleep(1)
        # for index in range(total_size_elements):
        #     # size_elements = WebDriverWait(driver, 10).until(
        #     #     EC.presence_of_all_elements_located((By.XPATH, "//div[@id='size']/div/span/input[contains(@class, 'options-select') and not(contains(@class, 'disabled'))]"))
        #     # )
        #     current_element = WebDriverWait(driver, 10).until(
        #         EC.presence_of_element_located((
        #             By.XPATH,
        #             f"(//div[@id='size']/div/span/input[contains(@class, 'options-select') and not(contains(@class, 'disabled'))])[{index+1}]"  # 动态定位索引
        #         ))
        #     )
        #     # current_element = size_elements[index]
        #     print(f"size:{current_element.get_attribute('aria-label')}")
        #     # ActionChains(driver).move_to_element(current_element).perform()
        #     # driver.execute_script("arguments.scrollIntoView({block: 'center'});", current_element)
        #     # driver.scroll_to_element(current_element)
        #     try:
        #         # 标准点击流程
        #         current_element.click()
        #     except ElementNotInteractableException:
        #         # parent_span = current_element.find_element(By.XPATH, "./parent::span")
        #         # parent_span.click()
        #         # wait_for_stability(driver)
        #         driver.execute_script("arguments.click();", current_element.find_element(By.XPATH, "./parent::span"))
        #     price_element = WebDriverWait(driver, 10).until(
        #         EC.presence_of_element_located((By.XPATH, "//div[@class='cart-and-ipay']//span[@class='markdown-prices']"))
        #     )
        #     print(f"price:{price_element.text}")


    # total_elements = len(driver.find_elements(By.XPATH, "//a[contains(@class, 'swatchAnchor')]"))
    # for index in range(total_elements):
    #     # 每次循环重新获取最新元素列表
    #     elements = WebDriverWait(driver, 10).until(
    #         EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@class, 'swatchAnchor')]"))
    #     )
    #     current_element = elements[index]
    #     current_element.click()
    #     time.sleep(1)
    #     # element_image = driver.find_element(By.XPATH, "//div[@class='image-container']/a[@title='prod9750541']")
    #     element_image = WebDriverWait(driver, 10).until(
    #         EC.presence_of_element_located((By.XPATH, "//div[@class='image-container']/a[@title='prod9750541']"))
    #     )
    #     href = element_image.get_attribute("href")
    #     print(href)
    #     element_image.click()
    #     # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    #     # print("Clicked:", element.text)
    #     time.sleep(1)
    #     driver.back()
    #     # 等待原页面重新加载完成
    #     WebDriverWait(driver, 10).until(
    #         EC.presence_of_all_elements_located((By.XPATH, "//a[contains(@class, 'swatchAnchor')]"))
    #     )

    # print(driver.page_source)  # 获取页面源代码
except TimeoutException:
    # 元素未在指定时间内出现
    print("元素未加载")
driver.quit()
