import unittest
from app.utils import get_cdn_name_by_ip, get_cdn_name_by_cname


class TestCDNName(unittest.TestCase):
    def test_cdn_ip(self):
        name = get_cdn_name_by_ip("1.1.1.1")

        self.assertTrue(name == "")

        name = get_cdn_name_by_ip("164.88.98.2")
        self.assertTrue(name == "云盾CDN")

    def test_cdn_cname(self):
        name = get_cdn_name_by_cname("example.com")
        self.assertTrue(name == "")

        name = get_cdn_name_by_cname("zff.qaxwzws.com")
        self.assertTrue(name == "网神CDN")

        name = get_cdn_name_by_cname("zff.xxgslb.com")
        self.assertTrue(name == "CDN")

        name = get_cdn_name_by_cname("zff.akamaized.net")
        self.assertTrue(name == "AkamaiCDN")

if __name__ == '__main__':
    unittest.main()
