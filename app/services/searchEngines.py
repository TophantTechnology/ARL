import re
from pyquery import PyQuery as pq
import time
from urllib.parse import quote, urljoin, urlparse
from app import utils

logger = utils.get_logger()


class BaiduSearch(object):
    def __init__(self, keyword=None, page_num=6):
        self.search_url = "https://www.baidu.com/s?rn=100&pn={page}&wd={keyword}"
        self.num_pattern = re.compile(r'百度为您找到相关结果约([\d,]*)个')
        self.first_html = ""
        self.keyword = keyword
        self.page_num = page_num
        self.pq_query = "#content_left h3.t a"
        self.search_result_num = 0
        self.default_interval = 3

    def result_num(self):
        url = self.search_url.format(page=0, keyword=quote(self.keyword))

        html = utils.http_req(url).text
        self.first_html = html
        result = re.findall(self.num_pattern, html)
        if not result:
            logger.warning("Unable to get baidu search results， {}".format(self.keyword))
            return 0

        num = int("".join(result[0].split(",")))
        self.search_result_num = num
        return num

    def match_urls(self, html):
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
        logger.info("BaiduSearch, sleep 5 on {}".format(self.keyword))
        time.sleep(5)

        self.result_num()
        logger.info("baidu search {} results found for keyword {}".format(self.search_result_num, self.keyword))
        urls = []
        for page in range(1, min(int(self.search_result_num / 10) + 2, self.page_num + 1)):
            if page == 1:
                _urls = self.match_urls(self.first_html)
                urls.extend(_urls)
                logger.info("baidu firsturl result {}".format(len(_urls)))
            else:
                time.sleep(self.default_interval)
                url = self.search_url.format(page=(page - 1) * 10, keyword=quote(self.keyword))
                html = utils.http_req(url).text
                _urls = self.match_urls(html)
                logger.info("baidu search url {}, result {}".format(url, len(_urls)))
                urls.extend(_urls)
        return urls


class BingSearch(object):
    def __init__(self, keyword=None, page_num=6):
        self.search_url = "https://cn.bing.com/search?q={keyword}&go=Search&qs=ds&form=QBRE&first={page}"
        self.num_pattern = re.compile(r'<span class="sb_count">([\d,]*) (results|条结果)</span>')
        self.pq_query = "#b_results > li h2 > a"
        self.keyword = keyword
        self.page_num = page_num
        self.cookies = {'_SS': '1'}
        self.default_interval = 3
        self.search_result_num = 0
        self.first_html = ""

    def result_num(self):
        num = 0
        url = self.search_url.format(page=1, keyword=quote(self.keyword))

        html = utils.http_req(url, cookies=self.cookies).text
        self.first_html = html
        result = re.findall(self.num_pattern, html)
        if result:
            num = int("".join(result[0][0].split(",")))
        self.search_result_num = num
        return num

    def match_urls(self, html):
        dom = pq(html)
        result_items = dom(self.pq_query).items()
        urls_result = [item.attr("href") for item in result_items]
        urls = set()
        for u in urls_result:
            urls.add(u)
        return list(urls)

    def run(self):
        logger.info("BingSearch, sleep 5 on {}".format(self.keyword))
        time.sleep(5)
        self.result_num()
        logger.info("bing search {} results found for keyword {}".format(self.search_result_num, self.keyword))
        urls = []
        for page in range(1, min(int(self.search_result_num / 10) + 2, self.page_num + 1)):
            if page == 1:
                _urls = self.match_urls(self.first_html)
                urls.extend(_urls)
                logger.info("bing search first url result {}".format(len(_urls)))
            else:
                time.sleep(self.default_interval)
                url = self.search_url.format(page=(page - 1) * 10, keyword=quote(self.keyword))
                html = utils.http_req(url, cookies=self.cookies).text
                _urls = self.match_urls(html)
                logger.info("bing search url {}, result {}".format(url, len(_urls)))
                urls.extend(_urls)
        return urls


