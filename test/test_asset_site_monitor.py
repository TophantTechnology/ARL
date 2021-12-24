import unittest

from app.services.asset_site_monitor import asset_site_monitor
from app.helpers.asset_site_monitor import submit_asset_site_monitor_job


class TestAssetSiteMonitor(unittest.TestCase):
    def test_scope_not_found(self):
        try:
            asset_site_monitor(scope_id="61382ea66591e709edd87299")
        except Exception as e:
            self.assertTrue("没有找到资产组" in str(e))

    def test_monitor(self):
        asset_site_monitor(scope_id="60b756b56591e7489b977a29")

    def test_monitor_job(self):
        submit_asset_site_monitor_job(scope_id="6168130a6591e724d0903aa7",
                                      name="测试站点监控", scheduler_id="60b756b56591e7489b977a29")


if __name__ == '__main__':
    unittest.main()
