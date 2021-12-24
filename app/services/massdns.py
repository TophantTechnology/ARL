from app import utils
from app.config import Config
import  os
logger = utils.get_logger()


class MassDNS:
    def __init__(self, domains = None, massdns_bin = None,
                 dnsserver = None, tmp_dir = None):
        self.domains = domains
        self.tmp_dir = tmp_dir
        self.dnsserver = dnsserver
        self.domaingen_output_path = os.path.join(tmp_dir,
                                                "domaingen_{}".format(utils.random_choices()))
        self.massdns_output_path = os.path.join(tmp_dir,
                                               "massdns_{}".format(utils.random_choices()))
        self.massdns_bin = massdns_bin


    def domaingen(self):
        with open(self.domaingen_output_path, "w") as f:
            for domain in self.domains:
                domain = domain.strip()
                if not domain:
                    continue
                f.write(domain + "\n")


    def massdns(self):
        command = [self.massdns_bin, "-q",
                   "-r {}".format(self.dnsserver),
                   "-o S",
                   "-w {}".format(self.massdns_output_path),
                   "-s {}".format(Config.DOMAIN_BRUTE_CONCURRENT),
                   self.domaingen_output_path,
                   "--root"
                   ]

        logger.info(" ".join(command))
        utils.exec_system(command)

    def parse_massdns_output(self):
        output = []
        lines = utils.load_file(self.massdns_output_path)
        for line in lines:
            data = line.split(" ")
            if len(data) != 3:
                continue
            domain, type, record = data
            item = {
                "domain": domain.strip("."),
                "type": type,
                "record": record.strip().strip(".")
            }
            output.append(item)

        self._delete_file()
        return output

    def _delete_file(self):
        try:
            os.unlink(self.domaingen_output_path)
            os.unlink(self.massdns_output_path)
        except Exception as e:
            logger.warning(e)

    def run(self):
        self.domaingen()
        self.massdns()
        output = self.parse_massdns_output()
        return output


def mass_dns(basedomain, words):
    domains = []
    is_fuzz_domain = "{fuzz}" in basedomain
    for word in words:
        word = word.strip()
        if word:
            if is_fuzz_domain:
                domains.append(basedomain.replace("{fuzz}", word))
            else:
                domains.append("{}.{}".format(word, basedomain))

    domains.append(basedomain)
    mass = MassDNS(domains, massdns_bin=Config.MASSDNS_BIN,
               dnsserver=Config.DNS_SERVER, tmp_dir=Config.TMP_PATH)

    return mass.run()