import unittest
from app.services.fofaClient import fofa_query_result, fofa_query


class TestFofa(unittest.TestCase):
    def test_query(self):
        data = fofa_query('ip="1.1.1.1"', page_size=1)
        self.assertTrue(data["size"] >= 1)

    def test_query_result(self):
        results = fofa_query_result('ip="1.1.1.1"', page_size=100)
        self.assertTrue(len(results) == 1)


if __name__ == '__main__':
    unittest.main()
