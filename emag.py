"""
    To install:
        pip install beautifulsoup4
        pip install pyyaml
"""
import re as regex
import warnings

from time import sleep

from lib.bot import Bot
from lib.config import Config, InvalidConfig, ConfigNotFound

warnings.filterwarnings('ignore', category=UserWarning, module='bs4')


class Emag(Bot):
    def __init__(self, *args, **kwargs):
        super(Emag, self).__init__(*args, **kwargs)

    def scrap_deals(self, debug=False, timeout=0.75, retry_timeout=0.75, max_page_number=100):
        pass


def main():
    try:
        config = Config(__file__[:-3] + '_config.yaml')
    except (ConfigNotFound, InvalidConfig) as e:
        print(str(e))
        return

    timeout = config.get('timeout', 0.75)
    retry_timeout = config.get('retry-timeout', 0.75)
    max_page_number = config.get('max-page-number', 100)

    emag = Emag()


main()
