import time
import difflib
import requests
from urllib.parse import urlparse, urljoin
import re
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import sys
from tld import get_tld
import itertools
import argparse

class ObjectDict(dict):
    """Makes a dictionary behave like an object, with attribute-style access.
    """

    def __getattr__(self, name):
        # type: (str) -> any
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        # type: (str, any) -> None
        self[name] = value

UA = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"

def http_req(url, method = 'get', **kwargs):
    proxies = {
        'https': settings.proxy,
        'http': settings.proxy
    }

    kwargs.setdefault('verify', False)
    kwargs.setdefault('timeout', (10.1, 30.1))
    kwargs.setdefault('allow_redirects', False)

    headers = kwargs.get("headers", {})
    headers.setdefault("User-Agent", UA)

    kwargs["headers"] = headers

    if settings.proxy:
        kwargs["proxies"] = proxies

    conn = getattr(requests, method)(url, **kwargs)

    return conn


def logger(msg):
    print(msg)

def get_title(body):
    """
    根据页面源码返回标题
    :param body: <title>sss</title>
    :return: sss
    """
    result = ''
    title_patten = re.compile(rb'<title>([\s\S]{1,200})</title>', re.I)
    title = title_patten.findall(body)
    if len(title) > 0:
        try:
            result = title[0].decode("utf-8")
        except Exception as e:
            result = title[0].decode("gbk", errors="replace")
    return result




import threading
import collections
import  requests.exceptions

class BaseThread(object):
    def __init__(self, targets, concurrency=6):
        self.concurrency = concurrency
        self.semaphore = threading.Semaphore(concurrency)
        self.targets = targets

    def work(self, site):
        raise NotImplementedError()

    def _work(self, url):
        try:
            self.work(url)
        except requests.exceptions.RequestException as e:
            pass

        except BaseException as e:
            logger("error on {}".format(url))
            self.semaphore.release()
            raise e

        self.semaphore.release()

    def _run(self):
        deque = collections.deque(maxlen=2000)
        cnt = 0
        for target in self.targets:
            if isinstance(target, str):
                target = target.strip()

            cnt += 1
            logger("[{}/{}] work on {}".format(cnt, len(self.targets), target))

            if not target:
                continue

            self.semaphore.acquire()
            #self._work(target)
            t1 = threading.Thread(target=self._work, args=(target,))
            t1.start()

            deque.append(t1)

        for t in list(deque):
            while t.is_alive():
                time.sleep(0.2)




settings = ObjectDict()

settings.min_length = 100
settings.max_length = 50*1024
settings.read_timeout = 60
settings.bool_ratio = 0.8







class URL():
    def __init__(self, url, payload):
        self.url = url
        self.payload = payload
        self._scope = None
        self._path = None

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if isinstance(other, URL):
            return self.url == other.url
        else:
            return False

    def __hash__(self):
        return hash(self.url)


    def __str__(self):
        return self.url

    def __repr__(self):
        return "<URL> " + self.__str__()

    def __lt__(self, other):
        return self.url < other.url

    def __gt__(self, other):
        return self.url > other.url

    @property
    def scope(self) -> str:
        if self._scope is None:
            parse = urlparse(self.url)
            scope = "{}://{}".format(parse.scheme, parse.netloc)
            self._scope = scope

        return self._scope

    @property
    def path(self) -> str:
        if self._path is None:
            parse = urlparse(self.url)
            self._path = parse.path

        return self._path

class HTTPReq():
    def __init__(self, url: URL , read_timeout = 60, max_length = settings.max_length):
        self.url = url
        self.read_timeout = read_timeout
        self.max_length = max_length
        self.conn = None
        self.status_code = None
        self.content = None

    def req(self):
        content = b''
        conn = http_req(self.url.url, 'get', timeout=(3, 6), stream=True)
        self.conn = conn
        start_time = time.time()
        for data in conn.iter_content(chunk_size=512):
            if time.time() - start_time >= self.read_timeout:
                break
            content += data
            if len(content) >= int(self.max_length):
                break

        self.status_code = conn.status_code
        self.content = content[:self.max_length]

        content_len = self.conn.headers.get("Content-Length", len(self.content))
        self.conn.headers["Content-Length"] = content_len
        conn.close()

        return self.status_code, self.content




