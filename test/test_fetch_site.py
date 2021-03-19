import unittest
from app import services


class TestDomain(unittest.TestCase):
    def test_fetch_site(self):
        sites = ["https://www.baidu.com"]
        data = services.fetch_site(sites, concurrency=2)
        self.assertTrue(len(data) >= 1)
        self.assertTrue(len(data[0]["favicon"]["data"]) >= 10)
        self.assertTrue(data[0]["favicon"]["hash"] == -1507567067)


if __name__ == '__main__':
    unittest.main()
