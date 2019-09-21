import re
import urllib.request

from bs4 import BeautifulSoup
from urllib import robotparser
from urllib.error import URLError, HTTPError, ContentTooShortError
from time import sleep

from lib.singleton import Singleton


class Bot(object, metaclass=Singleton):
    _retry_timeout = 0

    __soup = None
    __url = ''

    def __init__(self, url='', retry_timeout=1):
        self.set_url(url)
        self._retry_timeout = retry_timeout
        self.bs_class = BeautifulSoup

    def set_url(self, url):
        """
        :param url: url to scrap
        :return: None
        """
        self.__url = url

        if self.__soup:
            del self.__soup

        self.__soup = self.BeautifulSoup(self.__url, 'html.parser')

    def get_valid_user_agent(self):
        """
        Tries to get a valid user agent in maximum 10 attempts.
        :return: 'default-agent' if no valid agent is found or one of the form 'Scrappy1111111'
        """
        # init the robots.txt parser
        parser = robotparser.RobotFileParser()
        parser.set_url(self.__url + '/robots.txt')
        parser.read()

        # trying to get a valid agent name in less than 10 attempts
        user_agent = 'Scrappy'
        no_hops = 0
        while not parser.can_fetch(user_agent, self.__url):
            if user_agent[-1].isdigit():
                user_agent = user_agent[:-1] + str(int(user_agent[-1]) + 1)
            else:
                user_agent = user_agent + '1'

            no_hops += 1
            # error in finding a valid name
            if no_hops > 9:
                return 'default-agent'

        return user_agent

    def download_page(self, url, user_agent, debug=False):
        """
        Downloads the webpage located at url. Tries 10 times to download if the
        page exists (the error code is not in [500, 600) )
        :param url: url to download
        :param user_agent: user agent name
        :param debug: flag to print debug messages or not
        :return:
        """
        if debug:
            print('[DEBUG] Downloading: [' + url + '] ... ')
        page = None
        req = urllib.request.Request(url)
        req.add_header('User-agent', user_agent)

        for i in range(10):
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
        content = self.__soup.find(tag, cls)

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

    def scrap_deals(self, debug=False, timeout=0.75, retry_timeout=0.75, max_page_number=100):
        """
        This method should be overwritten by every child class of this one.
        :param debug: whether to print debug messages or not
        :param timeout: timeout between 2 consecutive requests when scrapping multiple pages
        :param retry_timeout: timeout between 2 consecutive GET requests on same page
        :param max_page_number: maximum page number to scrap
        :return:
        """
        pass
