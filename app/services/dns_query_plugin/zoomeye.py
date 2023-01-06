import json
import time

from app.services.dns_query import DNSQueryBase
from app import utils


class Query(DNSQueryBase):
    def __init__(self):
        super(Query, self).__init__()
        self.source_name = "zoomeye"
        self.api_url = "https://api.zoomeye.org/domain/search"
        self.api_key = None
        self.max_page = 20

    def init_key(self, api_key=None, max_page=20):
        self.api_key = api_key
        self.max_page = max_page

    def sub_domains(self, target):
        param = {
            "q": target,
            "page": 1,
            "type": "1",
        }

        headers = {
            "API-KEY": self.api_key
        }

        results = []

        curr_page = 1
        while True:
            self.logger.debug("zoomeye target:{} curr_page:{}".format(target, curr_page))
            param["page"] = curr_page
            conn = utils.http_req(self.api_url, 'get', params=param, headers=headers, timeout=(30.1, 50.1))
            data = conn.json()

            if conn.status_code != 200:
                self.logger.error("zoomeye query error:{}".format(json.dumps(data, ensure_ascii=False)))
                break

            items = data["list"]
            if not items:
                break

            for item in items:
                name = item["name"]
                if name.endswith("." + target):
                    results.append(name)

            self.logger.debug(
                "zoomeye target:{} curr_page:{} total:{} curr_size:{}".format(
                    target, curr_page, data["total"], len(items)))

            # zoomeye 是每页返回30条数据
            if len(items) < 30:
                break

            # 请求太多啦，稍后再试试
            time.sleep(2)
            curr_page += 1

            if curr_page > self.max_page:
                break

        return list(set(results))

