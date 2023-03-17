import base64
import json
import time
import re
from app.services.dns_query import DNSQueryBase
from app import utils


'''
这个源好像不提供域名查询了，先这样吧。
'''


class Query(DNSQueryBase):
    def __init__(self):
        super(Query, self).__init__()
        self.source_name = "threatminer"
        self.api_url = "https://api.threatminer.org/"

    def sub_domains(self, target):
        url = "{}/v2/domain.php".format(self.api_url)

        # 文档 https://www.threatminer.org/api.php
        param = {
            "rt": "5",
            "q": target
        }
        conn = utils.http_req(url, 'get', params=param, timeout=(30.1, 50.1))
        if conn.status_code == 404 or conn.status_code == 500:
            return []

        data = conn.json()
        if data["status_code"] != "200":
            status_message = data["status_message"]
            self.logger.error(f"{self.source_name} error: {status_message}")
            return []

        items = conn.json()["results"]
        results = []
        for item in items:
            if item.endswith("." + target):
                results.append(item)

        return list(set(results))

