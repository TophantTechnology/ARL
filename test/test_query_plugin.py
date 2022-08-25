import logging
import sys
import unittest
from app.services.dns_query import run_query_plugin
from app import utils


class TestQueryPlugin(unittest.TestCase):
    def test_run_query_plugin(self):
        logger = utils.get_logger()
        logger.setLevel(logging.DEBUG)

        # pycharm 下运行
        if "/pycharm/" in sys.argv[0]:
            results = run_query_plugin("tophant.com", ["crtsh"])
        else:
            print("sources :{}".format(" ".join(sys.argv[1:])))
            results = run_query_plugin("tophant.com", sys.argv[1:])

        print("results:")
        for item in results:
            print(item["domain"], item["source"])
        self.assertTrue(len(results) >= 1)


if __name__ == '__main__':
    #  python3.6 -m test.test_query_plugin [source1] [source2]
    unittest.main(argv=[sys.argv[0]])
