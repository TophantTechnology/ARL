import time
import json
from app import  utils
from app.config import Config
from .baseThread import BaseThread
from .fileLeak import Page, HTTPReq, URL
logger = utils.get_logger()


class PageFetch(BaseThread):
    def __init__(self, sites, concurrency=6):
        super().__init__(sites, concurrency = concurrency)
        self.page_map = {}

    def work(self, site):
        req = HTTPReq(URL(site, ""))
        req.req()
        page = Page(req)

        data = page.dump_json()

        self.page_map[site] = data

    def run(self):
        t1 = time.time()
        logger.info("start PageFetch {}".format(len(self.targets)))
        self._run()
        elapse = time.time() - t1
        logger.info("end PageFetch elapse {}".format(elapse))
        return self.page_map


def page_fetch(sites, concurrency = 6):
    s = PageFetch(sites, concurrency = concurrency)
    return s.run()





