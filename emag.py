"""
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

warnings.filterwarnings('ignore', category=UserWarning, module='bs4')


class Emag(Bot):
    def __init__(self, *args, **kwargs):
        super(Emag, self).__init__(*args, **kwargs)

    @staticmethod
    def display_product(name, old_price, new_price, discount, url=''):
        print(name)
        print('Old price: {}\tNew price: {}\nDiscount: {}%'.format(old_price, new_price, discount))
        print('Url: {}\n'.format(url))

    @staticmethod
    def get_old_price(soup):
        old_price = str(soup.find('p', class_='product-old-price'))
        matches = regex.search(r'[0-9]*[,.]{1}[0-9]*', old_price, regex.M | regex.I)
        # maybe it's not a discount
        if matches:
            return float(matches.group(0).replace(',', '').replace('.', '').replace('-', '0'))

        return None

    @staticmethod
    def get_new_price(soup):
        new_price = str(soup.find('p', class_='product-new-price'))
        matches = regex.search(r'[0-9]*[,.]{1}[0-9]*', new_price, regex.M | regex.I)
        # if price is > 1000
        if matches:
            new_price = float(matches.group(0).replace(',', '').replace('.', '').replace('-', '0'))
        else:
            matches = regex.search(r'[0-9]+', new_price, regex.M | regex.I)
            new_price = float(matches.group(0).replace('-', '0'))

        return new_price

    def scrap_deals(self):
        parser = 'html.parser'

        while True:
            self.url = self.get_next_page_url()

            if not self.url:
                return

            agent = self.get_valid_user_agent()
            page = self.download_page(user_agent=agent)

            soup = BeautifulSoup(page, parser)
            root = str(soup.find('div', id='card_grid'))

            soup = BeautifulSoup(root, parser)

            for product in soup.findAll(class_='card-item js-product-data'):
                product = str(product)

                soup = BeautifulSoup(product, parser)

                identification = soup.find('h2', class_='card-body product-title-zone')

                try:
                    url = identification.find('a', href=True)['href']
                except KeyError:
                    url = None

                name_info = str(identification.text).strip()
                old_price = Emag.get_old_price(soup)
                new_price = Emag.get_new_price(soup)

                discount = 0
                if isinstance(old_price, float) and isinstance(new_price, float):
                    discount = self.get_discount(old_price, new_price)

                if not old_price:
                    old_price = new_price

                Emag.display_product(name_info, old_price, new_price, discount, url)

            sleep(self.timeout)


def main():
    try:
        config = Config(__file__[:-3] + '_config.yaml')
    except (ConfigNotFound, InvalidConfig) as e:
        print(str(e))

    options = {
        'url': 'https://www.emag.ro/',
        'timeout': config.get('timeout', 0.75),
        'retry_timeout': config.get('retry-timeout', 0.75),
        'max_page_number': config.get('max-page-number', 100),
        'page_template': config.get('page-template', 'https://www.emag.ro/tablete/p{page}/c')
    }

    emag = Emag(**options)
    emag.scrap_deals()

main()
