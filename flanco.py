"""
    Example of config file with filters:
        debug: False
        page-template:
            - url: 'https://www.emag.ro/tablete/p{page}/c'
              filters:
                  max-price: 3000
                  min-price: 1000
                  brands:
                      - 'apple'
                      - 'samsung'
                  discount: 10

    To install:
        pip install beautifulsoup4
        pip install pyyaml
"""
import os
import random
import re as regex
import shutil
import warnings

from bs4 import BeautifulSoup
from time import sleep

from lib.bot import Bot
from lib.config import Config, InvalidConfig, ConfigNotFound
from lib.product import Product

warnings.filterwarnings('ignore', category=UserWarning, module='bs4')


class Flanco(Bot):
    def __init__(self, *args, **kwargs):
        super(Flanco, self).__init__(*args, **kwargs)

    def get_old_price(self, soup):
        old_price = soup.find('div', class_='produs-oldprice-old')

        if old_price:
            old_price = old_price.text
            matches = regex.search(r'[0-9]*[,.]{1}[0-9]*[,]*[0-9]*', old_price, regex.M | regex.I)

            raw_price = matches.group(0).replace('-', '0').replace(',', '.')
            if raw_price.count('.') > 1:
                raw_price = raw_price.replace('.', '', 1)
            return float(raw_price)

        return None

    def get_new_price(self, soup):
        # somehow this class name is different from the one on browser
        new_price = soup.find('div', class_='produs-price')

        if not new_price:
            new_price = soup.find('p', class_='produs-price')

            if not new_price:
                return None

        new_price = str(new_price)

        new_soup = BeautifulSoup(new_price, self.parser)
        new_price = new_soup.find('span', class_='price').text

        matches = regex.search(r'[0-9]*[,.]{1}[0-9]*[,]*[0-9]*', new_price, regex.M | regex.I)

        raw_price = matches.group(0).replace('-', '0').replace(',', '.')
        if raw_price.count('.') > 1:
            raw_price = raw_price.replace('.', '', 1)

        new_price = float(raw_price)

        return new_price

    def scrap_deals(self, file=None, max_no_hops=10):
        if not self.url:
            return

        agent = self.get_valid_user_agent()
        has_sort, products = self.sort is not None, []

        while True:
            self.url = self.get_next_page_url()

            if not self.url:
                break

            page = self.download_page(user_agent=agent, max_no_hops=max_no_hops)
            soup = BeautifulSoup(page, self.parser)

            root = soup.find('div', id='products-wrapper')

            if not root:
                if self.debug:
                    print('[DEBUG] No root products wrapper!')
                break

            soup = BeautifulSoup(str(root), self.parser)

            for product in soup.findAll(class_='produs'):
                product = str(product)

                soup = BeautifulSoup(product, self.parser)

                identification = soup.find('div', class_='produs-title')

                try:
                    url = identification.find('a', href=True)['href']
                except KeyError:
                    url = None

                name_info = str(identification.text).strip()

                old_price = self.get_old_price(soup)
                new_price = self.get_new_price(soup)

                discount = 0
                if isinstance(old_price, float) and isinstance(new_price, float):
                    discount = self.get_discount(old_price, new_price)

                if not old_price and not new_price:
                    continue

                if not old_price:
                    old_price = new_price

                item = Product(new_price=new_price, old_price=old_price, discount=discount, name=name_info, url=url)
                if self.apply_filters(item):
                    if has_sort:
                        products.append(item)
                    else:
                        item.display(file=file)

            sleep(self.timeout)

        if has_sort:
            products = self.apply_sort_criteria(products)
            for item in products:
                item.display(file=file)


def main():
    try:
        config = Config(__file__[:-3] + '_config.yaml')
    except (ConfigNotFound, InvalidConfig) as e:
        print(str(e))

    options = {
        'url': 'https://www.flanco.ro',
        'timeout': config.get('timeout', 0.75),
        'retry_timeout': config.get('retry-timeout', 0.75),
        'max_page_number': config.get('max-page-number', 100),
        'debug': config.get('debug', False),
        'sleep_flexibility': config.get('sleep-flexibility', 3),
        'proxy_fallback': config.get('fallback-on-proxies', False),
        'max_no_requests': config.get('max-number-of-requests-per-proxy', 0),
        'proxy_timeout': config.get('proxy-check-timeout', 10)
    }

    # clear current directory entries
    if config.get('write-to-files'):
        if os.path.exists('flanco'):
            shutil.rmtree('flanco')
        os.mkdir('flanco', 777)

    for category in config['page-template']:
        options['page_template'] = category['url']
        options['filters'] = category.get('filters')
        options['sort'] = category.get('sort')

        file = None
        if config.get('write-to-files'):
            file = open('flanco//' + category['url'].split('//')[1].split('/')[1] + '.txt', 'w')

        flanco = Flanco(**options)
        flanco.scrap_deals(file=file, max_no_hops=config.get('max-no-hops', 10))

        if file:
            file.close()

        sleep(config['sleep-between-categories'] + random.randrange(config['sleep-flexibility']))
        print("")


main()
