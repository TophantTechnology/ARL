import unittest
from app.services import fetch_favicon


class TestFavicon(unittest.TestCase):
    def test_favicon_error(self):
        data = fetch_favicon("https://106.55.91.130/")
        self.assertFalse(data)

    def test_favicon(self):
        data = fetch_favicon("https://www.qq.com/")
        self.assertTrue(data["hash"] == 1787932733)


if __name__ == '__main__':
    unittest.main()
