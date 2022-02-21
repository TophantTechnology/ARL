import threading
import collections
import time

from app import utils
from .baseThread import BaseThread

import requests.exceptions
logger = utils.get_logger()


class CheckHTTP(BaseThread):
    def __init__(self, urls, concurrency=10):
        super().__init__(urls, concurrency=concurrency)
        self.timeout = (5, 3)
        self.checkout_map = {}

    def check(self, url):
        conn = utils.http_req(url, method="head", timeout=self.timeout)
        if conn.status_code == 400:
            # 特殊情况排除
            etag = conn.headers.get("ETag")
            date = conn.headers.get("Date")
            if not etag or not date:
                return None

        if (conn.status_code >= 501) and (conn.status_code < 600):
            return None

        if conn.status_code == 403:
            conn2 = utils.http_req(url)
            check = b'</title><style type="text/css">body{margin:5% auto 0 auto;padding:0 18px}'
            if check in conn2.content:
                return None

        item = {
            "status": conn.status_code,
            "content-type": conn.headers.get("Content-Type", "")
        }

        return item

    def work(self, url):
        try:
            out = self.check(url)
            if out is not None:
                self.checkout_map[url] = out

        except requests.exceptions.RequestException as e:
            pass

        except Exception as e:
            logger.warning("error on url {}".format(url))
            logger.warning(e)

    def run(self):
        t1 = time.time()
        logger.info("start check http {}".format(len(self.targets)))
        self._run()
        elapse = time.time() - t1
        logger.info("end start check http {} elapse {}".format(len(self.checkout_map), elapse))
        return self.checkout_map


def check_http(urls, concurrency=15):
    c = CheckHTTP(urls, concurrency)
    return c.run()
