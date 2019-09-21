import yaml

from lib.singleton import Singleton


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Config(object, metaclass=Singleton):
    def __init__(self, path):
        self.load_config(path)
        self.__config = dict()

    def __getattr__(self, item):
        return self.__config[item]

    def __setitem__(self, key, value):
        self.__config[key] = value

    def get(self, key, fallback=None):
        if key not in self.__config:
            return fallback

    def load_config(self, path):
        config = None
        try:
            with open(path, 'r') as stream:
                try:
                    config = yaml.safe_load(stream)
                except yaml.YAMLError as exc:
                    print('[DEBUG] Error parsing config file')
                    raise InvalidConfig('Config syntax error')
        except FileNotFoundError:
            print('[DEBUG] Config file not found')
            raise ConfigNotFound('Config file not found')

        self.__config = config


class InvalidConfig(Exception):
    pass


class ConfigNotFound(Exception):
    pass
