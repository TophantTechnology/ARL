import unittest
from app import services


class TestDomain(unittest.TestCase):
    def test_fetch_site(self):
        sites = ["https://www.baidu.com"]
        data = services.fetch_site(sites, concurrency=2)
        self.assertTrue(len(data) >= 1)
        self.assertTrue(len(data[0]["finger"]) >= 3)
        self.assertTrue(len(data[0]["favicon"]["data"]) >= 10)
        self.assertTrue(data[0]["favicon"]["hash"] == -1588080585)

    def test_leye_taobao(self):
        sites = ["https://leye.taobao.com"]
        data = services.fetch_site(sites, concurrency=2)
        self.assertTrue(len(data) == 2)
        self.assertTrue(len(data[0]["finger"]) >= 1)


if __name__ == '__main__':
    unittest.main()
