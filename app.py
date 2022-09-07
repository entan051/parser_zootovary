import os
import sys
import csv
import json
import time
import random
import logging
from datetime import datetime
from logging import StreamHandler, Formatter
from unicodedata import category

import requests
from bs4 import BeautifulSoup


class Config: #Класс для работы с конфигурационными файлами.
    def __init__(self):
        with open("default.json", "r") as default_config_file:
            self.settings = json.load(default_config_file)

        with open("config.json", "r") as config_file:
            self.settings.update(json.load(config_file))        

    def get(self):
        if self.settings["delay_range_s"] == "0":
            self.settings["delay_range_s"] = (0, 0)
        else:
            self.settings["delay_range_s"] = tuple(map(
                int, 
                self.settings["delay_range_s"].split("-")
            ))
        return self.settings


class Logger: #Класс для работы с log файлами и настройки логирования.
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def setting(self, dir_name):
        self.logger.setLevel(logging.CRITICAL)
        self.logger.setLevel(logging.ERROR)
        self.logger.setLevel(logging.DEBUG)
        self.logger.setLevel(logging.INFO)

        file_path = os.path.join(
                self.prepare_dir(dir_name), 
                'log_file.log'
                ) 
        handler = StreamHandler(
                stream=sys.stdout
                )
        handler.setFormatter(
                Formatter(fmt='[%(asctime)s: %(levelname)s] - %(message)s')
                )
        self.logger.addHandler(handler)
        self.logger.addHandler(logging.FileHandler(file_path))

        return self.logger


    def prepare_dir(self, dir_name):
        directory = os.path.dirname(os.path.abspath(__file__))
        directory = os.path.join(directory, dir_name)      
        if not os.path.exists(directory): 
            os.makedirs(directory) 
        
        return dir_name

    def launch(self, dir_name): 
        return self.setting(dir_name)


class WriteCSV: #Класс для работы с csv файлами.
    CSV_HEADERS = [
        "price_datetime",
        "price",
        "price_promo",
        "sku_status",
        "sku_barcode",
        "sku_article",
        "sku_name",
        "sku_category",
        "sku_country",
        "sku_weight_min",
        "sku_volume_min",
        "sku_quantity_min",
        "sku_link",
        "sku_images",
    ]

    def __init__(self, output_dir):
        directory = os.path.dirname(os.path.abspath(__file__))
        directory = os.path.join(directory, output_dir)      
        if not os.path.exists(directory): 
            os.makedirs(directory) 

        csv_categories_path = os.path.join(directory, 'categories.csv')
        csv_categories = open(csv_categories_path, 'w', encoding='utf8')
        self.csv_writer_categories = csv.DictWriter(
                csv_categories, 
                delimiter=';',
                fieldnames=["name", "id", "parent_id"]
                )
        self.csv_writer_categories.writeheader()

        csv_products_path =os.path.join(directory, 'products.csv')
        csv_products = open(csv_products_path, 'w', encoding='utf8')
        self.csv_writer_products = csv.DictWriter(
                csv_products, 
                delimiter=';',
                fieldnames=self.CSV_HEADERS
                )
        self.csv_writer_products.writeheader()
    
    def write_article(self, dict_article):
        self.csv_writer_products.writerow(dict_article)

    def write_id(self, dict_id):
        self.csv_writer_categories.writerow(dict_id)


