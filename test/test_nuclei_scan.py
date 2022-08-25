import unittest
from app.services.nuclei_scan import nuclei_scan


class TestCDNName(unittest.TestCase):
    def test_nuclei_scan(self):
        name = nuclei_scan(["https://www.baidu.com"])


if __name__ == '__main__':
    unittest.main()