class Page():
    def __init__(self, req: HTTPReq):
        self.raw_req = req
        self.url = req.url
        self.content = req.content
        self.body_length = len(self.content)
        self.times = 0
        self.status_code = req.status_code
        self._title = None
        self._location_url = None
        self._is_back_up_path = None
        self._is_back_up_page = None
        self.back_up_suffix_list = [".tar", ".tar.gz", ".zip", ".rar", ".7z", ".bz2", ".gz", ".war"]

    def __eq__(self, other):
        if isinstance(other, Page):
            if self.status_code != other.status_code:
                return False

            if self.is_302() and other.is_302():
                self_new_url = self.location_url
                other_new_url = other.location_url

                self_new_url = urljoin(self.url.url, self_new_url)
                other_new_url = urljoin(other.url.url, other_new_url)

                if self_new_url.endswith(self.url.payload+ "/"):
                    if other_new_url.endswith(other.url.payload + "/"):
                        if not self.url.payload.endswith("/") and not other.url.payload.endswith("/"):
                            return False

                self_new_path = urlparse(self_new_url).path
                other_new_path = urlparse(other_new_url).path

                path1 = self_new_path.replace(self.url.payload, "$AAAA$")
                path2 = other_new_path.replace(other.url.payload, "$AAAA$")

                if urlparse(self_new_url).netloc == urlparse(other_new_url).netloc:
                    if path1 == path2 and self_new_path.endswith("$AAAA$/"):
                        if not self.url.payload.endswith("/") and not other.url.payload.endswith("/"):
                            return False

                if path1 == path2:
                    self.times += 1
                    return True
                else:
                    return False

            self_content = self.content.replace(self.url.payload.encode(), b"")
            other_content = other.content.replace(other.url.payload.encode(), b"")

            if abs(len(self_content) - len(other_content)) <= 5:
                self.times += 1
                return True

            min_len_content = min(len(self_content),  len(other_content))
            if abs(len(self_content) - len(other_content)) >= max(500, int(min_len_content*0.1)):
                return False

            if len(self.title) > 2 and self.title == other.title:
                return True

            quick_ratio = difflib.SequenceMatcher(None, self_content, other_content).quick_ratio()
            if quick_ratio >= settings.bool_ratio:
                self.times +=1
                return True
            else:
                return False

        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        p = urlparse(self.url.url)
        return hash(p.scheme + "://" + p.netloc)

    @property
    def location_url(self) -> str:
        if self._location_url is None:
            location = self.raw_req.conn.headers.get("Location", "")
            new_url = urljoin(self.url.url, location)
            self._location_url =  new_url.split("?")[0]

        return self._location_url

    def is_302(self):
        return self.status_code in [301, 302, 307, 308]


    @property
    def title(self) -> str:
        if self._title is None:
            self._title = get_title(self.content).strip()

        return self._title

    @property
    def is_backup_path(self) -> bool:
        if self._is_back_up_path is None:
            for suffix in self.back_up_suffix_list:
                if self.url.path.endswith(suffix):
                    self._is_back_up_path = True
                    return self._is_back_up_path

            self._is_back_up_path = False

        return self._is_back_up_path

    @property
    def is_backup_page(self) -> bool:
        if self._is_back_up_page is None:
            content_type = self.raw_req.conn.headers.get("Content-Type", "")
            if "application" in content_type.lower():
                self._is_back_up_page = True
            else:
                self._is_back_up_page = False

        return self._is_back_up_page


    def __str__(self):
        msg = "[{}][{}][{}]{}".format(self.status_code, self.title, len(self.content), self.url)
        return msg

    def __repr__(self):
        return "<Page> "+ self.__str__()





