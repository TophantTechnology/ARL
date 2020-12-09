import time
from app import utils, modules, services
from .baseThread import BaseThread

logger = utils.get_logger()




class FetchCert(BaseThread):
    def __init__(self, targets, concurrency=6):
        super().__init__(targets, concurrency=concurrency)
        self.fetch_map = {}

    def work(self, target):
        ip, port = target.split(":")
        cert = utils.get_cert(ip, int(port))
        if cert:
            self.fetch_map[target] = cert

    def run(self):
        t1 = time.time()
        logger.info("start FetchCert {}".format(len(self.targets)))
        self._run()
        elapse = time.time() - t1
        logger.info("end FetchCert elapse {}".format(elapse))
        return self.fetch_map



def fetch_cert(targets, concurrency = 15):
    f = FetchCert(targets, concurrency = concurrency)
    return f.run()



class SSLCert():
    def __init__(self, ip_info_list, base_doamin = None):
        self.ip_info_list = ip_info_list
        self.base_domain = base_doamin

    def run(self):
        target_temp_list = []
        for info in self.ip_info_list:
            if isinstance(info, modules.IPInfo):
                for port_info in info.port_info_list:
                    port_id = port_info.port_id
                    if port_id == 80:
                        continue

                    target_temp1 = "{}:{}".format(info.ip, port_id)
                    target_temp_list.append(target_temp1)

            elif isinstance(info, str) and utils.is_vaild_ip_target(info):
                target_temp_list.append("{}:443".format(info))

            elif isinstance(info, str) and ":" in info:
                target_temp_list.append(info)

        cert_map = services.fetch_cert(target_temp_list)

        for target in cert_map:
            pass

        return cert_map

