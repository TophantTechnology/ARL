#  -*- coding:UTF-8 -*-
import base64
from app.config import Config
from app import utils
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)


class FofaClient:
    def __init__(self, email, key, page_size=9999):
        self.email = email
        self.key = key
        self.base_url = Config.FOFA_URL
        self.search_api_url = "/api/v1/search/all"
        self.info_my_api_url = "/api/v1/info/my"
        self.page_size = page_size
        self.param = {}

    def info_my(self):
        param = {
            "email": self.email,
            "key": self.key,
        }
        self.param = param
        data = self._api(self.base_url + self.info_my_api_url)
        return data

    def fofa_search_all(self, query):
        qbase64 = base64.b64encode(query.encode())
        param = {
            "email": self.email,
            "key": self.key,
            "qbase64": qbase64.decode('utf-8'),
            "size": self.page_size
        }

        self.param = param
        data = self._api(self.base_url + self.search_api_url)
        return data

    def _api(self, url):
        data = utils.http_req(url, 'get', params=self.param).json()
        if data.get("error") and data["errmsg"]:
            raise Exception(data["errmsg"])

        return data

    def search_cert(self, cert):
        query = 'cert="{}"'.format(cert)
        data = self.fofa_search_all(query)
        results = data["results"]
        return results


def fetch_ip_bycert(cert, size=9999):
    ip_set = set()
    logger.info("fetch_ip_bycert {}".format(cert))
    try:
        client = FofaClient(Config.FOFA_EMAIL, Config.FOFA_KEY, page_size=size)
        items = client.search_cert(cert)
        for item in items:
            ip_set.add(item[1])
    except Exception as e:
        logger.warn("{} error: {}".format(cert, e))

    return list(ip_set)


def fofa_query(query, page_size=9999):
    try:
        if not Config.FOFA_KEY or not Config.FOFA_KEY:
            return "please set fofa key in config-docker.yaml"

        client = FofaClient(Config.FOFA_EMAIL, Config.FOFA_KEY, page_size=page_size)
        info = client.info_my()
        if info.get("vip_level") == 0:
            return "不支持注册用户"

        # 普通会员，最多只查100条
        if info.get("vip_level") == 1:
            client.page_size = min(page_size, 100)

        data = client.fofa_search_all(query)
        return data

    except Exception as e:
        error_msg = str(e)
        error_msg = error_msg.replace(Config.FOFA_KEY[10:], "***")
        return error_msg


def fofa_query_result(query, page_size=9999):
    try:
        ip_set = set()
        data = fofa_query(query, page_size)

        if isinstance(data, dict):
            if data['error']:
                return data['errmsg']

            for item in data["results"]:
                ip_set.add(item[1])
            return list(ip_set)

        raise Exception(data)
    except Exception as e:
        error_msg = str(e)
        return error_msg