class HandlerHTML: #Класс для обработки HTML.
    def __init__(self, data):
        self.processed_html = BeautifulSoup(data["response"].text, 
                                            "html.parser")

    def handler_categorie(self):
        categories = []
        
        categories_bs = self.processed_html.find_all(
                "a", 
                class_="catalog-menu-icon"
                )

        for categorie in categories_bs:
            categories.append((categorie.text, categorie["href"]))
            
        return categories


    def handler_subcategorie(self):
        sections = []
        subcategories = self.processed_html.find(
                "ul", 
                class_="catalog-menu-left-1"
                ).find_all("li")

        for subcategorie in subcategories:
            section = [
                    sub.attrs for sub in subcategorie.find_all("a") 
                    if sub.attrs.get("title")]
            section = {
                "section_url": section[0].get("href"),
                "section_name": section[0].get("title")
            }

            sections.append(section)

        return sections

    def handler_section(self):
        products_list = []
        more_page = False
        next_page_url = ""
        products = self.processed_html.find_all(
                "div", 
                class_="catalog-item"
                )

        for product in products:
            product_content = product.find("a", class_="name")
            if product_content:
                product_content = product_content.attrs
                product = {
                    "product_url": product_content.get("href"),
                    "product_name": product_content.get("title")
                }

                products_list.append(product)

        more_page, next_page_url = self.check_next_page()
        return (products_list, more_page, next_page_url)

    def handler_product(self):
        price_datetime = datetime.now()
        sku_category = self.processed_html.find(
                "ul", 
                class_="breadcrumb-navigation"
                )
        if sku_category:
            sku_category = sku_category.text[20:].replace(
                    " → ", 
                    "|"
                    )
            sku_name = sku_category.split("|")[-1] 
        else:
            sku_category = None

        articles = self.processed_html.find_all(
                "tr", 
                class_="b-catalog-element-offer"
                )
        photos = self.processed_html.find_all(
                "div", 
                class_="catalog-element-small-picture"
                ) 
        sku_country = self.processed_html.find(
                "div", 
                class_="catalog-element-offer-left"
                ).find("p")
        if sku_country:
            sku_country = sku_country.text.split(": ")[-1]

        sku_images = []
        for photo in photos:
            sku_image = photo.find("a")
            if not sku_image:
                sku_image = photo.find("img").attrs.get("src")
            else:
                sku_image = sku_image.attrs.get("href")
            
            sku_images.append(sku_image)

        articles_list = []
        for article in articles:
            sku_weight_min = ""
            sku_volume_min = ""
            sku_quantity_min = ""
            sku_status = 1

            tr = article.find_all("td")
            if len(tr) < 5:
                continue

            sku_article = tr[0].find_all("b")
            if sku_article:
                sku_article = sku_article[-1].text
            
            sku_barcode = tr[1].find_all("b")
            if sku_barcode:
                sku_barcode = sku_barcode[-1].text
            
            size = tr[2].find_all("b")
            if size:
                size = size[-1].text
                
            if size.endswith("л"):
                sku_volume_min = size[:-1]
            elif size.endswith("кг"):
                sku_weight_min = size[:-2]
            elif size.endswith("г"):
                sku_weight_min = size[:-1]
            elif size.endswith("шт"):
                sku_quantity_min = size[:-2]


            if tr[4].find("s"):
                price = tr[4].find("s")
                if price:
                    price = int(price.text.replace("р", "").replace(" ", ""))
                
                price_promo = tr[4].find("span")
                if price_promo:
                    price_promo = int(price_promo.text.replace("р", "").replace(" ", ""))
            else:
                price = tr[4].find("span")
                if price:
                    price = int(price.text.replace("р", "").replace(" ", ""))
                price_promo = ""

            if tr[-1].find("catalog-item-no-stock"):
                sku_status = 0
        
            articles_list.append({
                "price_datetime": price_datetime,
                "price": price,
                "price_promo": price_promo,
                "sku_status": sku_status,
                "sku_barcode": sku_barcode,
                "sku_article": sku_article,
                "sku_name": sku_name,
                "sku_category": sku_category,
                "sku_country": sku_country,
                "sku_weight_min": sku_weight_min,
                "sku_volume_min": sku_volume_min,
                "sku_quantity_min": sku_quantity_min,
                "sku_images": sku_images,            
                })
 
        return articles_list
        
    def check_next_page(self):
        more_page = False
        next_page = None
        next_page_url = ""
        navigation = self.processed_html.find(
                "div", 
                class_="navigation"
                )

        if navigation:
            current_page = int(navigation.find(
                    "span", 
                    class_="navigation-current"
                    ).text)
            if navigation.find_all("a")[-1].text == "»":
                last_page = int(navigation.find_all("a")[-2].text)
            else:
                last_page = int(navigation.find_all("a")[-1].text)

            if last_page > current_page:
                more_page = True
                next_page = current_page + 1
            else:
                more_page = False
                next_page = 0

        else:
            return (more_page, next_page_url)

        for page in navigation.find_all("a"):
            if page.text == "«":
                continue
            if int(page.text) == next_page:
                next_page_url = page["href"]
                break
        
        return (more_page, next_page_url)


