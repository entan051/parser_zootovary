import os
import re
import csv
import json
import time
import random
import logging
import requests
from datetime import datetime
from bs4 import BeautifulSoup


class Config:
    def __init__(self):
        with open("default.json", "r") as default_config_file:
            self.settings = json.load(default_config_file)
        
        with open("config.json", "r") as config_file:
            self.settings.update(json.load(config_file))        

    def get(self):
        if self.settings["delay_range_s"] == "0":
            self.settings["delay_range_s"] = (0, 0)
        elif not self.settings["delay_range_s"]:
            self.settings["delay_range_s"] = (1, 3)
        else:
            self.settings["delay_range_s"] = tuple(map(
                int, 
                self.settings["delay_range_s"].split("-")
            ))

        return self.settings


class Logger:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def setting(self):
        self.logger.setLevel(logging.DEBUG)
        self.logger.setLevel(logging.INFO)

    def prepare_dir(self, dir_name):
        directory = os.path.dirname(os.path.abspath(__file__))
        directory = os.path.join(directory, dir_name)      
        if not os.path.exists(directory): 
            os.makedirs(directory) 

        return dir_name

    def launch(self, dir_name): 
        file_path = os.path.join(
                self.prepare_dir(dir_name), 
                'log_file.log'
                ) 
        self.setting()
        self.logger.addHandler(logging.FileHandler(file_path))

        return self.logger


class WriteCSV:
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

    def __init__(self):
        csvfile = open('categories.csv', 'w', encoding='utf8')
        self.csv_file = csv.writer(csvfile, delimiter=';')
        self.csv_writer = csv.DictWriter(
                csvfile, 
                fieldnames=self.CSV_HEADERS
                )
        self.csv_writer.writeheader()
    
    def write_article(self, dict_article):
        self.csv_writer.writerow(dict_article)


class HandlerHTML:
    def __init__(self, data):
        self.processed_html = BeautifulSoup(data["response"].text, 
                                            "html.parser")

    def handler_subcategorie(self):
        sections = []
        subcategories = self.processed_html.find(
                "ul", 
                class_="catalog-menu-left-1"
                ).find_all("li")

        for subcategorie in subcategories:
            section_attrs = subcategorie.find("a").attrs
            section = {
                "section_url": section_attrs.get("href"),
            }

            sections.append(section)

        return sections

    def handler_section(self):
        products_list = []
        more_page = False
        next_page_url = ""
        products = self.processed_html.find_all(
                "div", 
                class_="catalog-item catalog-itemlist"
                )

        for product in products:
            product_content = product.find("a", class_="name").attrs
            product = {
                "product_url": product_content.get("href")
            }
            
            products_list.append(product)

        more_page, next_page_url = self.check_next_page()
        return (products_list, more_page, next_page_url)

    def handler_product(self):
        price_datetime = datetime.now()
        sku_category = self.processed_html.find(
                "ul", 
                class_="breadcrumb-navigation"
                ).text[20:].replace(" → ", " | ")
        sku_name = sku_category.split(" | ")[-1] 
        sku_country = self.processed_html.find(
                "div", 
                class_="catalog-element-offer-left"
                ).find("p").text.split(": ")[-1]
        articles = self.processed_html.find_all(
                "tr", 
                class_="b-catalog-element-offer"
                )
        photos = self.processed_html.find_all(
                "div", 
                class_="catalog-element-small-picture"
                ) 

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
            sku_article = tr[0].find_all("b")[-1].text
            sku_barcode = tr[1].find_all("b")[-1].text
            
            size = tr[2].find_all("b")[-1].text
            if size.endswith("л"):
                sku_volume_min = size[:-1]
            elif size.endswith("кг"):
                sku_weight_min = size[:-2]
            elif size.endswith("г"):
                sku_weight_min = size[:-1]
            elif size.endswith("шт"):
                sku_quantity_min = size[:-2]
            else:
                pass #TODO


            if tr[4].find("s"):
                price = tr[4].find("s").text.replace("р", "")
                price_promo = tr[4].find("span").text.replace("р", "")
            else:
                price = tr[4].find("span").text.replace("р", "")
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
        next_page_url = ""
        navigation = self.processed_html.find(
                "div", 
                class_="navigation"
                )

        if navigation:
            if navigation.find_all("a")[-1].text == "»":
                last_page = int(navigation.find_all("a")[-2].text)
            else:
                last_page = int(navigation.find_all("a")[-1].text)
            current_page = int(navigation.find(
                    "span", 
                    class_="navigation-current"
                    ).text)
        
            if last_page > current_page:
                more_page = True
                next_page = current_page + 1
        else:
            return (more_page, next_page_url)

        for page in navigation.find_all("a"):
            if int(page.text) == next_page:
                next_page_url = page["href"]
                break
        
        return (more_page, next_page_url)


class Parser:
    def __init__(self):
        self.settings = Config().get()
        self.logger = Logger().launch(self.settings["logs_dir"])
        self.csv_writer = WriteCSV()
        self.session = requests.Session()
        self.req_timestamp = time.time()
        self.max_retries = self.settings["max_retries"]
        self.delay_min_s = self.settings["delay_range_s"][0]
        self.delay_max_s = self.settings["delay_range_s"][1]

    def do_request(self, args):
        url = args.get("url")
        headers = args.get("headers")
        handler = args.get("handler")
        arg = args.get("args")

        if not handler or not url:
            pass
        
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

            if str(r.status_code).startswith(('4', '5')):
                self.max_retries -= 1
                continue
            else:
                break

        handler({
            "response": r,
            "args": arg,
        })


class Zoo(Parser):
    CATEGORIES = {
        "Собаки": "sobak",
        "Кошки": "koshek",
        "Птицы": "ptits",
        "Грызуны": "gryzunov",
        "Рыбы": "ryb",
        "Рептилии": "reptiliy",
        "Хорьки": "khorkov",
    }

    DEFAULT_CATEGORIES = [
        "Собаки",
        "Кошки",
        "Птицы",
        "Грызуны",
        "Рыбы",
        "Рептилии",
        "Хорьки",
    ]

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
        if not self.settings["categories"]:
            self.categories = self.DEFAULT_CATEGORIES
        else:
            self.categories = self.settings["categories"]
        
        self.headers = {}
        for header in self.settings["headers"]:
            if header in self.DEFAULT_HEADERS:
                self.headers[header] = self.DEFAULT_HEADERS[header]

        self.get_categotie()

    def get_categotie(self):
        for categorie in self.categories:
            self.do_request({
                "url": f"https://zootovary.ru/catalog/tovary-i-korma-dlya-{self.CATEGORIES[categorie]}/",
                "headers": self.headers,
                "handler": self.get_subcategotie,
                "args": {"categorie": categorie}
            })

    def get_subcategotie(self, data):
        for section in HandlerHTML(data).handler_subcategorie():
            section.update(data["args"])
            section['section_url'] = f"https://zootovary.ru{section['section_url']}"

            self.do_request({
                "url": section['section_url'],
                "headers": self.headers,
                "handler": self.get_section,
                "args": section
            })

    def get_section(self, data):
        products, status, next_page_url = HandlerHTML(data).handler_section()
        for product in products:
            product.update(data["args"])
            product['product_url'] = f"https://zootovary.ru{product['product_url']}"

            self.do_request({
                "url": product['product_url'],
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