class FileLeak(BaseThread):
    def __init__(self, target, urls, concurrency=8):
        super().__init__(urls, concurrency = concurrency)
        self.target = target.rstrip("/") + "/"
        self.urls = urls
        self.path_404 = "not_found_2222_111"
        self.page404_set = set()
        self.page200_set = set()
        self.page200_code_list = [200, 301, 302, 500]
        self.page404_title = ["404", "不存在", "错误", "403", "禁止访问", "请求含有不合法的参数"]
        self.page404_title.extend(["网络防火墙", "访问拦截", "由于安全原因JSP功能默认关闭"])
        self.page404_content = [b'<script>document.getElementById("a-link").click();</script>']
        self.location404 = ["/auth/login/", "error.html"]
        self.page_all = []
        self.error_times = 0
        self.record_page = False
        self.skip_302 = False
        self.location_404_url = set()

    def work(self, url):
        if self.error_times >= 20:
            return
        req = self.http_req(url)
        page = Page(req)


        if self.record_page:
            self.page_all.append(page)

        if self.is_404_page(page):
            self.page404_set.add(page)
            return

        if page not in self.page404_set:
            self.page200_set.add(page)


    def build_404_page(self):
        url_404 = URL(self.target + self.path_404, self.path_404)
        logger("req => {}".format(url_404))
        page_404 = Page(self.http_req(url_404))
        self.page404_set.add(page_404)
        if self.record_page:
            self.page_all.append(page_404)

        if page_404.is_302():
            self.location_404_url.add(page_404.location_url)

        if page_404.is_302() and page_404.location_url.endswith(page_404.url.payload + "/"):
            self.skip_302 = True

    def run(self):
        t1 = time.time()
        logger("start fileleak {}".format(len(self.targets)))

        self.build_404_page()

        self._run()

        self.check_page_200()

        elapse = time.time() - t1
        logger("end fileleak elapse {}".format(elapse))

        return self.page200_set

    def http_req(self, url: URL):
        try:
            req = HTTPReq(url)
            req.req()
            return req
        except Exception as e:
            logger("error on {}".format(e))
            self.error_times += 1
            raise e



    def is_404_page(self, page: Page):
        if page.status_code not in self.page200_code_list:
            return True

        if page.is_backup_path:
            if not page.is_backup_page:
                return True

        for title in self.page404_title:
            if title in page.title:
                return True

        for content in self.page404_content:
            if content in page.content:
                return True

        if "/." in page.url.url and page.status_code == 200:
            if len(page.content) == 0:
                return True

        if page.is_302():
            for location_404 in self.location404:
                if location_404 in page.location_url:
                    return True

            if not page.location_url.endswith(page.url.payload + "/"):
                self.location_404_url.add(page.location_url)
                return True

            return page.location_url in self.location_404_url

        return False

    def check_page_200(self):
        for page in self.page200_set:
            if page in self.page404_set:
                continue

            if self.skip_302:
                self.page404_set.add(page)
                continue

            url_404_list = self.gen_check_url(page.url)

            for url_404 in url_404_list:
                page_404 = Page(self.http_req(url_404))
                self.page404_set.add(page_404)

                if page_404.is_302() and page_404.location_url.endswith(page_404.url.payload + "/"):
                    self.page404_set.add(page)
                    self.skip_302 = True

        self.page200_set -= self.page404_set


    def gen_check_url(self, url: URL):
        payload = url.payload
        if url.path in url.scope:
            check_url = url.url + "1337"
        else:
            check_url = url.url.replace(url.path, url.path + "1337")
        end_check_url = URL(check_url, payload + "1337")

        payload_list = ["..", "?", "etc/passwd"]
        for p in payload_list:
            if p in payload:
                check_url = url.url.replace(p, p + "a1337")
                payload = payload.replace(p, p + "a1337")
                return [URL(check_url, payload)]

        if "." in url.path and "." in payload:
            path = url.path.replace(".", "a1337.")
            check_url = "{}{}".format(url.scope, path)
            payload = payload.replace(".", "a1337.")
            return [URL(check_url, payload), end_check_url]

        if url.path.endswith("/"):
            path = url.path[:-1] + "a1337/"
            check_url = "{}{}".format(url.scope, path)
            payload = payload + "a1337/"
            return [URL(check_url, payload)]

        return [end_check_url]

def normal_url(url):
    scheme_map = {
        'http': 80,
        "https": 443
    }
    o = urlparse(url)

    scheme = o.scheme
    hostname = o.hostname
    path = o.path

    if scheme not in scheme_map:
        return ""

    if o.path == "":
        path = "/"


    if o.port == scheme_map[o.scheme] or o.port is None:
        ret_url = "{}://{}{}".format(scheme, hostname, path)

    else:
        ret_url = "{}://{}:{}{}".format(scheme, hostname, o.port, path)

    if o.query:
        ret_url = ret_url + "?" + o.query

    return ret_url


import os




