from app import utils
import threading
import collections
from app.modules import  DomainInfo
from .baseThread import BaseThread
logger = utils.get_logger()


class ResolverDomain(BaseThread):
    def __init__(self, domains, concurrency=6):
        super().__init__(domains, concurrency=concurrency)
        self.resolver_map = {}

    '''
    {
        "api.baike.baidu.com":[
            "180.97.93.62",
            "180.97.93.61"
        ],
        "apollo.baidu.com":[
            "123.125.115.15"
        ],
        "www.baidu.com":[
            "180.101.49.12",
            "180.101.49.11"
        ]
    }
    '''
    def work(self, domain):
        curr_domain = domain
        if isinstance(domain, dict):
            curr_domain = domain.get("domain")

        elif isinstance(domain, DomainInfo):
            curr_domain = domain.domain

        if not curr_domain:
            return

        if curr_domain in self.resolver_map:
            return

        self.resolver_map[curr_domain] = utils.get_ip(curr_domain)

    def run(self):
        self._run()
        return self.resolver_map


def resolver_domain(domains, concurrency=15):
    r = ResolverDomain(domains, concurrency)
    return r.run()
