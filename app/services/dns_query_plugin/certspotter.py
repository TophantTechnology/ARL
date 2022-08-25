import json
import time
from app.services.dns_query import DNSQueryBase
from app import utils


class Query(DNSQueryBase):
    def __init__(self):
        super(Query, self).__init__()
        self.source_name = "certspotter"
        self.api_url = "https://api.certspotter.com/v1/issuances"
        self.after_id = 0
        self.max_page = 5

    def init_key(self, after_id=0, max_page=5):
        self.after_id = after_id
        self.max_page = max_page

    def sub_domains(self, target):
        max_page = self.max_page
        results = set()
        next_id = self.after_id
        for i in range(max_page):
            self.logger.info("{}: domain:{} page:[{}/{}] after_id:{}".format(self.source_name,
                                                                             target, i+1, max_page, next_id))
            items, next_id = self.cert_spotter_client(target, next_id)
            results |= items
            if next_id <= 0:
                break

        return list(results)

    def cert_spotter_client(self, domain, after=0):
        param = {
            "domain": domain,
            "include_subdomains": "true",
            "expand": "dns_names",
            "after": after,
        }

        conn = utils.http_req(self.api_url, params=param, timeout=(30.1, 50.1))
        data = conn.json()
        if isinstance(data, dict):
            if data["code"] == "rate_limited":
                retry_after = conn.headers.get("Retry-After", "0")
                sleep_time = int(retry_after) + 5
                self.logger.info("{}: Retry-After {}s".format(self.source_name, sleep_time))
                if sleep_time < 300:
                    time.sleep(sleep_time)
                    # 前面是频率限制重试一下
                    conn = utils.http_req(self.api_url, 'get', params=param, timeout=(30.1, 50.1))
                    data = conn.json()
            else:
                self.logger.error("{}: error: {}".format(self.source_name, json.dumps(data, ensure_ascii=False)))

        dns_names = set()
        next_id = 0
        if isinstance(data, list):
            for item in data:
                dns_names |= set(item["dns_names"])
            if data:
                next_id = data[-1]["id"]
            self.logger.debug("{}: {} result: {}, after: {}, next_id:{}".format(
                self.source_name, domain, len(data), after, next_id))
            # 表示结束了
            if len(data) < 100:
                next_id = 0

        return dns_names, int(next_id)
