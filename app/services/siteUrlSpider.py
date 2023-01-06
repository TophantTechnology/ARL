import time
from app import utils
from app.utils.url import urlsimilar
from .baseThread import BaseThread
from urllib.parse import urljoin, urlparse
from pyquery import PyQuery as pq

logger = utils.get_logger()


class URLTYPE:
    document = "document"
    js = "js"
    css = "css"


class URLInfo(object):
    def __init__(self, entry_url, crawl_url, url_type):
        self.entry_url = entry_url
        self.crawl_url = crawl_url
        self._similar_hash = urlsimilar(self.crawl_url)
        self.type = url_type or URLTYPE.document

    def to_dict(self):
        obj = dict()
        obj["base_url"] = self.entry_url
        obj["crawl_url"] = self.crawl_url
        obj["type"] = self.type
        return obj

    def __eq__(self, other):
        if not isinstance(other, URLInfo):
            return False
        return self.crawl_url == self.crawl_url

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return str(self.to_dict())

    def __str__(self):
        return self.__repr__()

    def __hash__(self):
        return self._similar_hash

    def similar_hash(self):
        return self._similar_hash


class URLList(object):
    def __init__(self):
        self.result = []
        self.similar_hash_pool = []

    def __iter__(self):
        return self.result.__iter__()

    def __getitem__(self, item):
        return self.result[item]

    def __len__(self):
        return self.result.__len__()

    def add(self, element: URLInfo):
        """
        正常添加
        :param element: URLInfo
        :return:
        """
        if not isinstance(element, URLInfo):
            raise TypeError("need URLInfo")
        if element not in self.result:
            self.result.append(element)

    def __repr__(self):
        return str(self.result)

    def __str__(self):
        return self.__repr__()

    def __contains__(self, item):
        if not isinstance(item, URLInfo):
            return False

        return item.similar_hash() in self.similar_hash_pool


class URLSimilarList(URLList):
    def add(self, element: URLInfo):
        """
        URL去除相似后添加
        :param element: URLInfo
        :return:
        """
        if not isinstance(element, URLInfo):
            raise TypeError("need URLinfo")

        if element.similar_hash() not in self.similar_hash_pool:
            self.result.append(element)
            self.similar_hash_pool.append(element.similar_hash())


class SiteURLSpider(object):
    def __init__(self, entry_urls=None, deep_num=3):
        entry_url_list = URLSimilarList()
        for url in entry_urls:
            entry_url_list.add(URLInfo(url, url, URLTYPE.document))

        self.entry_url_list = entry_url_list
        self.done_url_list = URLSimilarList()
        self.deep_num = deep_num
        self.all_url_list = URLSimilarList()
        self.max_url = max(60, len(entry_urls)*6)
        self.scope_url = entry_urls[0]

        self.tagMap = [{'name': 'a', 'attr': 'href', 'type': URLTYPE.document},
                       {'name': 'form', 'attr': 'action', 'type': URLTYPE.document},
                       {'name': 'iframe', 'attr': 'src', 'type': URLTYPE.document},
                       #{'name': 'script', 'attr': 'src', 'type': URLTYPE.js},
                       #{'name': 'link', 'attr': 'href', 'type': URLTYPE.css}
                       ]

        self.ignore_ext = [".pdf", ".xls", ".xlsx", ".doc", ".docx", ".ppt", ".pptx", ".zip", ".rar"]
        self.ignore_ext.extend([".png", ".jpg", ".gif", ".js", ".css", ".ico"])

    def get_urls(self, entry_url):
        return self._work(entry_url)

    def _work(self, entry_url):
        try:
            logger.debug("[{}] req = > {}".format(len(self.done_url_list), entry_url))
            if utils.url_ext(entry_url) in self.ignore_ext:
                return URLSimilarList()

            conn = utils.http_req(entry_url)
            if conn.status_code in [301, 302, 307]:
                _url = urljoin(entry_url, conn.headers.get("Location", "")).strip()
                _url = utils.normal_url(_url)
                if _url is None:
                    return URLSimilarList()

                url_info = URLInfo(entry_url, _url, URLTYPE.document)
                if utils.same_netloc(entry_url, _url) and (url_info not in self.done_url_list):
                    entry_url = _url
                    logger.info("[{}] req 302 = > {}".format(len(self.done_url_list), entry_url))
                    conn = utils.http_req(_url)
                    self.done_url_list.add(url_info)
                    self.all_url_list.add(url_info)

            html = conn.content
            if "html" not in conn.headers.get("Content-Type", "").lower():
                return URLSimilarList()

            dom = pq(html)
            ret_url = URLSimilarList()
            for tag in self.tagMap:
                items = dom(tag['name']).items()
                for i in items:
                    _url = urljoin(entry_url, i.attr(tag['attr'])).strip()
                    _url = utils.normal_url(_url)
                    if _url is None:
                        continue

                    if utils.url_ext(_url) in self.ignore_ext:
                        continue

                    _type = tag["type"]
                    if utils.same_netloc(_url, entry_url):
                        url_info = URLInfo(entry_url, _url, _type)
                        ret_url.add(url_info)
                        self.all_url_list.add(url_info)
            return ret_url
        except Exception as e:
            logger.error("error on {} {}".format(entry_url, e))
            return URLSimilarList()

    def run(self):
        tmp_urls = self.entry_url_list
        for num in range(0, self.deep_num):
            if len(tmp_urls) > 0:
                logger.info("{} deep num {}, len {}".format(self.scope_url, num + 1, len(tmp_urls)))

            new_url = URLSimilarList()
            for info in tmp_urls:
                self.all_url_list.add(info)
                if len(self.done_url_list) > self.max_url:
                    logger.warning("exit on request max url {}".format(self.scope_url))
                    return self.all_url_list

                if info not in self.done_url_list:
                    ret_urls = self.get_urls(info.crawl_url)
                    self.done_url_list.add(info)
                    for x in ret_urls:
                        new_url.add(x)

            tmp_urls = new_url

        return self.all_url_list


class SiteURLSpiderThread(BaseThread):
    def __init__(self, entry_urls_list, concurrency=6, deep_num=5):
        super().__init__(entry_urls_list, concurrency=concurrency)
        self.site_url_map = {}
        self.deep_num = deep_num

    def work(self, entry_urls):
        # entry_urls 是一个数组，第一个是当前站点
        site = entry_urls[0]
        self.site_url_map[site] = site_spider(entry_urls, self.deep_num)

    def run(self):
        t1 = time.time()
        logger.info("start site url spider entry_urls_list:{}".format(len(self.targets)))
        self._run()
        elapse = time.time() - t1
        logger.info("end site url spider ({:.2f}s)".format(elapse))
        return self.site_url_map


def site_spider_thread(entry_urls_list, deep_num=5):
    s = SiteURLSpiderThread(entry_urls_list, concurrency=6, deep_num=deep_num)
    return s.run()


def site_spider(entry_url, deep_num=3):
    if isinstance(entry_url, str):
        entry_url = [entry_url]

    ret = []
    s = SiteURLSpider(entry_url, deep_num)
    for x in s.run():
        if urlparse(x.crawl_url).path == "/" or (not urlparse(x.crawl_url).path):
            continue

        if x.type == URLTYPE.document:
            ret.append(x.crawl_url)

    return ret










