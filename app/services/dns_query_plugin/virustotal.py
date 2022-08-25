import base64
import json
import time
import re
from app.services.dns_query import DNSQueryBase
from app import utils


class Query(DNSQueryBase):
    def __init__(self):
        super(Query, self).__init__()
        self.source_name = "virustotal"
        self.api_url = "https://www.virustotal.com/"
        self.api_key = None

    def init_key(self, api_key=None):
        self.api_key = api_key

    def sub_domains(self, target):
        first_url = "{}api/v3/domains/{}/subdomains?limit=40".format(self.api_url, target)
        headers = {
            "x-apikey": self.api_key
        }
        next_url = first_url
        results = []
        curr_page = 1
        while True:
            self.logger.debug("{} target:{} curr_page:{}".format(self.source_name, target, curr_page))
            conn = utils.http_req(next_url, 'get', headers=headers)
            data = conn.json()
            if data.get("error"):
                self.logger.error("{} query error:{}".format(self.source_name, json.dumps(data, ensure_ascii=False)))
                break

            items = re.findall(r'"([^"]+)"', conn.text)

            for item in items:
                if item.endswith("." + target):
                    results.append(item)

            next_url = data["links"].get("next")
            curr_page += 1
            if not next_url:
                break

            self.logger.debug(
                "{} count:{} next_url: {}".format(
                    self.source_name, data["meta"]["count"], next_url))

            time.sleep(2)

        return list(set(results))

