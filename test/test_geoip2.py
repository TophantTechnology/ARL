import unittest
from app.utils import get_ip_city, get_ip_asn


class TestGeoIP2(unittest.TestCase):
    def test_get_ip_city(self):
        r = get_ip_city("202.106.196.115")
        self.assertTrue(r["region_name"] == "Beijing")

    def test_get_ip_asn(self):
        r = get_ip_asn("202.106.196.115")
        self.assertTrue(r["number"] == 4808)


if __name__ == '__main__':
    unittest.main()
