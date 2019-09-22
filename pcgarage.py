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
import re as regex
import warnings

from bs4 import BeautifulSoup
from time import sleep

from lib.bot import Bot
from lib.config import Config, InvalidConfig, ConfigNotFound
from lib.product import Product

warnings.filterwarnings('ignore', category=UserWarning, module='bs4')


class PCGarage(Bot):
    def __init__(self, *args, **kwargs):
        super(PCGarage, self).__init__(*args, **kwargs)

    def get_old_price(self, soup):
        raw_old_price = soup.find('p', class_='pbe-price-old')

        if raw_old_price:
            old_price = str(raw_old_price.text)
            matches = regex.search(r'[0-9,.]*', old_price, regex.M | regex.I)
            # maybe it's not a discount
            if matches:
                price = matches.group(0).replace(',', '.')  # type: str
                fpoint = price.find('.')
                price = price[:fpoint] + price[fpoint + 1:]
                return float(price)

        return None

    def get_new_price(self, soup):
        # this might be buggy in the future
        raw_new_price = str(soup.find('div', class_='pb-price').text)

        if raw_new_price:
            matches = regex.search(r'[0-9,.]+', raw_new_price, regex.M | regex.I)

            if matches:
                price = matches.group(0).replace(',', '.')  # type: str
                if price.count('.') > 1:
                    fpoint = price.find('.')
                    price = price[:fpoint] + price[fpoint + 1:]
                return float(price)

        return None

    def scrap_deals(self):
        if not self.url:
            return

        parser = 'html.parser'
        agent = self.get_valid_user_agent()

        self.url = self.get_next_page_url()

        if not self.url:
            return

        page = self.download_page(user_agent=agent)

        soup = BeautifulSoup(page, parser)
        root = str(soup.find('div', class_='grid-products clearfix product-list-container'))

        soup = BeautifulSoup(root, parser)

        for product in soup.findAll(class_='product-box-container'):
            product = str(product)
            soup = BeautifulSoup(product, parser)

            identification = soup.find('div', class_='pb-name')
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

            if not old_price:
                old_price = new_price

            item = Product(new_price=new_price, old_price=old_price, discount=discount, name=name_info, url=url)
            if self.apply_filters(item):
                item.display()


def main():
    try:
        config = Config(__file__[:-3] + '_config.yaml')
    except (ConfigNotFound, InvalidConfig) as e:
        print(str(e))

    options = {
        'url': 'https://www.pcgarage.ro/',
        'timeout': config.get('timeout', 0.75),
        'retry_timeout': config.get('retry-timeout', 0.75),
        'max_page_number': config.get('max-page-number', 100),
        'debug': config.get('debug', False)
    }

    for category in config['page-template']:
        options['page_template'] = category['url']
        options['filters'] = category.get('filters')

        pcgarage = PCGarage(**options)
        pcgarage.scrap_deals()

main()