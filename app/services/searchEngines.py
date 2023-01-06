import re
from pyquery import PyQuery as pq
import time
from urllib.parse import quote, urljoin, urlparse
from app import utils

logger = utils.get_logger()


class BaiduSearch(object):
    def __init__(self, keyword=None, page_num=6):
        self.search_url = "https://www.baidu.com/s?rn=100&pn={page}&wd={keyword}"
        self.num_pattern = re.compile(r'百度为您找到相关结果约?([\d,]*)个')
        self.first_html = ""
        self.keyword = keyword
        self.page_num = page_num
        self.pq_query = "#content_left h3.t a"
        self.headers = {"Accept-Language": "zh-cn"}
        self.search_result_num = 0
        self.default_interval = 3

    def result_num(self):
        url = self.search_url.format(page=0, keyword=quote(self.keyword))
        html = utils.http_req(url, headers=self.headers).text
        self.first_html = html
        result = re.findall(self.num_pattern, html)
        if not result:
            logger.warning("Unable to get baidu search results， {}".format(self.keyword))
            return 0

        num = int("".join(result[0].split(",")))
        self.search_result_num = num
        return num

    def match_urls(self, html):
        result = re.findall(self.num_pattern, html)
        if not result:
            raise Exception("获取百度结果异常")

        dom = pq(html)
        result_items = dom(self.pq_query).items()
        urls_result = [item.attr("href") for item in result_items]
        urls = set()
        for u in urls_result:
            try:
                if not re.match(r'^https?:/{2}\w.+$', u):
                    logger.info("url {} is invalid".format(u))
                    continue
                resp = utils.http_req(u, "head")
                real_url = resp.headers.get('Location')
                if real_url:
                    urls.add(real_url)
            except Exception as e:
                logger.exception(e)
        return list(urls)

    def run(self):
        self.result_num()
        logger.info("baidu search {} results found for keyword {}".format(self.search_result_num, self.keyword))
        urls = []

        # 没有找到直接return
        if self.search_result_num == 0:
            return urls

        for page in range(1, min(int(self.search_result_num / 10) + 2, self.page_num + 1)):
            if page == 1:
                _urls = self.match_urls(self.first_html)
                urls.extend(_urls)
                logger.info("baidu firsturl result {}".format(len(_urls)))
            else:
                time.sleep(self.default_interval)
                url = self.search_url.format(page=(page - 1) * 10, keyword=quote(self.keyword))
                html = utils.http_req(url, headers=self.headers).text
                _urls = self.match_urls(html)
                logger.info("baidu search url {}, result {}".format(url, len(_urls)))
                urls.extend(_urls)
        return urls


class BingSearch(object):
    def __init__(self, keyword=None, page_num=6):
        self.search_url = "https://cn.bing.com/search?q={keyword}&qs=n&form=QBRE&sp=-1&first={page}"
        self.num_pattern = re.compile(r'<span class="sb_count">([^<]+)</span>')
        self.pq_query = "#b_results > li h2 > a"
        self.keyword = keyword
        self.page_num = page_num
        self.headers = {"Accept-Language": "zh-cn"}
        self.default_interval = 3
        self.search_result_num = 0
        self.first_html = ""

    def result_num(self):
        url = self.search_url.format(page=1, keyword=quote(self.keyword))
        html = utils.http_req(url, headers=self.headers).text
        self.first_html = html
        result = re.findall(self.num_pattern, html)

        if result:
            # 第一种情况
            result_num = re.findall(r"共 ([\d,]*) 条", result[0])
            if result_num:
                num = int("".join(result_num[0].split(",")))
                self.search_result_num = num

            # 第二种情况
            else:
                result_num_2 = re.findall(r" ([\d,]*) 个结果", result[0])
                if result_num_2:
                    num = int("".join(result_num_2[0].split(",")))
                    self.search_result_num = num
        else:
            logger.warning("Unable to get bing search results， {}".format(self.keyword))
            return 0

        return self.search_result_num

    def match_urls(self, html):
        if "搜索</title>" not in html:
            raise Exception("获取Bing结果异常")

        dom = pq(html)
        result_items = dom(self.pq_query).items()
        urls_result = [item.attr("href") for item in result_items]
        urls = set()
        for u in urls_result:
            urls.add(u)
        return list(urls)

    def run(self):
        self.result_num()
        logger.info("bing search {} results found for keyword {}".format(self.search_result_num, self.keyword))
        urls = []

        # 没有找到直接return
        if self.search_result_num == 0:
            return urls

        for page in range(1, min(int(self.search_result_num / 10) + 2, self.page_num + 1)):
            if page == 1:
                _urls = self.match_urls(self.first_html)
                urls.extend(_urls)
                logger.info("bing search first url result {}".format(len(_urls)))
            else:
                time.sleep(self.default_interval)
                url = self.search_url.format(page=(page - 1) * 10, keyword=quote(self.keyword))
                html = utils.http_req(url, headers=self.headers).text
                _urls = self.match_urls(html)
                logger.info("bing search url {}, result {}".format(url, len(_urls)))
                urls.extend(_urls)
        return urls


def baidu_search(domain, page_num=6):
    keyword = "site:{}".format(domain)
    b = BaiduSearch(keyword, page_num)
    urls = b.run()
    urls = [u for u in urls if domain in urlparse(u).netloc]
    return utils.rm_similar_url(urls)


def bing_search(domain, page_num=5):
    urls = []
    keyword = "site:{}".format(domain)
    b = BingSearch(keyword, page_num)
    urls.extend(b.run())
    if b.search_result_num > 1000 and len(urls) > 25:
        keywords = ["admin", "管理|后台", "登陆|密码", "login", "manage", "dashboard", "api",
                    "console"]
        for k in keywords:
            keyword = "site:{} {}".format(domain, k)
            try:
                time.sleep(15)
                b = BingSearch(keyword, page_num=1)
                urls.extend(b.run())
            except Exception as e:
                logger.warning(e)
    urls = [u for u in urls if domain in urlparse(u).netloc]
    return utils.rm_similar_url(urls)


class SearchEngines(object):
    # *** 调用搜索引擎查找URL
    def __init__(self, base_domain):
        self.engines = [bing_search, baidu_search]
        self.base_domain = base_domain

    def run(self):
        urls = []
        for engine in self.engines:
            try:
                urls.extend(engine(self.base_domain))
                urls = utils.rm_similar_url(urls)
            except Exception as e:
                logger.exception(e)

        return urls


def search_engines(base_domain):
    s = SearchEngines(base_domain)
    return s.run()


if __name__ == '__main__':
    for x in baidu_search("qq.com", 6):
        print(x)
