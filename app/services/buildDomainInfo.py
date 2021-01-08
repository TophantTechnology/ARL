import time
from app import  modules
from app import  utils
from .baseThread import BaseThread
logger = utils.get_logger()


class BuildDomainInfo(BaseThread):
    def __init__(self, domains, concurrency=6):
        super().__init__(domains, concurrency = concurrency)

        self.domain_info_list = []


    def work(self, target):
        domain = target
        if hasattr(target, "domain"):
            domain = target.domain

        ips = utils.get_ip(domain)
        if not ips:
            return

        cnames = utils.get_cname(domain, False)

        info = {
            "domain": domain,
            "type": "A",
            "record": ips,
            "ips": ips
        }

        if cnames:
            info["type"] = 'CNAME'
            info["record"] = cnames

        self.domain_info_list.append(modules.DomainInfo(**info))

    def run(self):
        t1 = time.time()
        logger.info("start build Domain info {}".format(len(self.targets)))
        self._run()
        elapse = time.time() - t1
        logger.info("end build Domain info {} elapse {}".format(len(self.domain_info_list), elapse))

        return self.domain_info_list


def build_domain_info(domains, concurrency=15):
    p = BuildDomainInfo(domains, concurrency=concurrency)
    return p.run()
