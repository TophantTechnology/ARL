import unittest
from app import services, utils
from app.tasks import domain
from app import modules
from app.services import altDNS


class TestDomain(unittest.TestCase):
    def test_alt_dns(self):
        c = ['www.baidu.com', 'map.baidu.com', 'test.baidu.com']
        w = ['private', 'api-docs', 'lc']

        data = services.alt_dns(c, "baidu.com", w)
        self.assertTrue(len(data) >= 1)

    def test_mass_dns(self):
        data = services.mass_dns("tophant.com", ["www"])
        self.assertTrue(len(data) >= 1)

    def test_mass_dns_fuzz(self):
        data = services.mass_dns("ccm-{fuzz}.qq.com", ["cdn", "www"])
        self.assertTrue(len(data) >= 1)

    def test_mass_dns_wildcard(self):
        logger = utils.get_logger()
        base_domain = "jd.com"
        fake_domain = "at" + utils.random_choices(4) + "." + base_domain
        wildcard_domain_ip = utils.get_ip(fake_domain, log_flag=False)

        wildcard_domain_ip.extend(utils.get_cname(fake_domain, log_flag=False))

        logger.info(wildcard_domain_ip)

        data = services.mass_dns(base_domain, ["www", "wwwaaa"], wildcard_domain_ip=wildcard_domain_ip)
        logger.info(data)
        self.assertTrue(len(data) >= 1)
        self.assertTrue("wwwaaa" not in str(data))

    def test_alt_dns_wildcard(self):
        logger = utils.get_logger()
        base_domain = "jd.com"
        fake_domain = "at" + utils.random_choices(4) + "." + base_domain
        wildcard_domain_ip = utils.get_ip(fake_domain, log_flag=False)

        wildcard_domain_ip.extend(utils.get_cname(fake_domain, log_flag=False))

        logger.info(wildcard_domain_ip)

        c = ['cn.' + base_domain, 'wwwaaa.' + base_domain]
        w = ['private', 'api-docs', 'c', 'wwwaaa']

        data = services.alt_dns(c, base_domain, w, wildcard_domain_ip=wildcard_domain_ip)
        logger.info(data)
        self.assertTrue(len(data) >= 1)
        self.assertTrue("wwwaaa" not in str(data))

    def test_domain_alt_dns(self):
        subdomain = "antibot.baidu.com"
        base_domain = "baidu.com"
        fake = {
            "domain": subdomain,
            "type": "CNAME",
            "record": [],
            "ips": []
        }
        fake_info = modules.DomainInfo(**fake)

        alt = domain.AltDNS([fake_info], base_domain)
        data = alt.run()
        self.assertTrue(len(data) >= 1)

    def test_alt_dns_subdomain(self):
        subdomain = "antibot.baidu.com"
        primary_domain = utils.get_fld(subdomain)
        # 当前下发的是主域名，就跳过
        if primary_domain == subdomain or primary_domain == "":
            return []
        fake = {
            "domain": subdomain,
            "type": "CNAME",
            "record": [],
            "ips": []
        }
        fake_info = modules.DomainInfo(**fake)

        print("alt_dns_current {}, primary_domain:{}".format(subdomain, primary_domain))
        data = domain.alt_dns([fake_info], primary_domain, wildcard_domain_ip=None)

        print(data)
        self.assertTrue(len(data) >= 1)

    def test_services_alt_dns(self):
        domains = ["test.baidu.com"]
        gen_domains = altDNS.DnsGen(set(domains), ["test", 'devops'],
                                    base_domain="baidu.com").run()

        data = list(gen_domains)
        print(data)
        self.assertTrue(len(data) >= 1)


if __name__ == '__main__':
    unittest.main()
