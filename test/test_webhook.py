import sys
import unittest
from app.services.webhook import ip_asset_web_hook, domain_asset_web_hook, site_asset_web_hook
from app.config import Config


class TestCDNName(unittest.TestCase):
    def test_ip_asset_web_hook(self):
        self.assertTrue(Config.WEB_HOOK_URL)

        if "/pycharm/" in sys.argv[0]:
            task_id = "62e20a4a6591e72712558422"
            scope_id = "61b9e0a56591e70a53c5f69d"
        else:
            task_id = sys.argv[1]
            scope_id = sys.argv[2]

        print("task_id:{} scope_id: web_hook_url:{}".format(task_id, scope_id, Config.WEB_HOOK_URL))
        ip_asset_web_hook(task_id=task_id, scope_id=scope_id)

    def test_domain_asset_web_hook(self):
        self.assertTrue(Config.WEB_HOOK_URL)

        if "/pycharm/" in sys.argv[0]:
            task_id = "62d8c1f76591e723876347ee"
            scope_id = "61b9e0a56591e70a53c5f69d"
        else:
            task_id = sys.argv[1]
            scope_id = sys.argv[2]

        print("task_id:{} scope_id: web_hook_url:{}".format(task_id, scope_id, Config.WEB_HOOK_URL))
        domain_asset_web_hook(task_id=task_id, scope_id=scope_id)

    def test_site_asset_web_hook(self):
        self.assertTrue(Config.WEB_HOOK_URL)

        if "/pycharm/" in sys.argv[0]:
            task_id = "62d8c1f76591e723876347ee"
            scope_id = "61b9e0a56591e70a53c5f69d"
        else:
            task_id = sys.argv[1]
            scope_id = sys.argv[2]

        print("task_id:{} scope_id: web_hook_url:{}".format(task_id, scope_id, Config.WEB_HOOK_URL))
        site_asset_web_hook(task_id=task_id, scope_id=scope_id)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]])
