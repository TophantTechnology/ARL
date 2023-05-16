import time
from app import utils
from .baseThread import BaseThread
logger = utils.get_logger()


class ProbeHTTP(BaseThread):
    def __init__(self, domains, concurrency=6):
        super().__init__(self._build_targets(domains), concurrency = concurrency)

        self.sites = []
        self.domains = domains

    def _build_targets(self, domains):
        _targets = []
        for item in domains:
            domain = item
            if hasattr(item, 'domain'):
                domain = item.domain

            _targets.append("https://{}".format(domain))
            _targets.append("http://{}".format(domain))

        return _targets

    def work(self, target):
        conn = utils.http_req(target, 'head', timeout=(3, 2))

        if conn.status_code in [502, 504, 501, 422, 410]:
            logger.debug(f"{target} 状态码为 {conn.status_code} 跳过")
            return

        self.sites.append(target)

    def run(self):
        t1 = time.time()
        logger.info("start ProbeHTTP {}".format(len(self.targets)))
        self._run()
        # 去除https和http相同的
        alive_site = []
        for x in self.sites:
            if x.startswith("https://"):
                alive_site.append(x)

            elif x.startswith("http://"):
                x_temp = "https://" + x[7:]
                if x_temp not in self.sites:
                    alive_site.append(x)

        elapse = time.time() - t1
        logger.info("end ProbeHTTP {} elapse {}".format(len(alive_site), elapse))

        return alive_site


def probe_http(domain, concurrency=10):
    p = ProbeHTTP(domain, concurrency=concurrency)
    return p.run()
