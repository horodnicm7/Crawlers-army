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
from urllib.parse import urlparse

from lib.bot import Bot
from lib.config import Config, InvalidConfig, ConfigNotFound
from lib.product import Product

warnings.filterwarnings('ignore', category=UserWarning, module='bs4')


class Cel(Bot):
    def __init__(self, *args, **kwargs):
        super(Cel, self).__init__(*args, **kwargs)

    def get_old_price(self, soup):
        old_price = soup.find('div', class_='pret_v')

        if old_price:
            old_price = old_price.text
            matches = regex.search(r'[0-9,.]+', old_price, regex.M | regex.I)

            raw_price = matches.group(0).replace('-', '0').replace(',', '.')
            if raw_price.count('.') > 1:
                raw_price = raw_price.replace('.', '', 1)

            return float(raw_price)

        return None

    def get_new_price(self, soup):
        # somehow this class name is different from the one on browser
        new_price = soup.find('div', class_='pret_n')

        if not new_price:
            return None

        new_price = new_price.text

        matches = regex.search(r'[0-9,.]+', new_price, regex.M | regex.I)

        raw_price = matches.group(0).replace('-', '0').replace(',', '.')
        if raw_price.count('.') > 1:
            raw_price = raw_price.replace('.', '', 1)

        new_price = float(raw_price)

        return new_price

    def scrap_deals(self):
        if not self.url:
            return

        agent = self.get_valid_user_agent()
        url_path = urlparse(self._page_template)
        trap_url = url_path.path.format(page=2)
        long_way_passed = False

        while True:
            self.url = self.get_next_page_url()

            if not self.url:
                return

            page = self.download_page(user_agent=agent)
            soup = BeautifulSoup(page, self.parser)

            # check if you passed the last page. Cel.ro doesn't return 404, but the
            # first page and so it makes crawlers to go into an infinite loop
            next_page = soup.find("link", {"rel": "next"})
            if next_page and trap_url in str(next_page) and long_way_passed:
                return

            root = soup.find('div', class_='productlisting')

            if not root:
                break

            soup = BeautifulSoup(str(root), self.parser)

            for product in soup.findAll(class_='product_data productListing-tot'):
                product = str(product)

                soup = BeautifulSoup(product, self.parser)

                identification = soup.find('h2', class_='productTitle')

                try:
                    url = 'https://www.cel.ro' + identification.find('a', href=True)['href']
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
                    item.display()

            long_way_passed = True
            sleep(self.timeout)


def main():
    try:
        config = Config(__file__[:-3] + '_config.yaml')
    except (ConfigNotFound, InvalidConfig) as e:
        print(str(e))

    options = {
        'url': 'https://www.cel.ro/',
        'timeout': config.get('timeout', 0.75),
        'retry_timeout': config.get('retry-timeout', 0.75),
        'max_page_number': config.get('max-page-number', 100),
        'debug': config.get('debug', False)
    }

    for category in config['page-template']:
        options['page_template'] = category['url']
        options['filters'] = category.get('filters')

        cel = Cel(**options)
        cel.scrap_deals()


main()
