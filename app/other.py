# from app import celerytask
from app import services
from app import modules
import time
from app.config import Config
import json
from app import utils
from app.services import resolver_domain
from app.tasks import domain
import threading



semaphore = threading.Semaphore(6)


def work():
    out = services.mass_dns("baidu.com", ["www", "blog"])
    time.sleep(10)
    print(out)
    semaphore.release()


def mass_dns_brute():
    for x in range(20):
        semaphore.acquire()
        t1 = threading.Thread(target=work)
        t1.start()

        print(x)


def port_scan():
    out = services.port_scan(['10.0.86.169', '10.0.83.6', '10.0.83.16'], os_detect=True)

    for o in out:
        port_info_obj_list = []
        for port_info in o["port_info"]:
            port_info_obj_list.append(modules.PortInfo(**port_info))

        o["port_info"] = port_info_obj_list
        print(modules.IPInfo(**o))


def resolver():
    domains = ["www.baidu.com", "api.baike.baidu.com", "apollo.baidu.com", "www.baidu.com"]
    out = resolver_domain(domains)
    print(json.dumps(out))


with open(Config.DOMAIN_DICT_2W) as f:
    domain_2w = map(str.strip, f.readlines())


def domain_brue():
    out1 = domain.domain_brute("baidu.com")

    out2 = domain.domain_brute("baidu.com")

    print(len(out1))
    print(len(out2))
    diff21 = set(out2) - set(out1)
    diff12 = set(out2) - set(out1)
    print(diff21)
    print(diff12)


def find_site():
    domain_info_list = domain.domain_brute("baidu.com", word_file=Config.DOMAIN_DICT_TEST)
    option = {
        "ports": modules.ScanPortType.TOP1000,
        "service_detect": False,
        "os_detect": False
    }
    ip_info_list = domain.scan_port(domain_info_list, option)
    a = domain.find_site(ip_info_list)
    print(a)
    print(len(a))


def site_screenshot():
    sites = ["https://www.baidu.com",
             'https://www.dogedoge.com/results?q=%22docker+hub%22&a=1']
    services.site_screenshot(sites)


def fetch_site():
    site_info = services.fetch_site(["https://www.baidu.com/"])
    print(json.dumps(site_info))



def build_domain_info():
    t1 = time.time()
    d1 = ["dsf.freebuf.com","fdsf.freebuf.com","fsdf.freebuf.com","www.freebuf.com","www.freebuf.com","www.freebuf.com","www.freebuf.com","www.freebuf.com"]
    d2 = d1.copy() + d1.copy() + d1.copy() + d1.copy()

    services.build_domain_info(d2, concurrency=10)
    t2 = time.time()
    print(t2 - t1)



def check_domain_black():
    a = utils.check_domain_black("tcdnff.qq.com")
    print(a)
    b = utils.check_domain_black("test.tcdn.qq.com")
    print(b)

#check_domain_black()

def get_domains():
    url = "http://10.0.83.77:5018/domain/?task_id=5f2298aa6591e770f69e8f62&source=altdns&size=2000"
    data = utils.http_req(url).json()
    items = data["items"]
    domains = [x["domain"] for x in items]
    print(domains)
    return  services.probe_http(domains)



def domain_search_engines():
    from app.tasks import domain

    s = domain.SearchEngines(["https://www.genkisushi.co.jp/"])
    urls = s.run()
    return urls


def site_spider():
    items = ["https://www.qq.com/"]
    for item in items:
        urls = services.site_spider([item], 5)
        for x in urls:
            print(x)



def get_urls():
    url = "http://10.0.83.77:5018/site/?page=1&hostname=baidu.com&size=6000"
    data = utils.http_req(url).json()
    items = data["items"]
    urls = []
    print(len(items))
    for item in items:
        urls.append(item["site"])


    with open("../arl_tool/urls2.txt", "w") as f:
        for x in set(urls):
            f.write(x + "\n")


def web_app_identify1():
    site_info_list = services.fetch_site(["http://10.0.83.6:7001/"])
    for site_info in site_info_list:
        print(site_info)
        app = services.web_app_identify(site_info)
        print(app)

def web_app_identify():
    site_list = ["http://10.0.83.6:81/login.php"]
    site_info_list = services.fetch_site(site_list)
    web_analyze_map = {}
    for site_info in site_info_list:
        curr_site = site_info["site"]
        finger_list = [{'name': 'xxx', 'confidence': '80', 'version': '', 'icon': 'default.png', 'website': 'https://www.riskivy.com', 'categories': []}]

        site_info["finger"] = finger_list

        web_app_finger = services.web_app_identify(site_info)
        flag = False
        if web_app_finger and finger_list:
            for finger in finger_list:
                if finger["name"].lower() == web_app_finger["name"].lower():
                    flag = True
                    break

        if not flag and web_app_finger:
            finger_list.append(web_app_finger)

        print(site_info["finger"])


from bson import ObjectId
from datetime import datetime


def update_asset():
    tables = ["asset_site", "asset_domain", "asset_ip"]

    cnt = 1
    for table in tables:
        print("update {}".format(table))
        items = utils.conn_db(table).find({})
        for item in items:
            update_date = item["update_date"]
            save_date = item["save_date"]
            if isinstance(update_date, str):
                item["update_date"] = datetime.strptime(update_date, "%Y-%m-%d %H:%M:%S")

            if isinstance(save_date, str):
                item["save_date"] = datetime.strptime(save_date, "%Y-%m-%d %H:%M:%S")
            query = {"_id": item["_id"]}
            a = utils.conn_db(table).find_one_and_replace(query, item)
            if a:
                cnt += 1
            if cnt % 100 == 0:
                print(cnt)


