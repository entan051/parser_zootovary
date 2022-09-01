from html.parser import HTMLParser
import os
import json
import time
import random
import logging
import requests

from bs4 import BeautifulSoup


class Config:
    def __init__(self):
        with open("default.json", "r") as default_config_file:
            self.settings = json.load(default_config_file)
        
        with open("config.json", "r") as config_file:
            self.settings.update(json.load(config_file))        

    def get(self):
        if self.settings["delay_range_s"] == "0":
            self.settings["delay_range_s"] = None
        else:
            self.settings["delay_range_s"] = map(
                int(), 
                self.settings["output_directory"].split("-")
            )

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
        file_path = os.path.join(self.prepare_dir(dir_name), 'log_file.log') 
        self.setting()

        self.logger.addHandler(logging.FileHandler(file_path))

        return self.logger


class WriteCSV:
    pass


class HandlerHTML:
    def __init__(self, data):
        self.processed_html = BeautifulSoup(data["response"].text, "html.parser")

    def handler_categorie(self):
        pass

    def handler_subcategorie(self):
        pass

    def handler_product(self):
        pass
        


class Parser(Config, Logger, WriteCSV):
    def __init__(self):
        self.settings = self.get()
        self.logger = self.launch(self.settings["logs_dir"])
        self.session = requests.Session()
        self.req_timestamp = time.time()
        self.max_retries = self.settings["max_retries"]
        
        if self.settings["delay_range_s"]:
            self.delay_min_s = self.settings["delay_range_s"][0]
            self.delay_max_s = self.settings["delay_range_s"][1]
        else:
            self.delay_min_s = 0
            self.delay_max_s = 0


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

            if r.status_code.startswith(('4', '5')):
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
        "собаки": "sobak",
        "кошки": "koshek",
        "птицы": "ptits",
        "грызуны": "gryzunov",
        "рыбы": "ryb",
        "рептилии": "reptiliy",
        "хорьки": "khorkov",
    }

    DEFAULT_CATEGORIES = [
        "собаки",
        "кошки",
        "птицы",
        "грызуны",
        "рыбы",
        "рептилии",
        "хорьки",
    ]

    DEFAULT_HEADERS = {
        "accept": 'text/html,application/xhtml+xml,application/xml;\
                q=0.9,image/avif,image/webp,image/apng,*/*;\
                q=0.8,application/signed-exchange;v=b3;q=0.9',
        "accept-encoding": 'gzip, deflate, br',
        "accept-language": 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        "cache-control": 'max-age=0',
        "sec-ch-ua": '"Google Chrome";v="105", \
                    "Not)A;Brand";v="8",\
                    "Chromium";v="105"',
        "sec-ch-ua-mobile": '?0',
        "sec-ch-ua-platform": '"Linux"',
        "sec-fetch-dest": 'document',
        "sec-fetch-mode": 'navigate',
        "sec-fetch-site": 'same-origin',
        "sec-fetch-user": '?1',
        "upgrade-insecure-requests": '1',
        "user-agent": 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36\
                     (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36',
    }

    def __init__(self):
        if not self.setting["categories"]:
            self.categories = self.DEFAULT_CATEGORIES
        else:
            self.categories = self.setting["categories"]
        
        self.headers = {}
        for header in self.setting["headers"]:
            if header in self.DEFAULT_HEADERS:
                self.headers[header] = self.DEFAULT_HEADERS[header]

    def launch(self):
        self.get_categotie()

    def get_categotie(self):
        for categorie in self.categories:
            self.do_request({
                "url": f"https://zootovary.ru/catalog/tovary-i-korma-dlya-{categorie}/",
                "headers": self.headers,
                "handler": self.get_subcategotie,
                "args": {"categorie": categorie}
            })

    def get_subcategotie(self, data):
        for subcategorie in HTMLParser(data).handler_categorie():
            pass

    def get_product(self, data):
        for product in HTMLParser(data).handler_subcategorie():
            pass


if __name__ == "__main__":
    parser = Zoo()
