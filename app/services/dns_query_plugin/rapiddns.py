import logging

from app.services.dns_query import DNSQueryBase
from app import utils
from pyquery import PyQuery as pq

class Query(DNSQueryBase):
    def __init__(self):
        super(Query, self).__init__()
        self.source_name = "rapiddns"
        self.api_url = "https://rapiddns.io/"

    def sub_domains(self, target):
        url = "{}subdomain/{}?full=1".format(self.api_url, target)

        # *** 当数据比较大的时候会报错， Connection broken: IncompleteRead(0 bytes read)
        html = utils.http_req(url, timeout=(30.1, 50.1)).content
        results = []
        dom = pq(html)
        items = dom("#table > tbody > tr")
        for item in items:
            subdomain = pq(item)("td:nth-child(2)").text()
            results.append(subdomain)

        return list(set(results))

