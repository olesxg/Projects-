"""
Модуль з класами для завантаження та парсингу веб-сторінок.
"""
import time
import logging
import requests
from typing import List, Optional, Dict, Any
import json
import os
import asyncio
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random
from playwright.async_api import async_playwright
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

import httpx
from models import Leaflet
from utils import parse_date_range, validate_url

logger = logging.getLogger('prospekt_scraper')


class Scraper:
    """
    Клас для завантаження та парсингу веб-сторінок з проспектами.
    """
    
    def __init__(self, base_url: str = 'https://www.prospektmaschine.de/hypermarkte/'):
        """
        Ініціалізація скрапера.
        
        Args:
            base_url: Основний URL для парсингу
        """
        self.base_url = base_url
        self.session = self._create_session()
        # Список відомих супермаркетів для розпізнавання
        self.known_shops = [
            "Aldi", "Lidl", "Rewe", "Edeka", "Kaufland", "Penny", "Netto", 
            "Real", "Metro", "Globus", "Hit", "Norma", "Marktkauf", "Famila", 
            "Bünting", "Combi", "Tegut", "Kaisers", "Tengelmann", "V-Markt",
            "dm", "Rossmann", "Müller", "Alnatura", "Denn's", "Basic", "Bio Company",
            "Wasgau", "Walmart", "Dohle", "Rewe Center", "E-Center", "EDEKA"
        ]
        
    def _create_session(self) -> requests.Session:
        """
        Створює сесію з налаштуваннями повторних спроб.
        
        Returns:
            requests.Session: Сесія з налаштуваннями
        """
        session = requests.Session()
        
        # Налаштування повторних спроб
        retry_strategy = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Розширені заголовки для обходу захисту
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        })
        
        return session
        
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Завантажує сторінку та повертає об'єкт BeautifulSoup.
        
        Args:
            url: URL сторінки для завантаження
            
        Returns:
            Optional[BeautifulSoup]: Об'єкт BeautifulSoup або None, якщо завантаження не вдалося
        """
        try:
            logger.info(f"Завантаження сторінки: {url}")
            
            # Додаємо випадкову затримку
            time.sleep(random.uniform(2, 5))
            
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Зберігаємо HTML для відлагодження
            with open('debug.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.debug(f"Збережено HTML для відлагодження в debug.html")
            
            return BeautifulSoup(response.text, 'lxml')
            
        except requests.RequestException as e:
            logger.error(f"Помилка при завантаженні сторінки {url}: {str(e)}")
            return None
            
    def _extract_shop_name(self, title: str, texts: List[str]) -> str:
        """
        Витягує назву магазину з тексту.
        
        Args:
            title: Заголовок проспекту
            texts: Список текстів з блоку проспекту
            
        Returns:
            str: Назва магазину
        """
        # Спочатку перевіряємо, чи заголовок містить відомий магазин
        for shop in self.known_shops:
            if shop.lower() in title.lower():
                return shop
        
        # Шукаємо серед текстів
        for text in texts:
            for shop in self.known_shops:
                if shop.lower() in text.lower():
                    return shop
        
        # Шукаємо розділений дефісом текст
        if " - " in title:
            shop_part = title.split(" - ")[0]
            return shop_part
            
        # Шукаємо тексти з "Geschäft"
        for text in texts:
            if "Geschäft" in text:
                parts = text.split("Geschäft")
                if len(parts) > 1:
                    return parts[1].strip().rstrip(',.:;')
                    
        # Якщо нічого не знайдено, повертаємо перші 2-3 слова заголовка
        words = title.split()
        if len(words) >= 3:
            return " ".join(words[:2])
        elif len(words) > 0:
            return words[0]
        
        return "Unknown Shop"
    
    def _get_image_url(self, img_tag, base_url: str) -> str:
        """
        Отримує повний URL зображення з тегу img.
        
        Args:
            img_tag: Тег <img> з BeautifulSoup
            base_url: Базовий URL сторінки для відносних шляхів
            
        Returns:
            str: Повний URL зображення або порожній рядок
        """
        if not img_tag:
            return ""
            
        # Пробуємо різні атрибути для отримання URL зображення
        for attr in ["src", "data-src", "data-lazy-src", "data-original"]:
            img_src = img_tag.get(attr)
            if img_src:
                # Якщо URL відносний, перетворюємо його на абсолютний
                if not img_src.startswith(("http://", "https://")):
                    img_src = urljoin(base_url, img_src)
                return img_src
                
        # Шукаємо srcset
        srcset = img_tag.get("srcset")
        if srcset:
            # Витягуємо перший URL з srcset
            urls = re.findall(r'([^\s,]+)', srcset)
            if urls:
                url = urls[0]
                if not url.startswith(("http://", "https://")):
                    url = urljoin(base_url, url)
                return url
                
        return ""

    def parse_leaflets(self) -> List[Dict[str, Any]]:
        """
        Парсить всі проспекти з основної сторінки.
        
        Returns:
            List[Dict[str, Any]]: Список словників з даними проспектів
        """
        soup = self.get_page(self.base_url)
        if not soup:
            logger.error("Не вдалося завантажити основну сторінку")
            return []
            
        leaflets = []
        
        try:
            # Зберігаємо повний HTML для аналізу
            with open('full_page.html', 'w', encoding='utf-8') as f:
                f.write(str(soup))
            logger.debug("Збережено повний HTML в full_page.html")
            
            # Знаходимо всі блоки з проспектами (базуючись на вмісті сайту)
            # Спеціальні селектори для сайту prospektmaschine.de
            prospekt_blocks = []
            
            # Шукаємо блоки "Vorschau von dem Prospekt"
            vorschau_blocks = soup.find_all(lambda tag: tag.name and "Vorschau" in tag.text and "Prospekt" in tag.text)
            if vorschau_blocks:
                logger.info(f"Знайдено {len(vorschau_blocks)} блоків з текстом 'Vorschau von dem Prospekt'")
                prospekt_blocks.extend(vorschau_blocks)
            
            # Шукаємо всі кнопки "Zeige den Prospekt"
            zeige_buttons = soup.find_all(lambda tag: tag.name and "Zeige den Prospekt" in tag.text)
            if zeige_buttons:
                logger.info(f"Знайдено {len(zeige_buttons)} кнопок 'Zeige den Prospekt'")
                for button in zeige_buttons:
                    parent = button.parent
                    if parent and parent not in prospekt_blocks:
                        prospekt_blocks.append(parent)
            
            # Додатково шукаємо по загальним селекторам
            selectors = [
                "div.item", "article", ".aktuelle-prospekte-item", 
                ".prospekte-block", ".grid-item", ".aktuelle-prospekte .item",
                ".leaflet-preview-container", ".prospekt-container", "article.leaflet",
                "div[class*='leaflet']", "div[class*='prospekt']",
                ".col-md-3", ".col-sm-4"
            ]
            
            for selector in selectors:
                blocks = soup.select(selector)
                if blocks:
                    logger.info(f"Знайдено {len(blocks)} блоків з селектором: {selector}")
                    for block in blocks:
                        if block not in prospekt_blocks:
                            prospekt_blocks.append(block)
            
            # Обробляємо знайдені блоки
            logger.info(f"Загалом знайдено {len(prospekt_blocks)} блоків проспектів для обробки")
            
            for i, block in enumerate(prospekt_blocks):
                try:
                    # Логуємо блок для аналізу
                    logger.debug(f"Обробка блоку {i+1}:\n{block}")
                    
                    # Шукаємо зображення
                    img = block.find("img")
                    img_src = self._get_image_url(img, self.base_url) if img else ""
                    if not img_src:
                        img_src = "https://www.prospektmaschine.de/static/images/default-leaflet.jpg"
                    
                    # Шукаємо всі можливі елементи з текстом
                    texts = [t.strip() for t in block.stripped_strings if t.strip()]
                    
                    # Якщо немає зображення і немає тексту, пропускаємо
                    if not texts:
                        continue
                    
                    # Визначаємо назву проспекту та магазину
                    bold_text = block.find(["b", "strong", "h2", "h3", "h4"])
                    title = bold_text.text.strip() if bold_text else texts[0]
                    
                    # Витягуємо назву магазину з текстів
                    shop_name = self._extract_shop_name(title, texts)
                    
                    # Шукаємо дати - зазвичай це тексти з крапками в форматі дати
                    date_text = ""
                    for text in texts:
                        if text.count('.') >= 2:  # Мінімум одна дата з крапками (дд.мм.рррр або дд.мм)
                            date_text = text
                            break
                    
                    # Парсимо дати
                    valid_from, valid_to = parse_date_range(date_text)
                    
                    # Створюємо об'єкт проспекту
                    leaflet = Leaflet(
                        title=title,
                        thumbnail=img_src,
                        shop_name=shop_name,
                        valid_from=valid_from,
                        valid_to=valid_to
                    )
                    
                    leaflets.append(leaflet.to_dict())
                    logger.info(f"Додано проспект: {title} ({valid_from} - {valid_to})")
                    
                except Exception as e:
                    logger.error(f"Помилка при обробці блоку проспекту {i+1}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Помилка при парсингу проспектів: {str(e)}")
            
        # Якщо не знайдено жодного проспекту і маємо приклади, використовуємо їх
        if not leaflets:
            logger.warning("Не знайдено жодного проспекту з HTTP-методу.")
            
        return leaflets


class LeafletScraper(Scraper):
    """
    Скрапер проспектів з використанням Playwright
    """
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Отримує сторінку за URL використовуючи Playwright.
        
        Args:
            url (str): URL для запиту
            
        Returns:
            Optional[BeautifulSoup]: Об'єкт BeautifulSoup або None в разі помилки
        """
        # Ця функція повертає BeautifulSoup об'єкт для сумісності з базовим класом
        try:
            html = self.get_page_playwright(url)
            if html:
                return BeautifulSoup(html, 'html.parser')
            return None
        except Exception as e:
            logger.error(f"Помилка при отриманні сторінки {url}: {str(e)}")
            return None
    
    def get_page_playwright(self, url: str) -> Optional[str]:
        """
        Отримує сторінку з використанням Playwright.
        
        Args:
            url (str): URL для запиту
            
        Returns:
            Optional[str]: HTML код сторінки або None в разі помилки
        """
        try:
            with async_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser_context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="de-DE",
                    viewport={"width": 1920, "height": 1080},
                    extra_http_headers={
                        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
                    }
                )
                
                page = browser_context.new_page()
                page.set_default_timeout(60000)  # 60 секунд
                
                logger.info(f"Відкриваю сторінку {url}")
                response = page.goto(url, wait_until="networkidle")
                
                if not response:
                    logger.error("Помилка завантаження сторінки")
                    browser.close()
                    return None
                
                if response.status >= 400:
                    logger.error(f"Помилка HTTP: {response.status}")
                    browser.close()
                    return None
                
                # Додаємо затримку для імітації людської поведінки
                time.sleep(random.uniform(1.0, 2.0))
                
                # Прокручуємо сторінку для завантаження всього контенту
                self._scroll_page(page)
                
                # Зберігаємо HTML для аналізу
                html = page.content()
                with open('debug_playwright.html', 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.debug("Збережено HTML з Playwright в debug_playwright.html")
                
                browser.close()
                return html
                
        except Exception as e:
            logger.error(f"Помилка при використанні Playwright: {str(e)}")
            return None
            
    def _scroll_page(self, page):
        """
        Прокручує сторінку для завантаження динамічного контенту.
        
        Args:
            page: Об'єкт сторінки Playwright
        """
        try:
            # Отримуємо висоту сторінки
            height = page.evaluate("document.body.scrollHeight")
            
            # Прокручуємо поступово з паузами для завантаження контенту
            logger.info("Прокручую сторінку для завантаження контенту")
            
            steps = 10
            for i in range(1, steps + 1):
                # Прокручуємо до певної частини сторінки
                page.evaluate(f"window.scrollTo(0, {height * i / steps})")
                # Випадкова пауза між прокрутками
                time.sleep(random.uniform(0.5, 1.0))
            
            # Переконуємося, що дійшли до кінця
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            
            # Прокручуємо трохи вгору і назад для активації будь-яких ледачих завантажень
            page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.7)")
            time.sleep(0.5)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Помилка при прокручуванні сторінки: {str(e)}")
    
    def parse_leaflets(self) -> List[Dict[str, Any]]:
        """
        Парсить проспекти з використанням Playwright.
        
        Returns:
            List[Dict[str, Any]]: Список словників з даними проспектів
        """
        html = self.get_page_playwright(self.base_url)
        if not html:
            logger.error("Не вдалося отримати сторінку")
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        leaflets = []
        
        try:
            with async_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser_context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="de-DE",
                    viewport={"width": 1920, "height": 1080}
                )
                
                page = browser_context.new_page()
                page.set_default_timeout(60000)  # 60 секунд
                
                # Відкриваємо сторінку з prospektmaschine.de/hypermarkte
                logger.info(f"Відкриваю сторінку {self.base_url}")
                response = page.goto(self.base_url, wait_until="networkidle")
                
                if not response or response.status >= 400:
                    logger.error(f"Помилка при завантаженні сторінки: {response and response.status}")
                    browser.close()
                    return []
                
                # Додаємо затримку і прокручуємо
                time.sleep(random.uniform(2.0, 3.0))
                self._scroll_page(page)
                
                # Шукаємо блоки з проспектами за різними селекторами
                selector_groups = [
                    # Елементи з текстом "Prospekt" та "Vorschau"
                    ["//div[contains(text(), 'Prospekt')]", "//div[contains(text(), 'Vorschau')]"],
                    # Елементи з кнопкою "Zeige den Prospekt"
                    ["//a[contains(text(), 'Zeige den Prospekt')]", "//button[contains(text(), 'Zeige den Prospekt')]"],
                    # Стандартні селектори для grid та списків
                    [".aktuelle-prospekte-item", ".prospekt-item", ".prospektitem"],
                    [".col-sm-4 .item", ".col-md-3 .item", ".grid-item"],
                    ["article.module", "article.item", "div.item"],
                    [".row .prospekt-container", ".leaflet-preview-container"]
                ]
                
                # Пробуємо знайти проспекти за всіма групами селекторів
                for selector_group in selector_groups:
                    for selector in selector_group:
                        try:
                            logger.info(f"Шукаю проспекти за селектором: {selector}")
                            
                            if selector.startswith('//'):
                                # Для XPath
                                items = page.locator(selector)
                            else:
                                # Для CSS селекторів
                                items = page.locator(selector)
                                
                            count = items.count()
                            if count > 0:
                                logger.info(f"Знайдено {count} елементів за селектором {selector}")
                                
                                # Обмежуємо до максимум 10 проспектів для швидкості
                                for i in range(min(count, 10)):
                                    try:
                                        item = items.nth(i)
                                        
                                        # Отримуємо HTML-вміст елемента
                                        item_html = item.evaluate("el => el.outerHTML")
                                        item_soup = BeautifulSoup(item_html, 'html.parser')
                                        
                                        # Логуємо елемент для відлагодження
                                        logger.debug(f"Елемент {i+1}: {item_html[:200]}...")
                                        
                                        # Витягуємо дані з елемента
                                        img = item_soup.find("img")
                                        img_src = self._get_image_url(img, self.base_url) if img else ""
                                        
                                        # Всі текстові елементи
                                        texts = [t.strip() for t in item_soup.stripped_strings if t.strip()]
                                        
                                        if not texts and not img_src:
                                            continue
                                            
                                        # Шукаємо назву магазину і заголовок
                                        shop_name = self._extract_shop_name(item_soup.text, texts)
                                        title = item_soup.text.strip()
                                        
                                        # Шукаємо дати
                                        date_text = ""
                                        for text in texts:
                                            if text.count('.') >= 4:  # Мінімум дві дати (дд.мм.рррр)
                                                date_text = text
                                                break
                                                
                                        valid_from, valid_to = parse_date_range(date_text)
                                        if not valid_from or not valid_to:
                                            # Шукаємо дати у форматі ДД.ММ.РРРР в усіх текстах
                                            date_match = re.findall(r'\d{2}\.\d{2}\.\d{4}', ' '.join(texts))
                                            if len(date_match) >= 2:
                                                # Перша дата - початок, друга - кінець
                                                try:
                                                    date_from = datetime.strptime(date_match[0], "%d.%m.%Y")
                                                    date_to = datetime.strptime(date_match[1], "%d.%m.%Y")
                                                    valid_from = date_from.strftime("%Y-%m-%d")
                                                    valid_to = date_to.strftime("%Y-%m-%d")
                                                except Exception as e:
                                                    logger.error(f"Помилка при парсингу дат: {str(e)}")
                                                    valid_from = datetime.now().strftime("%Y-%m-%d")
                                                    valid_to = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                                            else:
                                                # Якщо не знайшли дати, використовуємо поточну і +7 днів
                                                valid_from = datetime.now().strftime("%Y-%m-%d")
                                                valid_to = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                                                
                                        # Створюємо об'єкт проспекту
                                        leaflet = Leaflet(
                                            title=title,
                                            thumbnail=img_src or "https://example.com/default.jpg",
                                            shop_name=shop_name,
                                            valid_from=valid_from,
                                            valid_to=valid_to
                                        )
                                        
                                        # Додаємо до списку
                                        leaflet_dict = leaflet.to_dict()
                                        if leaflet_dict not in leaflets:  # Уникаємо дублікатів
                                            leaflets.append(leaflet_dict)
                                            logger.info(f"Додано проспект: {title} ({valid_from} - {valid_to})")
                                        
                                    except Exception as e:
                                        logger.error(f"Помилка при обробці елемента {i+1}: {str(e)}")
                                        continue
                                        
                            # Якщо знайшли хоч щось, можемо перервати пошук
                            if count > 0 and leaflets:
                                break
                                
                        except Exception as e:
                            logger.error(f"Помилка при використанні селектора {selector}: {str(e)}")
                            continue
                            
                    # Якщо знайшли хоч щось, можемо перервати пошук по групах
                    if leaflets:
                        break
                
                # Якщо не знайдено жодного проспекту за селекторами, спробуємо знайти за зображеннями
                if not leaflets:
                    logger.info("Не знайдено проспектів за селекторами, шукаю за зображеннями")
                    
                    # Шукаємо всі зображення на сторінці
                    images = page.locator("img")
                    count = images.count()
                    logger.info(f"Знайдено {count} зображень на сторінці")
                    
                    suitable_images = []
                    
                    # Перевіряємо кожне зображення
                    for i in range(count):
                        try:
                            img = images.nth(i)
                            
                            # Перевіряємо розмір і видимість зображення
                            is_visible = img.is_visible()
                            if not is_visible:
                                continue
                                
                            # Отримуємо атрибути зображення
                            src = img.get_attribute("src") or ""
                            alt = img.get_attribute("alt") or ""
                            
                            # Перевіряємо, чи це може бути зображення проспекту
                            if not src:
                                continue
                                
                            # Перевіряємо ключові слова в атрибутах
                            keywords = ["prospekt", "leaflet", "flyer", "katalog", "angebot", "aktion"]
                            if any(keyword in src.lower() or keyword in alt.lower() for keyword in keywords):
                                suitable_images.append({
                                    "src": src,
                                    "alt": alt,
                                    "index": i
                                })
                                logger.debug(f"Підходяще зображення {i}: {src}")
                        except Exception as e:
                            logger.error(f"Помилка при перевірці зображення {i}: {str(e)}")
                            continue
                            
                    logger.info(f"Знайдено {len(suitable_images)} підходящих зображень")
                    
                    # Обробляємо знайдені зображення
                    for img_info in suitable_images[:10]:  # Обмежуємо до 10 зображень
                        try:
                            img_src = self._get_image_url(img_info["img"], self.base_url)
                            shop_name = img_info["alt"] or "Невідомий магазин"
                            
                            # Створюємо проспект
                            leaflet = Leaflet(
                                title=f"Проспект {shop_name}",
                                thumbnail=img_src,
                                shop_name=shop_name,
                                valid_from=datetime.now().strftime("%Y-%m-%d"),
                                valid_to=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                            )
                            
                            leaflet_dict = leaflet.to_dict()
                            if leaflet_dict not in leaflets:  # Уникаємо дублікатів
                                leaflets.append(leaflet_dict)
                                logger.info(f"Додано проспект з зображення: {shop_name}")
                            
                        except Exception as e:
                            logger.error(f"Помилка при обробці зображення {img_info['index']}: {str(e)}")
                            continue
                
                browser.close()
                
        except Exception as e:
            logger.error(f"Помилка при парсингу проспектів з Playwright: {str(e)}")
        
        if not leaflets:
            logger.warning("Не знайдено жодного проспекту. Рекомендується змінити URL або метод скрапінгу.")
        
        return leaflets
    
    # Метод для отримання тестових даних
    def _get_test_leaflets(self):
        self.logger.info("Завантаження тестових даних...")
        test_leaflets = [
            Leaflet(
                title="Aldi Nord Акції цього тижня",
                thumbnail="https://example.com/aldi.jpg",
                shop_name="Aldi",
                valid_from="2025-03-18",
                valid_to="2025-03-24"
            ),
            Leaflet(
                title="EDEKA Спеціальні пропозиції",
                thumbnail="https://example.com/edeka.jpg",
                shop_name="EDEKA",
                valid_from="2025-03-15",
                valid_to="2025-03-21"
            ),
            Leaflet(
                title="NORMA Новий каталог",
                thumbnail="https://example.com/norma.jpg",
                shop_name="NORMA",
                valid_from="2025-03-17",
                valid_to="2025-03-23"
            ),
            Leaflet(
                title="Lidl Акційні товари",
                thumbnail="https://example.com/lidl.jpg",
                shop_name="Lidl",
                valid_from="2025-03-19",
                valid_to="2025-03-25"
            ),
            Leaflet(
                title="Netto Спеціальні пропозиції",
                thumbnail="https://example.com/netto.jpg",
                shop_name="Netto",
                valid_from="2025-03-16",
                valid_to="2025-03-22"
            )
        ]
        
        self.logger.info(f"Завантажено {len(test_leaflets)} тестових проспектів")
        return [leaflet.to_dict() for leaflet in test_leaflets] 