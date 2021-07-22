import unittest
from app.modules import SiteAutoTag
from app.services import auto_tag
from app.services.fetchSite import fetch_site


class TestCDNName(unittest.TestCase):
    def test_302_1(self):
        item = {
            "site": "https://www.qq.com",
            "title": "",
            "status": 302,
            "headers": "Connection: keep-alive\nLocation: https://url.cn/sorry",
            "body_length": 0,
        }
        auto_tag(item)
        self.assertTrue(item["tag"][0] == SiteAutoTag.INVALID)

    def test_302_2(self):
        item = {
            "site": "https://www.qq.com",
            "title": "",
            "status": 302,
            "headers": "Connection: close\nLocation: https://www.dnspod.cn/promo/mi",
            "body_length": 0,
        }
        auto_tag(item)
        self.assertTrue(item["tag"][0] == SiteAutoTag.ENTRY)

    def test_200(self):
        site_info_list = fetch_site(["https://www.baidu.com"])
        auto_tag(site_info_list)
        self.assertTrue(site_info_list[0]["tag"][0] == SiteAutoTag.ENTRY)

    def test_invalid(self):
        item = {
            "site": "https://www.qq.com",
            "title": "Test Page for the Nginx HTTP Server on Fedora",
            "status": 200,
            "headers": "Connection: close",
            "body_length": 3700,
        }
        auto_tag(item)
        self.assertTrue(item["tag"][0] == SiteAutoTag.INVALID)

    def test_entry(self):
        item = {
            "site": "https://www.qq.com",
            "title": "",
            "status": 200,
            "headers": "Content-Type: text/html",
            "body_length": 260,
        }
        auto_tag(item)
        self.assertTrue(item["tag"][0] == SiteAutoTag.ENTRY)


if __name__ == '__main__':
    unittest.main()
