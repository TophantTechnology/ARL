from threading import Thread
import unittest
import time
from app.services import npoc
from app.config import Config

class TestUtilsNpoc(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestUtilsNpoc, self).__init__(*args, **kwargs)

    def test_load_poc(self):
        n = npoc.NPoC(tmp_dir=Config.TMP_PATH)
        plugins = n.load_all_poc()
        print("plugins", len(plugins))
        self.assertTrue(len(plugins) >= 10)

    def test_sync_2_db(self):
        npoc.sync_to_db(del_flag=True)

    def test_run_all_poc(self):
        n = npoc.NPoC(tmp_dir=Config.TMP_PATH)
        targets = ["https://www.baidu.com/"]
        ret = n.run_all_poc(targets)
        if ret:
            print(ret)

    def test_run_poc_cnt(self):
        targets = ["https://www.baidu.com/"]
        self.run_all_poc(targets)

    def test_run_poc(self):
        names = ["Thinkphp5_RCE"]
        targets = ["https://www.baidu.com/"]
        npoc.run_risk_cruising(plugins=names, targets=targets)

    def run_all_poc(self, targets):
        n = npoc.NPoC(tmp_dir=Config.TMP_PATH, concurrency=6)
        run_total = len(n.plugin_name_list) * len(targets)
        print("run total {}".format(run_total))
        run_thread = Thread(target=n.run_all_poc, args=(targets,))
        run_thread.start()
        while run_thread.is_alive():
            time.sleep(0.6)
            print("runner cnt {}/{}".format(n.runner.runner_cnt, run_total))

        if n.result:
            print(n.result)

        print("done")

    def test_result_set_run_poc(self):
        from app import utils
        from bson import ObjectId
        item = utils.conn_db("result_set").find_one({"_id": ObjectId("6017edf36591e76d16171b65")})
        if not item:
            return
        targets = item["items"]
        self.run_all_poc(targets)


if __name__ == '__main__':
    unittest.main()
