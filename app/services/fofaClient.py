#  -*- coding:UTF-8 -*-
import base64
from app.config import Config
from app import utils
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


class FofaClient:
    def __init__(self, email, key, page_size = 9999):
        self.email = email
        self.key = key
        self.base_url = "https://fofa.so"
        self.search_api_url = "/api/v1/search/all"
        self.page_size = page_size #终身用户
        self.param = {}

    def fofa_search_all(self, query):
        qbase64 = base64.b64encode(query.encode())
        param = {
            "email": self.email,
            "key": self.key,
            "qbase64": qbase64.decode('utf-8'),
            "size": self.page_size
        }

        self.param = param
        data =  self._api(self.base_url + self.search_api_url)
        return data

    def _api(self, url):
        data =  utils.http_req(url, 'get', params = self.param).json()
        return data


    def search_cert(self, cert):
        query = 'cert="{}"'.format(cert)
        data = self.fofa_search_all(query)
        if data["error"] and data["errmsg"]:
            raise Exception(data["errmsg"])

        results = data["results"]
        return results




def fetch_ip_bycert(cert, size=9999):
    ip_set = set()

    try:
        client = FofaClient(Config.FOFA_EMAIL, Config.FOFA_KEY, page_size=size)
        items = client.search_cert(cert)
        for item in items:
            ip_set.add(item[1])
    except Exception as e:
        logger.warn("{} error: {}".format(cert, e))

    return list(ip_set)

