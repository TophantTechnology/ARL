import base64
import json
import time

from app.services.dns_query import DNSQueryBase
from app import utils


class Query(DNSQueryBase):
    def __init__(self):
        super(Query, self).__init__()
        self.source_name = "hunter_qax"
        self.api_url = "https://hunter.qianxin.com/openApi/search"
        self.api_key = None
        self.page_size = 10
        self.max_page = 10

    def init_key(self, api_key=None, page_size=10, max_page=5):
        self.api_key = api_key
        self.page_size = page_size
        self.max_page = max_page

    def sub_domains(self, target):
        search = "domain.suffix=\"{}\"".format(target)

        param = {
            "search": base64.urlsafe_b64encode(search.encode("utf-8")),
            "page": 1,
            "page_size": self.page_size,
            "is_web": "1",
            "api-key": self.api_key
        }

        results = []

        curr_page = 1
        while True:
            self.logger.debug("hunter_qax target:{} page_size:{} curr_page:{}".format(target, self.page_size, curr_page))
            param["page"] = curr_page
            data = utils.http_req(self.api_url, 'get', params=param).json()

            if data["code"] != 200 and data["code"] != 40205:
                self.logger.error("hunter_qax query error:{}".format(json.dumps(data, ensure_ascii=False)))
                break

            if data["code"] == 40205:
                self.logger.info(data["message"])

            arr = data["data"]["arr"]
            if arr is None:
                break

            for item in data["data"]["arr"]:
                name = item["domain"]
                if name.endswith("." + target):
                    results.append(name)

            self.logger.debug(
                "hunter_qax target:{} page_size:{} curr_page:{} total:{} curr_size:{}".format(
                    target, self.page_size, curr_page, data["data"]["total"], len(arr)))

            if len(arr) < self.page_size:
                break

            # 请求太多啦，稍后再试试
            time.sleep(2)
            curr_page += 1

            if curr_page > self.max_page:
                break

        return list(set(results))