class GenBackDicts:
    def __init__(self, url):
        self.target = normal_url(url)
        self.suffixs = [".tar", ".tar.gz", ".zip", ".rar", ".7z", ".bz2", ".gz", "_bak.rar", ".war"]
        self.backup_path_deep = 7
        self.dymaic_dicts_deep = 5
        self.path = urlparse(self.target).path


    def gen_dict_from_domain(self):
        result = []
        res = get_tld(self.target, as_object=True, fail_silently=True)
        if res:
            result = [x for x in [str(res.parsed_url.netloc).split(":")[0], res.fld, res.subdomain,
                                 res.domain] + res.subdomain.split(".") if x != ""]

        return set(result)

    def gen_backup_dicts(self, nemes):
        out = []
        items = itertools.product(nemes, self.suffixs)
        for x in items:
            out.append("".join(x))
        return out

    def gen_dict_from_path(self):
        out = []
        dirs = os.path.dirname(self.path).split("/")
        if len(dirs)> 1 and dirs[-1]:
            out = self.gen_backup_dicts([dirs[-1]])
        return out


    def gen(self):
        ret = set()
        names = self.gen_dict_from_domain()

        for x in  self.gen_backup_dicts(names):
            ret.add(URL(urljoin(self.target, x), x))

        for x in  self.gen_dict_from_path():
            ret.add(URL(urljoin(self.target, x), x))
            ret.add(URL(urljoin(self.target, "./../"+ x), x))

        return ret


class GenURL():
    def __init__(self, target, dicts):
        self.target = normal_url(target).split("?")[0]
        self.dicts = set(dicts)
        self.urls = set()

    def build_urls(self):
        target = os.path.dirname(self.target)
        for d in self.dicts:
            u = URL("{}/{}".format(target, d.strip()), d.strip())
            self.urls.add(u)

    def gen(self, flag = True):
        if urlparse(self.target).path == "/":
            self.dicts |= GenBackDicts(self.target).gen_dict_from_domain()

        self.build_urls()
        if flag:
            self.urls |=  GenBackDicts(self.target).gen()

        return self.urls


def load_file(path):
    with open(path, "r+") as f:
        return f.readlines()



def file_leak(targets, dicts):
    all_gen_url = set()
    map_url = dict()
    for site in targets:
        site = normal_url(site.strip())
        if not site:
            continue

        map_url[URL(site, "").scope] = set()
        a = GenURL(site, dicts)
        all_gen_url |= a.gen(settings.gen_dict)

    for url in all_gen_url:
        map_url[url.scope].add(url)

    cnt = 0
    total = len(map_url)
    for target in map_url:
        cnt += 1
        print("file leak => [{}/{}] {}".format(cnt, total, target))
        try:
            f = FileLeak(target, map_url[target], settings.concurrency_count)
            pages = f.run()
            with open(settings.output, "a") as f:
                for page in pages:
                    logger("found => {}".format(page))
                    f.write("{}\n".format(page))

        except Exception as e:
            logger("error on {}".format(e))

class ArgumentDefaultsHelpFormatter(argparse.HelpFormatter):
    """Help message formatter which adds default values to argument help.

    Only the name of this class is considered a public API. All the methods
    provided by the class are considered an implementation detail.
    """

    def _get_help_string(self, action):
        help = action.help
        if '%(default)' not in action.help:
            if action.default is not argparse.SUPPRESS:
                defaulting_nargs = [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    if action.default is not None:
                        help += ' (default: %(default)s)'
        return help




def test_main():
    dicts = load_file(settings.dict)
    file_leak([settings.target], dicts)

def work_file():
    dicts = load_file(settings.dict)
    targets = load_file(settings.target)
    file_leak(targets, dicts)


if __name__ == '__main__':  # pragma: no cover

    parser = argparse.ArgumentParser(prog="fileleak",
                                     formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument('--version', '-V', action='version', version='%(prog)s 2.1')

    parser.add_argument('--target',
                        '-t',
                        help='目标文件或者URL',
                        required=True)

    parser.add_argument('--dict',
                        '-d',
                        default='dicts/mid.txt',
                        help='自定义字典路径',
                        required=False)

    parser.add_argument('--output',
                        '-o',
                        default='succ.txt',
                        help='输出文件',
                        required=False)

    parser.add_argument('--gen-dict',
                        action='store_true',
                        default=False)

    parser.add_argument('--concurrency-count',
                        '-c',
                        default=8,
                        type=int,
                        help='并发请求数量')

    parser.add_argument('--bool-ratio',
                        default=0.8,
                        type=float,
                        help='页面相似度阈值')

    parser.add_argument('--proxy',
                        "-x",
                        help='代理地址')

    args = parser.parse_args()

    settings.target = args.target
    settings.dict = args.dict
    settings.gen_dict = args.gen_dict
    settings.bool_ratio = args.bool_ratio
    settings.concurrency_count = args.concurrency_count
    settings.output = args.output
    settings.proxy = args.proxy

    t1 = time.time()

    if "://" in settings.target:
        test_main()
    else:
        work_file()

    print(time.time() - t1)




