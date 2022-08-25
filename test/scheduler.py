import unittest
from app.tasks.scheduler import wrap_domain_executors


base_doamin = "qq.com"
job_id = "5fb51bb26591e71df2d1f27d"
scope_id = "5fb51bb26591e71df2d1f27c"

options = {
    'domain_brute': True,
    'domain_brute_type': 'test',
    'alt_dns': False,
    'arl_search': False,
    'port_scan_type': 'test',
    'port_scan': True,
    'dns_query_plugin': False,
    'site_identify': True
}


class TestScheduler(unittest.TestCase):
    def test_01_domain_execute(self):
        wrap_domain_executors(base_domain=base_doamin,
                              job_id=job_id, scope_id=scope_id, options=options)


if __name__ == '__main__':
    unittest.main()