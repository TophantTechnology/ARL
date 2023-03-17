from app import utils
from app.config import Config
import os

logger = utils.get_logger()


class MassDNS:
    def __init__(self, domains=None, mass_dns_bin=None,
                 dns_server=None, tmp_dir=None, wildcard_domain_ip=None, concurrent=0):

        if wildcard_domain_ip is None:
            wildcard_domain_ip = []

        if concurrent == 0:
            concurrent = 100

        self.domains = domains
        self.tmp_dir = tmp_dir
        self.dns_server = dns_server
        self.domain_gen_output_path = os.path.join(tmp_dir,
                                                   "domain_gen_{}".format(utils.random_choices()))
        self.mass_dns_output_path = os.path.join(tmp_dir,
                                                 "mass_dns_{}".format(utils.random_choices()))
        self.mass_dns_bin = mass_dns_bin
        self.wildcard_domain_ip = wildcard_domain_ip
        self.concurrent = concurrent

    def domain_write(self):
        """将域名写到文件"""
        cnt = 0
        with open(self.domain_gen_output_path, "w") as f:
            for domain in self.domains:
                domain = domain.strip()
                if not domain:
                    continue
                f.write(domain + "\n")
                cnt += 1

        logger.info("MassDNS dict {}".format(cnt))

    def mass_dns(self):
        """域名爆破"""
        command = [self.mass_dns_bin, "-q",
                   "-r {}".format(self.dns_server),
                   "-o S",
                   "-w {}".format(self.mass_dns_output_path),
                   "-s {}".format(self.concurrent),
                   self.domain_gen_output_path,
                   "--root"
                   ]

        logger.info(" ".join(command))
        utils.exec_system(command, timeout=5*24*60*60)

    def parse_mass_dns_output(self):
        output = []
        with open(self.mass_dns_output_path, "r+", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                data = line.split(" ")
                if len(data) != 3:
                    continue
                domain, _type, record = data
                record = record.strip().strip(".")

                # 泛解析域名IP  直接过滤掉
                if record in self.wildcard_domain_ip:
                    continue

                item = {
                    "domain": domain.strip("."),
                    "type": _type,
                    "record": record
                }
                output.append(item)

        self._delete_file()
        return output

    def _delete_file(self):
        try:
            os.unlink(self.domain_gen_output_path)
            os.unlink(self.mass_dns_output_path)
        except Exception as e:
            logger.warning(e)

    def run(self):
        self.domain_write()
        self.mass_dns()
        output = self.parse_mass_dns_output()
        return output


def mass_dns(based_domain, words, wildcard_domain_ip=None):
    if wildcard_domain_ip is None:
        wildcard_domain_ip = []

    domains = []
    is_fuzz_domain = "{fuzz}" in based_domain
    for word in words:
        word = word.strip()
        if word:
            if is_fuzz_domain:
                domains.append(based_domain.replace("{fuzz}", word))
            else:
                domains.append("{}.{}".format(word, based_domain))

    if not is_fuzz_domain:
        domains.append(based_domain)

    logger.info("start brute:{} words:{} wildcard_record:{}".format(
        based_domain, len(domains), ",".join(wildcard_domain_ip)))

    mass = MassDNS(domains, mass_dns_bin=Config.MASSDNS_BIN,
                   dns_server=Config.DNS_SERVER, tmp_dir=Config.TMP_PATH,
                   wildcard_domain_ip=wildcard_domain_ip, concurrent=Config.DOMAIN_BRUTE_CONCURRENT)

    return mass.run()