class DogeSearch():
    def __init__(self, keyword=None, page_num=6):
        self.search_url = "https://dogedoge.com/results?q={keyword}&p={page}"
        self.num_pattern = re.compile(r'约 ([\d,]*) 条结果')
        self.pq_query = "h2.result__title a.result__a"
        self.keyword = keyword
        self.page_num = page_num
        self.base_search_url = 'https://www.dogedoge.com/'
        self.default_interval = 0.2
        self.search_result_num = 0

    def result_num(self):
        url = self.search_url.format(page=0, keyword=quote(self.keyword))
        #logger.info("search url {}".format(url))
        html = utils.http_req(url, allow_redirects=True).text
        self.first_html = html
        result = re.findall(self.num_pattern, html)
        if not result:
            return 0
        num = int("".join(result[0].strip().split(",")))
        self.search_result_num = num
        return num

    def match_urls(self, html):
        dom = pq(html)
        result_items = dom(self.pq_query).items()
        urls_result = [urljoin(self.base_search_url, item.attr("href")) for item in result_items]
        urls = set()
        if urls_result:
            for u in urls_result:
                try:
                    resp = utils.http_req(u, "head", allow_redirects=False, verify=False)
                    real_url = resp.headers.get('Location')
                    if real_url:
                        urls.add(real_url)
                except Exception as e:
                    continue
        return list(urls)

    def run(self):
        self.result_num()
        logger.info("doge search {} results found for keyword {}".format(self.search_result_num, self.keyword))
        urls = []
        for page in range(1, min(int(self.search_result_num / 10) + 2, self.page_num + 1)):
            if page == 1:
                _urls = self.match_urls(self.first_html)
                urls.extend(_urls)
                logger.info("doge search first url result {}".format(len(_urls) ))
            else:
                time.sleep(self.default_interval)
                url = self.search_url.format(page=page, keyword=quote(self.keyword))
                html = utils.http_req(url, allow_redirects=True).text
                _urls = self.match_urls(html)
                logger.info("doge search url {}, result {}".format(url, len(_urls)))
                urls.extend(_urls)
        return urls


def baidu_search(domain, page_num=6):
    keyword = "site:{}".format(domain)
    b = BaiduSearch(keyword, page_num)
    urls = b.run()
    urls = [u for u in urls if domain in urlparse(u).netloc]
    return utils.rm_similar_url(urls)


def bing_search(domain, page_num=6):
    urls = []
    keyword = "site:{}".format(domain)
    b = BingSearch(keyword, page_num)
    urls.extend(b.run())
    if b.search_result_num > 1000 and len(urls) > 30:
        keywords = ["admin", "管理", "后台", "登陆", "密码", "login", "manage", "env", "dashboard", "api",
                    "console"]
        for k in keywords:
            keyword = "site:{} {}".format(domain, k)
            try:
                b = BingSearch(keyword, page_num=1)
                urls.extend(b.run())
            except Exception as e:
                logger.warning(e)
    urls = [u for u in urls if domain in urlparse(u).netloc]
    return utils.rm_similar_url(urls)


def doge_search(domain, page_num=3):
    urls = []
    keyword = "site:{}".format(domain)
    b = DogeSearch(keyword, page_num=page_num)
    urls.extend(b.run())

    if b.search_result_num > 1000 and len(urls) > 30:
        _keyword = "intext:login|admin|manage|console|管理|后台|登陆|平台|用户名|密码|账号 | inurl:admin|login|manage|env|dashboard|api|console|system|管理|后台|登陆|平台"
        keyword = "site:{} {}".format(domain, _keyword)
        b = DogeSearch(keyword, page_num=1)
        urls.extend(b.run())
    urls = [u for u in urls if domain in urlparse(u).netloc]  # 包含过滤
    return utils.rm_similar_url(urls)


if __name__ == '__main__':
    for x in baidu_search("qq.com", 6):
        print(x)
