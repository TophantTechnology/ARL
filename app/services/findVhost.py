import json
from app.utils import get_title, http_req, get_logger
from .baseThread import BaseThread, thread_map
from requests.exceptions import ConnectTimeout, ReadTimeout
import difflib

logger = get_logger()

bool_ratio = 0.9


class Page(object):
    def __init__(self, url, domain, content, status_code, content_type):
        self.url = url
        self.domain = domain
        self.content = content
        self.body_length = len(content)
        self.status_code = status_code
        self.title = get_title(self.content)
        self.content_type = content_type.lower()

    def __eq__(self, other):
        if isinstance(other, Page):
            if self.status_code != other.status_code:
                return False

            if self.content_type != other.content_type:
                return False

            if abs(self.body_length - other.body_length) > 20:
                return False

            if abs(len(self.title) - len(self.title)) >= 3:
                return False

            if self.status_code == 200 and abs(self.body_length - other.body_length) <= 3:
                return True

            quick_ratio = difflib.SequenceMatcher(None, self.content, other.content).quick_ratio()
            return quick_ratio > bool_ratio
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return "<Page>{}-----{}".format(self.url, self.domain)

    def __hash__(self):
        return hash(self.url)

    def dump_json(self):
        item = {
            "url": self.url,
            "domain": self.domain,
            "body_length": self.body_length,
            "title": self.title,
            "status_code": self.status_code
        }
        return json.dumps(item, ensure_ascii=False)

    def dump_json_obj(self):
        item = {
            "url": self.url,
            "domain": self.domain,
            "body_length": self.body_length,
            "title": self.title,
            "status_code": self.status_code
        }
        return item


class BruteVhost(BaseThread):
    def __init__(self, ip, domains, scheme, concurrency=6):
        super(BruteVhost, self).__init__(targets=domains, concurrency=concurrency)
        self.ip = ip
        self.scheme = scheme
        self.url_ip = "{}://{}".format(self.scheme, self.ip)
        self.domains = domains
        self.not_found_set = set()
        self.success_set = set()
        self.cnt = 0
        self.total_cnt = len(self.domains)
        self.error_cnt = 0
        self.print_skip_warning_flag = False

    def brute_domain(self, domain):
        try:
            headers = {
                "Host": "{}".format(domain)
            }
            res = http_req(self.url_ip, headers=headers, timeout=(3, 6))
            content = res.content.replace(domain.encode(), b"")
            res_type = res.headers.get("Content-Type", "")
            page = Page(url=self.url_ip, domain=domain, content=content,
                        status_code=res.status_code, content_type=res_type)
            return page
        except Exception as e:
            logger.debug("{} {} {}".format(self.url_ip, domain, str(e)))
            if isinstance(e, (ConnectTimeout, ReadTimeout)):
                self.error_cnt += 1

    def work(self, domain):
        if self.error_cnt >= 10:
            if not self.print_skip_warning_flag:
                logger.warning("skip {}".format(self.url_ip))

            self.print_skip_warning_flag = True
            return

        self.cnt += 1
        if self.cnt % 20 == 1:
            logger.debug("[{}/{}] >>> {} {}".format(
                self.cnt, self.total_cnt,
                self.url_ip, domain))

        page = self.brute_domain(domain)
        if not page:
            return

        # 针对性处理下
        if '百度一下' in page.title:
            return

        if page.status_code not in [301, 302, 200]:
            return

        if "json" not in page.content_type and "text" not in page.content_type:
            return

        if "text" in page.content_type and page.body_length < 150:
            return

        if "text" in page.content_type and b"<" not in page.content:
            return

        if page in self.not_found_set:
            return

        if page not in self.success_set:
            success = page.dump_json()
            logger.success("found {}".format(success))
            self.success_set.add(page)

    def run(self):
        domain_404_list = [self.ip, "not123abc" + self.domains[0], "wfaz.zljhaz.com", "n0ta." + self.domains[0]]
        logger.debug(">> build 404 page {}://{}".format(self.scheme, self.ip))
        for item in domain_404_list:
            page = self.brute_domain(item)
            if page:
                self.not_found_set.add(page)
        self._run()

        if len(self.success_set) > 0:
            logger.info("found {} {}".format(self.url_ip, len(self.success_set)))

        return self.success_set


def brute_vhost(ip, args):
    domains, scheme = args
    logger.info("brute_vhost >>> ip: {}, domain: {}, scheme: {}".format(ip, len(domains), scheme))
    brute = BruteVhost(ip=ip, domains=domains, scheme=scheme,
                       concurrency=8)
    return brute.run()


def find_vhost(ips, domains):
    target_scheme = ["http", "https"]
    results = []
    same_set = set()

    for scheme in target_scheme:
        result_map = thread_map(brute_vhost, items=ips, arg=(domains, scheme), concurrency=3)
        for ip in result_map:
            page_set = result_map[ip]
            for page in page_set:
                # 添加全局的去重逻辑，屏蔽CDN等原因
                key = "{}-{}-{}".format(page.domain, page.title, page.status_code)
                if key in same_set:
                    continue

                same_set.add(key)
                results.append(page.dump_json_obj())

    return results





