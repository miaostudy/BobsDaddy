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
import json
import time
import random
import os
from urllib.parse import urljoin, urlparse, parse_qs
import logging
from tqdm import tqdm
from selenium.webdriver.common.action_chains import ActionChains
import re

# 调整工作目录到根目录
work_dir =os.getcwd()
if work_dir.split('\\')[-1] == 'data':
    os.chdir(os.path.join(work_dir, '../'))

# 日志
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler("./logs/scraper.log"),
        logging.StreamHandler()
    ]
)

class UpdateEverything:
    # 初始化
    def __init__(self,
                 cache_dir='asserts',
                 use_proxy=False,
                 proxy='127.0.0.1:7890'
                 ):
        # 缓存设置
        self.cache_dir = cache_dir
        self.json_caches_path = os.path.join(self.cache_dir, 'jsons')
        self._create_cache_dir()


        # 代理设置
        if use_proxy:
            self._set_proxy(proxy)

        # Selenium设置
        self.base_url = "https://hearthstone.blizzard.com/zh-tw/battlegrounds"
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
        self.wait = WebDriverWait(self.driver, 15) # 通用的等待时间

        # 卡牌信息
        self.count = 0
        self.ids = []
    """创建缓存文件夹"""
    def _create_cache_dir(self):
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
        dir_names = {
            'imgs' : ['hero', 'minion', 'spell', 'task', 'award', 'mutation', 'accessories', 'timeWarp'],
            'jsons' : []
        }
        for dir in ['imgs', 'jsons']:
            cur_path = os.path.join(self.cache_dir, dir)
            if not os.path.exists(cur_path):
                os.makedirs(cur_path, exist_ok=True)
            for dir_name in dir_names[dir]:
                res_path = os.path.join(cur_path, dir_name)
                if not os.path.exists(res_path):
                    os.makedirs(res_path, exist_ok=True)


    """保存数据到JSON文件"""
    # TODO 修改成加入单个json数据
    def _add_element_to_cache(self, data, filename):
        try:
            if not isinstance(data, dict):
                logging.error(f"保存失败：预期输入是字典，但收到了 {type(data)}")
                return


            with open(filename, 'a', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            logging.info(f"成功保存缓存至 {filename}")

        except Exception as e:
            logging.error(f"保存缓存失败: {e}")

    """设置代理"""
    def _set_proxy(self, proxy):
        os.environ['http_proxy'] = proxy
        os.environ['https_proxy'] = proxy

    """从缓存文件中加载数据"""
    def _load_cached_json(self, filename):
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                pass
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    return {}

                data_list = json.loads(content)

                if not isinstance(data_list, list):
                    logging.warning("缓存文件格式错误，重置为空")
                    return {}

                cache_dict = {}
                for item in data_list:
                    if 'id' in item:
                        cache_dict[int(item['id'])] = item

                logging.info(f"成功加载缓存，共 {len(cache_dict)} 条数据")
                return cache_dict

        except Exception as e:
            logging.error(f"加载缓存失败: {e}")
            return {}

    """使用Selenium获取页面并返回BeautifulSoup对象"""
    # def _get_soup(self, url, wait_for=None, timeout=30):
    #     try:
    #         # 添加随机延迟
    #         time.sleep(random.uniform(2, 4))
    #         self.driver.get(url)
    #         logging.info(f"get pages {url}")
    #
    #         # 等待指定元素加载完成
    #         if wait_for:
    #             WebDriverWait(self.driver, timeout).until(
    #                 EC.presence_of_element_located(wait_for)
    #             )
    #         else:
    #             # 等待body加载完成
    #             WebDriverWait(self.driver, timeout).until(
    #                 EC.presence_of_element_located((By.TAG_NAME, 'body'))
    #             )
    #
    #         # 要额外等待一会
    #         time.sleep(random.uniform(2, 5))
    #         # 获取页面内容
    #         page_source = self.driver.page_source
    #         # 检查响应内容
    #         if not page_source.strip():
    #             logging.warning(f"page {url} is empty")
    #             return None
    #         return page_source
    #     except TimeoutException:
    #         logging.error(f"get page {url} timed out")
    #         return None
    #     except Exception as e:
    #         logging.error(f"get page {url} failed: {str(e)}")
    #         return None

    """点击元素并等待指定条件满足"""
    def _click_and_wait(self, element_locator, wait_condition=None, retry=3):
        try:
            # 等待元素可点击
            element = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable(element_locator)
            )

            # 滚动到元素可见位置
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(random.uniform(1, 2))  # 等待滚动完成

            # 点击元素
            element.click()
            logging.info(f"click element: {element_locator}")

            # 如果有指定等待条件，则等待其满足
            if wait_condition:
                WebDriverWait(self.driver, 20).until(wait_condition)
                time.sleep(random.uniform(1, 3))  # 等待内容加载
            return True
        except (TimeoutException, ElementClickInterceptedException, StaleElementReferenceException) as e:
            logging.warning(f"click element {element_locator} failed: {str(e)}")
            if retry > 0:
                time.sleep(random.uniform(5, 10))
                try:
                    # 重新查找元素
                    element = self.driver.find_element(*element_locator)
                    self.driver.execute_script("arguments[0].click();", element)
                    logging.info(f"Use JavaScript to click element: {element_locator}")

                    if wait_condition:
                        WebDriverWait(self.driver, 20).until(wait_condition)
                        time.sleep(random.uniform(1, 3))
                    return True
                except Exception as js_e:
                    logging.warning(f"JavaScript click element {element_locator} failed: {str(js_e)}")
                    return self._click_and_wait(element_locator, wait_condition, retry - 1)
            return False

    """点击第一个随从"""
    def _click_first_minion(self):
        # 找到外层包裹
        try:
            wrapper = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.CardWrap"))
            )
            target_url = wrapper.get_attribute("href")
            logging.info(f"找到第一张卡牌，目标链接是: {target_url}")

            card_image = wrapper.find_element(By.CSS_SELECTOR, ".CardImage")
            # 滚动到卡牌位置
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card_image)
            time.sleep(1)
            # 鼠标移到卡上，防止有东西没加载出来
            actions = ActionChains(self.driver)
            actions.move_to_element(card_image).perform()
            time.sleep(0.5)
            # 尝试点击
            logging.info('正在点击第一张卡')
            try:
                card_image.click()
            except Exception as e:
                time.sleep(0.5)
                logging.warning('点击失败，尝试使用JS点击')
                self.driver.execute_script("arguments[0].click();", card_image)
        except Exception as e:
            logging.info(f'点击第一个随从失败')
            logging.error(e)

        logging.info("点击成功")
        
    def _get_total_count(self):
        try:
            count_element = self.wait.until(
                EC.visibility_of_element_located((By.XPATH, "//div[contains(text(), '在英雄戰場中找到')]"))
            )
            text = count_element.text
            match = re.search(r'(\d+)', text)
            if match:
                count = int(match.group(1))
                logging.info(f"文本显示共有 {count} 张卡牌")
            else:
                count = -1
            # 滚动循环，加载所有的CardWarper
            last_card_count = 0
            retry_count = 0
            max_retries = 3 # 连续滚动多少次没有新卡牌，就退出

            while True:
                time.sleep(2)
                # 当前页面上卡牌数量
                cards = self.driver.find_elements(By.CSS_SELECTOR, "a.CardWrap")
                current_card_count = len(cards)
                logging.info(f"当前已加载: {current_card_count} 张")

                # 是否到底
                if current_card_count > last_card_count:
                    last_card_count = current_card_count
                    retry_count = 0
                else:
                    retry_count += 1
                    logging.info(f"数量未增加，正在确认是否到底... ({retry_count}/{max_retries})")

                    # 尝试稍微往回滚一点再滚下去
                    if retry_count == 1:
                        self.driver.execute_script("window.scrollBy(0, -200);")
                        time.sleep(0.5)
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    if retry_count >= max_retries:
                        logging.info("已到达页面底部，停止滚动。")
                        break
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            logging.info("开始提取链接...")

            final_cards = self.driver.find_elements(By.CSS_SELECTOR, "a.CardWrap")
            for card in final_cards:
                id = self._url2id(card.get_attribute("href"))
                self.ids.append(id)
            logging.info(f'官方标明的随从数量:{count}, 提取到的卡牌数量:{len(final_cards)}')

            if count > 0 and len(final_cards) > 0:
                if count > len(final_cards):
                    logging.warning(f'提取到的卡牌数量少于官方标明的数量')
                    return count
                elif count < len(final_cards):
                    logging.warning(f'提取到的卡牌数量多于官方标明的数量，可以提取到的数量为准')
            if count <= 0:
                logging.warning(f'未获取到官方标明的卡牌数量')
            return len(final_cards)
        except Exception as e:
            logging.info(f'获取卡牌数量失败: {e}')
    def _url2id(self, url):
        return url.split("/")[-1].rsplit("-")[0]

    def _parse_one_minion(self, id):
        logging.info(f'缓存中没有随从{id}, 开始获取详细信息')
        data = {}
        try:
            self.wait.until(
                EC.visibility_of_element_located((By.CLASS_NAME, "card-change-animated"))
            )
            card_containers = self.driver.find_elements(By.CLASS_NAME, "card-change-animated")
            card_container = card_containers[-1]
            name_element = card_container.find_element(By.TAG_NAME, "h3")
            data['id'] = id
            try:
                items = card_container.find_elements(By.CSS_SELECTOR, "ul > li")
                for item in items:
                    text = item.text
                    if ":" in text:
                        key, val = text.split(":", 1)
                        if key.strip() == '類型':
                            data['type'] = val.strip()
                        elif key.strip() == '手下類別':
                            data['race'] = [i.strip() for i in val.strip().split(',')]
            except:
                pass
            data['name'] = name_element.text
            descriptions = card_container.find_elements(By.TAG_NAME, "p")
            data['description'] = "\n".join([p.text for p in descriptions if p.text.strip()])
            data['used'] = True
            return data
        except Exception as e:
            logging.error(f'解析随从{id}失败, {e}')

    """获取当前页面上所有具体随从信息"""
    def _get_all_minions(self):
        '''
        :return: [{}, {}, ....]
        '''
        minions = []
        for i in range(self.count):
            cur_id = self._url2id(self.driver.current_url)
            print(cur_id)
            # 加载缓存
            minions_cache_path = os.path.join(self.json_caches_path, 'minions.json')
            cache = self._load_cached_json(minions_cache_path)
            if cache.get(cur_id):
                minions.append(cache[cur_id])
            else:
                data = self._parse_one_minion(cur_id)
                self._add_element_to_cache(data, minions_cache_path)
                # 点击next按钮
                next_btn = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a[direction='next']"))
                )
                self.driver.execute_script("arguments[0].click();", next_btn)

    def get_default_card_schema(self, card_type='minion'):
        """
        返回标准卡牌数据结构
        """
        return {
            "id": None,
            "type": card_type,
            "race": [],
            "name": None,
            "description": None,
            "attack": None,
            "health": None,
            "addiction": [],
            "golden": {
                "name": None,
                "description": None,
                "attack": None,
                "health": None
            },
            "used": True
        }
    """解析随从"""
    def get_minions(self,force_refresh=False):
        logging.info(f"get minions ...")
        minions_url = self.base_url + "?bgCardType=minion"
        logging.info(f"正在访问列表页: {minions_url}")
        self.driver.get(minions_url)

        # 获取随从牌数量
        self.count = self._get_total_count()
        # 点击第一张随从卡
        self._click_first_minion()
        # 获取所有随从信息
        self._get_all_minions()

        # 检查缓存




updater = UpdateEverything()
updater.get_minions()