class Parser: #Родительские класс для создания необходимых экземпляров классов и настройки правил запросов.
    def __init__(self):
        self.settings = Config().get()
        self.logger = Logger().launch(self.settings["logs_dir"])
        self.csv_writer = WriteCSV(self.settings["output_directory"])
        self.session = requests.Session()

        self.req_timestamp = time.time()
        self.max_retries = self.settings["max_retries"]
        self.delay_min_s = self.settings["delay_range_s"][0]
        self.delay_max_s = self.settings["delay_range_s"][1]
        self.counter_id = 0

    def do_request(self, args):    
        url = args.get("url")
        headers = args.get("headers")
        handler = args.get("handler")
        arg = args.get("args")
        
        while self.max_retries>0:
            now_timestamp = time.time()-self.req_timestamp
            if now_timestamp < self.delay_min_s:
                time.sleep(
                    random.uniform(
                        self.delay_min_s-now_timestamp, 
                        self.delay_max_s
                    )
                )

            r = self.session.get(
                url,
                headers=headers,
            )

            if str(r.status_code) not in ["200"]:
                self.logger.warning(f'Статус код - {r.status_code}. Проблемы с запросом по адресу - {url}.')
                self.max_retries -= 1
                continue
            else:
                break

        while self.settings["restart"]["restart_count"] >= 0: 
            try:
                handler({
                    "response": r,
                    "args": arg,
                })
                break
            except Exception as exp:
                self.logger.critical(exp, exc_info=True)
                self.settings["restart"]["restart_count"] -= 1
                time.sleep(self.settings["restart"]["interval_m"]*60)


class Zoo(Parser): # Класс-парсер сайта
    DEFAULT_HEADERS = {
        "accept": 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        "accept-encoding": 'gzip, deflate, br',
        "accept-language": 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        "cache-control": 'max-age=0',
        "sec-ch-ua": '"Google Chrome";v="105", "Not)A;Brand";v="8", "Chromium";v="105"',
        "sec-ch-ua-mobile": '?0',
        "sec-ch-ua-platform": '"Linux"',
        "sec-fetch-dest": 'document',
        "sec-fetch-mode": 'navigate',
        "sec-fetch-site": 'same-origin',
        "sec-fetch-user": '?1',
        "upgrade-insecure-requests": '1',
        "user-agent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
    }

    def launch(self):
        self.headers = {}
        for header in self.settings["headers"]:
            if header in self.DEFAULT_HEADERS:
                self.headers[header] = self.DEFAULT_HEADERS[header]

        self.logger.info("Запуск парсера...")
        start_time = time.time()
        self.do_request({
            "url": f"https://zootovary.ru/",
            "headers": self.headers,
            "handler": self.get_categotie,
            "args": {}
        })
        self.logger.info(f"Парсер закончил работу. Время выполнения: {time.time() - start_time}")

    def get_categotie(self, data):
        categories = HandlerHTML(data).handler_categorie()
        for categorie in categories:
            categorie, url = categorie
            if categorie not in self.settings["categories"] and self.settings["categories"]:
                continue

            self.logger.info(f"Обработки категории \"{categorie}\".")
            start_time = time.time()
            
            self.do_request({
                "url": f"https://zootovary.ru{url}",
                "headers": self.headers,
                "handler": self.get_subcategotie,
                "args": {"categorie": categorie}
            })

            self.logger.info(f"Категория \"{categorie}\" обработана. Время выполнения: {time.time() - start_time}")

    def get_subcategotie(self, data):
        self.counter_id += 1
        parent_id = self.counter_id
        self.csv_writer.write_id({
            "name": data["args"]["categorie"],
            "id": parent_id
        })       
        for section in HandlerHTML(data).handler_subcategorie():
            self.logger.info(f"Обработка раздела \"{section['section_name']}\".")
            start_time = time.time()
            section.update(data["args"])
            
            self.counter_id += 1
            self.csv_writer.write_id({
                "name": section["section_name"],
                "parent_id": parent_id,
                "id": self.counter_id
            })

            section['section_url'] = f"https://zootovary.ru{section['section_url']}"
            self.do_request({
                "url": section['section_url'],
                "headers": self.headers,
                "handler": self.get_section,
                "args": section
            })
            self.logger.info(f"Раздел \"{section['section_name']}\" обработан. Время выполнения: {time.time() - start_time}")

    def get_section(self, data):
        products, status, next_page_url = HandlerHTML(data).handler_section()
        for product in products:
            self.logger.info(f"Обработка продукта \"{product['product_name']}\".")

            product.update(data["args"])

            self.do_request({
                "url": f"https://zootovary.ru{product['product_url']}",
                "headers": self.headers,
                "handler": self.get_product,
                "args": product
            })
            
        if status:
            self.do_request({
                "url": f"https://zootovary.ru{next_page_url}",
                "headers": self.headers,
                "handler": self.get_section,
                "args": data["args"]
            })

    def get_product(self, data):
        for article in HandlerHTML(data).handler_product():
            article.update({
                "sku_link": data["args"]['product_url'],
                })
            self.csv_writer.write_article(article)
            

if __name__ == "__main__":
    parser = Zoo().launch()

