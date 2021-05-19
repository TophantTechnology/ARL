import unittest
from app import services


class TestCrtsh(unittest.TestCase):
    def test_crtsh(self):
        data = services.crtsh_search("tophant.com")
        self.assertTrue(len(data) >= 1)


if __name__ == '__main__':
    unittest.main()
