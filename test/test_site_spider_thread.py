import unittest

from app.services import site_spider_thread


class TestSiteSpiderThread(unittest.TestCase):
    def test_site_spider_thread(self):
        entry_urls_list = [
           # ["https://daybreak.tophant.com", "https://daybreak.tophant.com/docs/9_api/"],
            ["https://account.tophant.com"]
        ]

        results = site_spider_thread(entry_urls_list, deep_num=5)
        for items in results:
            print(results[items])
