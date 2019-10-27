import random
import re
import urllib.request

from bs4 import BeautifulSoup
from urllib import robotparser
from urllib.error import URLError, HTTPError, ContentTooShortError
from time import sleep

from lib.product import Product
from lib.proxy import RotatingProxyServer


class Bot(object):
    _retry_timeout = 0
    _max_page_number = 100
    _debug = False
    _page_number = 0
    _soup = None
    _url = ''
    _filters = {}
    _sleep_flexibility = 3
    _proxy_fallback = False

    _page_template = ''

    def __init__(self, url='', retry_timeout=1, timeout=0.75, max_page_number=100, debug=False, page_template='',
                 filters=None, sort=None, sleep_flexibility=3, proxy_fallback=False):
        """
        :param url: base url
        :param retry_timeout: time to sleep between 2 consecutive requests on the same page
        :param timeout: time to sleep between 2 consecutive requests for different pages
        :param max_page_number: maximum page number to scrap
        :param debug: whether to display additional info on the process
        :param page_template: starting page template to built urls
        :param filters: filters to consider when displaying a product
        :param sort: sort criterias before displaying products
        """
        self._url = url
        self._retry_timeout = retry_timeout
        self._max_page_number = max_page_number
        self._debug = debug
        self._timeout = timeout
        self._filters = filters
        self._sort = sort
        self._page_template = page_template
        self._sleep_flexibility = sleep_flexibility
        self._proxy_fallback = proxy_fallback

        self.parser = 'html.parser'
        self.crawled_fpage = False
        self.first_page = ''

    @property
    def sort(self):
        return self._sort

    @property
    def timeout(self):
        return self._timeout

    @property
    def max_page_number(self):
        return self._max_page_number

    @property
    def debug(self):
        return self._debug

    @property
    def retry_timeout(self):
        return self._retry_timeout

    @property
    def filters(self):
        return self._filters

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value

    def set_url(self, url):
        """
        :param url: url to scrap
        :return: None
        """
        self._url = url
        if self._soup:
            del self._soup
        self._soup = BeautifulSoup(self._url, 'html.parser')

    def get_next_page_url(self):
        self._page_number += 1

        if self.debug:
            print('[DEBUG] Preparing page {}'.format(self._page_number))

        if self._page_number > self._max_page_number:
            return None

        return self._page_template.format(page=self._page_number)

    def get_valid_user_agent(self, max_no_hops=10):
        """
        Tries to get a valid user agent in maximum 10 attempts.
        :param max_no_hops: maximum number of tries to get page content
        :return: 'default-agent' if no valid agent is found or one of the form 'Scrappy1111111'
        """
        # init the robots.txt parser
        parser = robotparser.RobotFileParser()
        parser.set_url(self._url + '/robots.txt')
        parser.read()

        # trying to get a valid agent name in less than 10 attempts
        user_agent = 'Scrappy'
        no_hops = 0
        while not parser.can_fetch(user_agent, self._url):
            if user_agent[-1].isdigit():
                user_agent = user_agent[:-1] + str(int(user_agent[-1]) + 1)
            else:
                user_agent = user_agent + '1'

            no_hops += 1
            # error in finding a valid name
            if no_hops == max_no_hops:
                return 'default-agent'

        return user_agent

    def download_page(self, url=None, user_agent=None, max_no_hops=10):
        """
        Downloads the webpage located at url. Tries 10 times to download if the
        page exists (the error code is not in [500, 600) )
        :param url: url to download
        :param user_agent: user agent name
        :param debug: flag to print debug messages or not
        :param max_no_hops: maximum number of tries to get page content
        :return:
        """
        if not url:
            url = self._url

        if not user_agent:
            user_agent = self.get_valid_user_agent()

        if self._debug:
            print('[DEBUG] Downloading: [' + url + '] ... ')
        page = None
        req = urllib.request.Request(url)
        req.add_header('User-agent', user_agent)

        for i in range(max_no_hops):
            try:
                response = urllib.request.urlopen(req)
                page = response.read().decode('utf-8')
                break
            except (URLError, HTTPError, ContentTooShortError) as e:
                if hasattr(e, 'code'):
                    if e.code < 500:
                        return None
                sleep(self._retry_timeout)
        return page

    def get_info(self, regex, tag, cls):
        """
        Returns text based on criteria.
        :param regex: regex used to parse data
        :param tag: tag to use (e.g: div, p, etc.)
        :param cls: tag unique identifier
        :return:
        """
        content = self._soup.find(tag, cls)

        if not content:
            return None

        text = re.search(regex, str(content), re.M | re.I)
        return text.group

    @staticmethod
    def get_discount(old_price, new_price):
        """
        Method that computes the discount based on the old and the new price
        :param old_price:
        :param new_price:
        :return:
        """
        return round(100 - (100 * new_price) / old_price, 2)

    def apply_filters(self, product):
        """
        Returns True if this product respects all filters and False otherwise
        :param product: product info
        :type product: Product
        :return: boolean
        """
        if not self.filters:
            return True

        if 'max-price' in self.filters:
            if product.price > self.filters['max-price']:
                return False

        if 'min-price' in self.filters:
            if product.price < self.filters['min-price']:
                return False

        if 'discount' in self.filters:
            if product.discount < self.filters['discount']:
                return False

        if 'brands' in self.filters:
            found = False
            for brand in self.filters['brands']:
                if brand.capitalize() in product.name or brand.upper() in product.name or brand.lower() in product.name:
                    found = True
                    break

            if not found:
                return False

        return True

    def apply_sort_criteria(self, products):
        """
        :param products: list of Products to sort
        :type products: list of Product
        :return: a sorted list of products
        """
        if not self.sort or not isinstance(self.sort, dict):
            return products

        discount_crit = self.sort.get('discount')
        old_price_crit = self.sort.get('old-price')
        new_price_crit = self.sort.get('new-price')
        desc = False

        if discount_crit:
            discount_crit = discount_crit.lower()
            if discount_crit == 'descending':
                desc = True

            products.sort(key=lambda prod: prod.discount, reverse=desc)
            return products

        if old_price_crit:
            old_price_crit = old_price_crit.lower()
            if old_price_crit == 'descending':
                desc = True

            products.sort(key=lambda prod: prod.old_price, reverse=desc)
            return products

        if new_price_crit:
            new_price_crit = new_price_crit.lower()
            if new_price_crit == 'descending':
                desc = True

            products.sort(key=lambda prod: prod.price, reverse=desc)
            return products

        return products

    def is_cheap_trap(self, soup):
        """
        Method used to test loops, because those f***ers can't give a 404 if you exceed the page number
        :param soup: BeautifulSoup instance
        :return:
        """
        # check if you passed the last page. Emag doesn't return 404, but the
        # first page and so it makes crawlers to go into an infinite loop
        cr_page = soup.find("link", {"rel": "canonical"})['href']
        if cr_page:
            if self.crawled_fpage:
                if cr_page == self.first_page:
                    return True
            else:
                self.crawled_fpage, self.first_page = True, cr_page

        return False

    def sleep_between_requests(self):
        sleep(self.timeout + random.randrange(self._sleep_flexibility))

    def scrap_deals(self):
        """
        This method should be overwritten by every child class of this one.
        :return:
        """
        pass

    def get_old_price(self, soup):
        """
        This method should be overwritten by every child class of this one.
        :param soup: BeautifulSoup instance
        :return:
        """
        pass

    def get_new_price(self, soup):
        """
        This method should be overwritten by every child class of this one.
        :param soup: BeautifulSoup instance
        :return:
        """
        pass
