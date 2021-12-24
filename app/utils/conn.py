import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests


from app.config import Config

UA = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36"


proxies = {
    'https': "http://127.0.0.1:8080",
    'http': "http://127.0.0.1:8080"
}

SET_PROXY = False


def http_req(url, method='get', **kwargs):
    kwargs.setdefault('verify', False)
    kwargs.setdefault('timeout', (10.1, 30.1))
    kwargs.setdefault('allow_redirects', False)

    headers = kwargs.get("headers", {})
    headers.setdefault("User-Agent", UA)
    # 不允许缓存
    headers.setdefault("Cache-Control", "max-age=0")

    kwargs["headers"] = headers

    if Config.PROXY_URL:
        proxies['https'] = Config.PROXY_URL
        proxies['http'] = Config.PROXY_URL
        kwargs["proxies"] = proxies

    conn = getattr(requests, method)(url, **kwargs)

    return conn


from pymongo import MongoClient


class ConnMongo(object):
    def __new__(self):
        if not hasattr(self, 'instance'):
            self.instance = super(ConnMongo, self).__new__(self)
            self.instance.conn = MongoClient(Config.MONGO_URL)
        return self.instance


def conn_db(collection, db_name = None):
    conn = ConnMongo().conn
    if db_name:
        return conn[db_name][collection]

    else:
        return conn[Config.MONGO_DB][collection]