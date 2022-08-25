import base64
import json
import time
import re
from app.services.dns_query import DNSQueryBase
from app import utils


class Query(DNSQueryBase):
    def __init__(self):
        super(Query, self).__init__()
        self.source_name = "threatminer"
        self.api_url = "https://api.threatminer.org/"
        self.api_key = None

    def init_key(self, api_key=None):
        self.api_key = api_key

    def sub_domains(self, target):
        url = "{}/v2/domain.php".format(self.api_url)

        # 文档 https://www.threatminer.org/api.php
        param = {
            "rt": "5",
            "q": target
        }
        conn = utils.http_req(url, 'get', params=param, timeout=(30.1, 50.1))
        if conn.status_code == 404:
            return []

        items = conn.json()["results"]
        results = []
        for item in items:
            if item.endswith("." + target):
                results.append(item)

        return list(set(results))

