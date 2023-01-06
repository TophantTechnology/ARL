import unittest
from app.services import baidu_search, bing_search
from app.services.searchEngines import search_engines


class TestSearchEngines(unittest.TestCase):
    def test_baidu_search(self):
        urls = baidu_search("tophant.com")
        print("result:", len(urls))
        for x in urls:
            print(x)

    def test_bing_search(self):
        urls = bing_search("qq.com")
        print("result:", len(urls))
        for x in urls:
            print(x)

    def test_search_engines(self):
        urls = search_engines("vulbox.com")
        print("result:", len(urls))
        for x in urls:
            print(x)


if __name__ == '__main__':
    unittest.main()
