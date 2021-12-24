import time
from pyquery import PyQuery as pq
import binascii
from urllib.parse import urljoin, urlparse
from urllib3.util.url import get_host
import mmh3
from app import utils
from .baseThread import BaseThread
logger = utils.get_logger()
from .autoTag import auto_tag
from app.utils import http_req
from app.utils.fingerprint import load_fingerprint, fetch_fingerprint


class FetchSite(BaseThread):
    def __init__(self, sites, concurrency=6, http_timeout=None):
        super().__init__(sites, concurrency)
        self.site_info_list = []
        self.fingerprint_list = load_fingerprint()
        self.http_timeout = http_timeout
        if http_timeout is None:
            self.http_timeout = (10.1, 30.1)

    def fetch_fingerprint(self, item, content):
        favicon_hash = item["favicon"].get("hash", 0)
        result = fetch_fingerprint(content=content, headers=item["headers"],
                                   title=item["title"], favicon_hash=favicon_hash,
                                   finger_list=self.fingerprint_list)

        finger = []
        for name in result:
            finger_item = {
                "icon": "default.png",
                "name": name,
                "confidence": "80",
                "version": "",
                "website": "https://www.riskivy.com",
                "categories": []
            }
            finger.append(finger_item)

        if finger:
            item["finger"] = finger

    def work(self, site):
        _, hostname, _ = get_host(site)

        conn = utils.http_req(site, timeout=self.http_timeout)
        item = {
            "site": site,
            "hostname": hostname,
            "ip": "",
            "title": utils.get_title(conn.content),
            "status": conn.status_code,
            "headers": utils.get_headers(conn),
            "http_server":  conn.headers.get("Server", ""),
            "body_length": len(conn.content),
            "finger": [],
            "favicon": fetch_favicon(site)
        }

        self.fetch_fingerprint(item, content=conn.content)
        domain_parsed = utils.domain_parsed(hostname)
        if domain_parsed:
            item["fld"] = domain_parsed["fld"]
            ips = utils.get_ip(hostname)
            if ips:
                item["ip"] = ips[0]
        else:
            item["ip"] = hostname

        self.site_info_list.append(item)
        if conn.status_code == 301 or conn.status_code == 302:
            url_302 = urljoin(site, conn.headers.get("Location", ""))
            if url_302 != site and url_302.startswith(site):
                site_path = urlparse(site).path.strip("/")
                url_302_path = urlparse(url_302).path
                if len(site_path) > 5 and url_302_path.endswith(site_path):
                    return
                self.work(url_302)

    def run(self):
        t1 = time.time()
        logger.info("start fetch site {}".format(len(self.targets)))
        self._run()
        elapse = time.time() - t1
        logger.info("end fetch site elapse {}".format(elapse))

        # 对站点信息自动打标签
        auto_tag(self.site_info_list)

        return self.site_info_list


def fetch_favicon(url):
    f = FetchFavicon(url)
    return f.run()


def fetch_site(sites, concurrency=15, http_timeout=None):
    f = FetchSite(sites, concurrency=concurrency, http_timeout=http_timeout)
    return f.run()


class FetchFavicon(object):
    def __init__(self, url):
        self.url = url
        self.favicon_url = None
        pass

    def build_result(self, data):
        result = {
            "data": data,
            "url": self.favicon_url,
            "hash": mmh3.hash(data)
        }
        return result

    def run(self):
        result = {}
        try:
            favicon_url = urljoin(self.url, "/favicon.ico")
            data = self.get_favicon_data(favicon_url)
            if data:
                self.favicon_url = favicon_url
                return self.build_result(data)

            favicon_url = self.find_icon_url_from_html()
            if not favicon_url:
                return result
            data = self.get_favicon_data(favicon_url)
            if data:
                self.favicon_url = favicon_url
                return self.build_result(data)

        except Exception as e:
            logger.warning("error on {} {}".format(self.url, e))

        return result

    def get_favicon_data(self, favicon_url):
        conn = http_req(favicon_url)
        if conn.status_code != 200:
            return

        if len(conn.content) <= 80:
            logger.debug("favicon content len lt 100")
            return

        if "image" in conn.headers.get("Content-Type", ""):
            data = self.encode_bas64_lines(conn.content)
            return data

    def encode_bas64_lines(self, s):
        """Encode a string into multiple lines of base-64 data."""
        MAXLINESIZE = 76  # Excluding the CRLF
        MAXBINSIZE = (MAXLINESIZE // 4) * 3
        pieces = []
        for i in range(0, len(s), MAXBINSIZE):
            chunk = s[i: i + MAXBINSIZE]
            pieces.append(bytes.decode(binascii.b2a_base64(chunk)))
        return "".join(pieces)

    def find_icon_url_from_html(self):
        conn = http_req(self.url)
        if b"<link" not in conn.content:
            return
        d = pq(conn.content)
        links = d('link').items()
        icon_link_list = []
        for link in links:
            if link.attr("href") and 'icon' in link.attr("rel"):
                icon_link_list.append(link)

        for link in icon_link_list:
            if "shortcut" in link:
                return urljoin(self.url, link.attr('href'))

        if icon_link_list:
            return urljoin(self.url, icon_link_list[0].attr('href'))

