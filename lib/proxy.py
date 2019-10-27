from urllib.request import Request, urlopen
from bs4 import BeautifulSoup
import random
from lib.singleton import Singleton


class RotatingProxyServer(object, metaclass=Singleton):
    __proxies = []
    __accepted_country_codes = ['AT', 'BG', 'FR', 'HU', 'MT', 'NL', 'RU', 'UA', 'GB']
    __tries = 0
    current_proxy = None
    max_no_req = 10
    proxy_timeout = 10

    def __init__(self, target_url, debug=False, max_no_requests=10, proxy_timeout=10):
        self.target_url = target_url
        self.debug = debug
        self.max_no_req = max_no_requests
        self.proxy_timeout = proxy_timeout
        self.fetch_list_of_proxies()

    def fetch_list_of_proxies(self):
        proxies_req = Request('https://www.sslproxies.org/')
        proxies_req.add_header('User-Agent', str(random.randrange(100, 20000)))
        proxies_doc = urlopen(proxies_req).read().decode('utf8')

        soup = BeautifulSoup(proxies_doc, 'html.parser')
        proxies_table = soup.find(id='proxylisttable')

        # Save proxies in the list
        for row in proxies_table.tbody.find_all('tr'):
            proxy = row.find_all('td')

            if proxy[2].string in self.__accepted_country_codes:
                self.__proxies.append({
                    'ip': proxy[0].string,
                    'port': proxy[1].string,
                    'country': proxy[2].string
                })

        print(self.__proxies)
        print(len(self.__proxies))

    def __change_proxy(self):
        req = Request(self.target_url)
        while True:
            # get a random proxy server and try it
            index = random.randrange(len(self.__proxies))
            proxy = self.__proxies[index]

            req.set_proxy(proxy['ip'] + ':' + proxy['port'], 'https')

            if self.debug:
                print('[DEBUG] Testing proxy: {}:{}'.format(proxy['ip'], proxy['port']))

            # Make the call
            try:
                data = urlopen(req, timeout=self.proxy_timeout).read().decode('utf8')
                if not data:
                    raise

                if self.debug:
                    print('[DEBUG] Using {}:{} as proxy'.format(proxy['ip'], proxy['port']))
                return proxy
            except Exception:  # If there's an error, delete this proxy and find another one
                del self.__proxies[index]
                if self.debug:
                    print('[DEBUG] Proxy ' + proxy['ip'] + ':' + proxy['port'] + ' deleted.')

    def get_random_proxy(self):
        if not self.__tries % self.max_no_req:
            self.__tries = 0
            self.current_proxy = self.__change_proxy()

        self.__tries += 1
        return self.current_proxy
