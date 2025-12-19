'''
执行此脚本会自动从官方网页爬取并更新所有卡牌信息
https://hearthstone.blizzard.com/zh-tw/battlegrounds?bgCardType=minion

'''
from idlelib.rpc import response_queue
from zoneinfo import reset_tzpath

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, \
    StaleElementReferenceException, NoSuchElementException, ElementClickInterceptedException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import time
import random
import os
from urllib.parse import urljoin, urlparse, parse_qs
import logging
from tqdm import tqdm

# 日志
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)

class Pa:
    # 初始化
    def __init__(self,
                 cache_dir='asserts',
                 use_proxy=False,
                 proxy='127.0.0.1:7890'
                 ):
        # 缓存设置
        self.cache_dir = cache_dir
        self._create_cache_dir()

        # 代理设置
        if use_proxy:
            self._set_proxy(proxy)

        # Selenium设置
        self.base_url = "https://hearthstone.blizzard.com/zh-tw/battlegrounds?bgCardType=minion"
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument(
            f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        self.driver.implicitly_wait(10)  # 隐式等待时间
        self.driver.set_page_load_timeout(60)  # 页面加载超时时间
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})") # 移除webdriver特征

    """创建缓存文件夹"""
    def _create_cache_dir(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
        for dir in ['img', 'json']:
            cur_path = os.path.join(self.cache_dir, dir)
            if not os.path.exists(cur_path):
                os.makedirs(cur_path, exist_ok=True)
            for dir_name in ['hero', 'minion', 'spell', 'task', 'award', 'mutation', 'accessories', 'timeWarp']:
                res_path = os.path.join(cur_path, dir_name)
                if not os.path.exists(res_path):
                    os.makedirs(res_path, exist_ok=True)

    """保存数据到JSON文件"""
    def _save_json(self, data, filename):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            logging.info(f"save json to {filename}")
        except Exception as e:
            logging.error(f"failed to save json: {str(e)}")

    """设置代理"""
    def _set_proxy(self, proxy):
        os.environ['http_proxy'] = proxy
        os.environ['https_proxy'] = proxy

    """从缓存文件中加载数据"""
    def _load_cached_json(self, filename):
        try:
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logging.info(f"load from: {filename}")
                return data
            return None
        except Exception as e:
            logging.error(f"load json failed: {str(e)}")
            return None

    """使用Selenium获取页面并返回BeautifulSoup对象"""
    def _get_soup(self, url, wait_for=None, timeout=30):
        try:
            # 添加随机延迟
            time.sleep(random.uniform(2, 4))
            self.driver.get(url)
            logging.info(f"get pages {url}")

            # 等待指定元素加载完成
            if wait_for:
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located(wait_for)
                )
            else:
                # 等待body加载完成
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'body'))
                )

            # 要额外等待一会
            time.sleep(random.uniform(2, 5))
            # 获取页面内容
            page_source = self.driver.page_source
            # 检查响应内容
            if not page_source.strip():
                logging.warning(f"page {url} is empty")
                return None
            return BeautifulSoup(page_source, 'html.parser')
        except TimeoutException:
            logging.error(f"get page {url} timed out")
            return None
        except Exception as e:
            logging.error(f"get page {url} failed: {str(e)}")
            return None


