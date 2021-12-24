import unittest
from app.config import Config
from app.utils import http_req, get_logger, get_title

logger = get_logger()


class TestProxyURL(unittest.TestCase):
    def test_proxy_url(self):
        self.assertTrue(Config.PROXY_URL)
        target = "https://www.baidu.com"
        conn = http_req(target)
        code = conn.status_code
        logger.info("req:{} proxy:{}".format(target, Config.PROXY_URL))
        title = get_title(conn.content)
        logger.info("status_code:{} title:{} body_length:{}".format(code, title, len(conn.content)))

        self.assertTrue(conn.status_code == 200)


if __name__ == '__main__':
    unittest.main()
