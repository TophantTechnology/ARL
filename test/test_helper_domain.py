import unittest
from app.helpers.domain import find_private_domain_by_task_id, find_public_ip_by_task_id


class TestHelperDomain(unittest.TestCase):
    def test_private_domain(self):
        task_id = "61513c9f6591e704f896b175"
        domains = find_private_domain_by_task_id(task_id)
        self.assertTrue(len(domains) > 1)

    def test_public_ip(self):
        task_id = "61513c9f6591e704f896b175"
        ips = find_public_ip_by_task_id(task_id)
        self.assertTrue(len(ips) > 1)


if __name__ == '__main__':
    unittest.main()
