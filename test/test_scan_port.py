import unittest
from app.tasks.domain import scan_port
from app.modules import ScanPortType
from app import services


class TestCDNName(unittest.TestCase):
    def test_scan_port(self):
        scan_port_option = {
            "ports": ScanPortType.TEST,
            "service_detect": False,
            "os_detect": False,
            "skip_scan_cdn_ip": False  # 跳过扫描CDN IP
        }
        domain_info = services.build_domain_info(['join.lianjia.com', 'gzh.qq.com'], concurrency=10)
        print(domain_info)

        self.assertTrue(len(domain_info) == 2)

        ip_info_list = scan_port(domain_info, scan_port_option)
        print(ip_info_list)
        for info in ip_info_list:
            self.assertTrue(info.cdn_name)

    def test_scan_port_skip(self):
        scan_port_option = {
            "ports": ScanPortType.TEST,
            "service_detect": False,
            "os_detect": False,
            "skip_scan_cdn_ip": True  # 跳过扫描CDN IP
        }
        domain_info = services.build_domain_info(['www.taobao.com', 'www.aliyun.com'], concurrency=10)
        self.assertTrue(len(domain_info) == 2)

        ip_info_list = scan_port(domain_info, scan_port_option)
        for info in ip_info_list:
            self.assertTrue(info.cdn_name)
            self.assertTrue(len(info.port_info_list) == 2)


if __name__ == '__main__':
    unittest.main()
