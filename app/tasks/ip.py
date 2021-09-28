from bson.objectid import  ObjectId
import time
from app import services
from app.modules import ScanPortType, TaskStatus, CollectSource
from app.services import fetchCert, run_risk_cruising, run_sniffer
from app import utils
from app.services.commonTask import CommonTask
from app.config import Config


logger = utils.get_logger()


def ssl_cert(ip_info_list):
    try:
        targets = []
        for ip_info in ip_info_list:
            for port_info in ip_info["port_info"]:
                if port_info["port_id"] == 80:
                    continue
                targets.append("{}:{}".format(ip_info["ip"], port_info["port_id"]))

        f = fetchCert.SSLCert(targets)
        return f.run()
    except Exception as e:
        logger.exception(e)

    return {}


class IPTask(CommonTask):
    def __init__(self, ip_target=None, task_id=None, options=None):
        super().__init__(task_id=task_id)

        self.ip_target = ip_target
        self.task_id = task_id
        self.options = options
        self.ip_info_list = []
        self.ip_set = set()
        self.site_list = []
        self.site_302_list = []
        self.web_analyze_map = {}
        self.cert_map = {}
        self.service_info_list = []
        self.npoc_service_target_set = set()
        # 用来区分是正常任务还是监控任务
        self.task_tag = "task"

        self.scope_id = None
        self.task_name = None
        self.asset_ip_port_set = set()
        self.asset_ip_info_map = dict()

    def set_asset_ip(self):
        """
        用来获取Asset_IP 中的信息，仅仅在监控阶段使用
        """
        raise NotImplementedError()

    def async_ip_info(self):
        """
        用来同步发现的 ip 中的信息，仅仅在监控阶段使用
        """
        raise NotImplementedError()

    def async_site_info(self, site_info_list):
        """
        用来同步发现的 site 中的信息，仅仅在监控阶段使用
        """
        raise NotImplementedError()

    def port_scan(self):
        scan_port_map = {
            "test": ScanPortType.TEST,
            "top100": ScanPortType.TOP100,
            "top1000": ScanPortType.TOP1000,
            "all": ScanPortType.ALL,
            "custom": self.options.get("port_custom", "80,443")
        }
        option_scan_port_type = self.options.get("port_scan_type", "test")
        scan_port_option = {
            "ports": scan_port_map.get(option_scan_port_type, ScanPortType.TEST),
            "service_detect": self.options.get("service_detection", False),
            "os_detect": self.options.get("os_detection", False),
            "port_parallelism": self.options.get("port_parallelism", 32),  # 探测报文并行度
            "port_min_rate": self.options.get("port_min_rate", 64),  # 最少发包速率
            "custom_host_timeout": None  # 主机超时时间(s)
        }
        # 只有当设置为自定义时才会去设置超时时间
        if self.options.get("host_timeout_type") == "custom":
            scan_port_option["custom_host_timeout"] = self.options.get("host_timeout", 60 * 15)

        targets = self.ip_target.split()
        ip_port_result = services.port_scan(targets, **scan_port_option)
        self.ip_info_list.extend(ip_port_result)

        if self.task_tag == 'monitor':
            self.set_asset_ip()

        for ip_info in ip_port_result:
            curr_ip = ip_info["ip"]
            self.ip_set.add(curr_ip)
            if not utils.not_in_black_ips(curr_ip):
                continue

            ip_info["task_id"] = self.task_id
            ip_info["ip_type"] = utils.get_ip_type(curr_ip)
            ip_info["geo_asn"] = {}
            ip_info["geo_city"] = {}

            if ip_info["ip_type"] == "PUBLIC":
                ip_info["geo_asn"] = utils.get_ip_asn(curr_ip)
                ip_info["geo_city"] = utils.get_ip_city(curr_ip)

            # 仅仅资产发现任务将IP全部存储起来
            if self.task_tag == 'task':
                utils.conn_db('ip').insert_one(ip_info)

        # 监控任务同步IP信息
        if self.task_tag == 'monitor':
            self.async_ip_info()

    def find_site(self):
        url_temp_list = []
        for ip_info in self.ip_info_list:
            for port_info in ip_info["port_info"]:
                curr_ip = ip_info["ip"]
                port_id = port_info["port_id"]
                if port_id == 80:
                    url_temp = "http://{}".format(curr_ip)
                    url_temp_list.append(url_temp)
                    continue

                if port_id == 443:
                    url_temp = "https://{}".format(curr_ip)
                    url_temp_list.append(url_temp)
                    continue

                url_temp1 = "http://{}:{}".format(curr_ip, port_id)
                url_temp2 = "https://{}:{}".format(curr_ip, port_id)
                url_temp_list.append(url_temp1)
                url_temp_list.append(url_temp2)

        check_map = services.check_http(url_temp_list)

        # 去除https和http相同的
        alive_site = []
        for x in check_map:
            if x.startswith("https://"):
                alive_site.append(x)

            elif x.startswith("http://"):
                x_temp = "https://" + x[7:]
                if x_temp not in check_map:
                    alive_site.append(x)

        self.site_list.extend(alive_site)

    def fetch_site(self):
        site_info_list = services.fetch_site(self.site_list)

        for site_info in site_info_list:
            curr_site = site_info["site"]
            if curr_site not in self.site_list:
                self.site_302_list.append(curr_site)
            site_path = "/image/" + self.task_id
            file_name = '{}/{}.jpg'.format(site_path, utils.gen_filename(curr_site))
            site_info["task_id"] = self.task_id
            site_info["screenshot"] = file_name

            # 调用读取站点识别的结果，并且去重
            if self.web_analyze_map:
                finger_list = self.web_analyze_map.get(curr_site, [])
                known_finger_set = set()
                for finger_item in site_info["finger"]:
                    known_finger_set.add(finger_item["name"].lower())

                for analyze_finger in finger_list:
                    analyze_name = analyze_finger["name"].lower()
                    if analyze_name not in known_finger_set:
                        site_info["finger"].append(analyze_finger)

            utils.conn_db('site').insert_one(site_info)

        if self.task_tag == 'monitor':
            self.async_site_info(site_info_list)

    def site_screenshot(self):
        '''***站点截图***'''
        capture_sites = self.site_list + self.site_302_list
        capture_save_dir = Config.SCREENSHOT_DIR + "/" + self.task_id
        services.site_screenshot(capture_sites, concurrency=6, capture_dir=capture_save_dir)


    def update_services(self, services, elapsed):
        elapsed = "{:.2f}".format(elapsed)
        self.update_task_field("status", services)
        query = {"_id": ObjectId(self.task_id)}
        update = {"$push": {"service": {"name": services, "elapsed": float(elapsed)}}}
        utils.conn_db('task').update_one(query, update)

    def update_task_field(self, field = None, value = None):
        query = {"_id": ObjectId(self.task_id)}
        update = {"$set": {field: value}}
        utils.conn_db('task').update_one(query, update)

    def site_identify(self):
        self.web_analyze_map = services.web_analyze(self.site_list)

    def ssl_cert(self):
        if self.options.get("port_scan"):
            self.cert_map = ssl_cert(self.ip_info_list)
        else:
            self.cert_map = ssl_cert(self.ip_set)

        for target in self.cert_map:
            if ":" not in target:
                continue
            ip = target.split(":")[0]
            port = int(target.split(":")[1])
            item = {
                "ip": ip,
                "port": port,
                "cert": self.cert_map[target],
                "task_id": self.task_id,
            }
            utils.conn_db('cert').insert_one(item)

    def save_service_info(self):
        self.service_info_list = []
        services_list = set()
        for _data in self.ip_info_list:
            port_info_lsit = _data.get("port_info")
            for _info in port_info_lsit:
                if _info.get("service_name"):
                    if _info.get("service_name") not in services_list:
                        _result = {}
                        _result["service_name"] = _info.get("service_name")
                        _result["service_info"] = []
                        _result["service_info"].append({'ip': _data.get("ip"),
                                                        'port_id': _info.get("port_id"),
                                                        'product': _info.get("product"),
                                                        'version': _info.get("version")})
                        _result["task_id"] = self.task_id
                        self.service_info_list.append(_result)
                        services_list.add(_info.get("service_name"))
                    else:
                        for service_info in self.service_info_list:
                            if service_info.get("service_name") == _info.get("service_name"):
                                service_info['service_info'].append({'ip': _data.get("ip"),
                                                                    'port_id': _info.get("port_id"),
                                                                    'product': _info.get("product"),
                                                                    'version': _info.get("version")})
        if self.service_info_list:
            utils.conn_db('service').insert(self.service_info_list)


    def file_leak(self):
        for site in self.site_list:
            pages = services.file_leak([site], utils.load_file(Config.FILE_LEAK_TOP_2k))
            for page in pages:
                item = page.dump_json()
                item["task_id"] = self.task_id
                item["site"] = site

                utils.conn_db('fileleak').insert_one(item)

    def risk_cruising(self):
        """运行PoC任务"""
        poc_config = self.options.get("poc_config", [])
        plugins = []
        for info in poc_config:
            if not info.get("enable"):
                continue
            plugins.append(info["plugin_name"])

        result = run_risk_cruising(plugins=plugins, targets=self.site_list)
        for item in result:
            item["task_id"] = self.task_id
            item["save_date"] = utils.curr_date()
            utils.conn_db('vuln').insert_one(item)

    def npoc_service_detection(self):
        targets = []
        for ip_info in self.ip_info_list:
            for port_info in ip_info["port_info"]:
                skip_port_list = [80, 443, 843]
                if port_info["port_id"] in skip_port_list:
                    continue

                targets.append("{}:{}".format(ip_info["ip"], port_info["port_id"]))

        result = run_sniffer(targets)
        for item in result:
            self.npoc_service_target_set.add(item["target"])
            item["task_id"] = self.task_id
            item["save_date"] = utils.curr_date()
            utils.conn_db('npoc_service').insert_one(item)

    def site_spider(self):
        entry_urls_list = []
        for site in self.site_list:
            entry_urls_list.append([site])

        site_spider_result = services.site_spider_thread(entry_urls_list)
        for site in site_spider_result:
            target_urls = []
            target_urls.extend(site_spider_result[site])

            if not target_urls:
                continue

            page_map = services.page_fetch(target_urls)
            for url in page_map:
                item = {
                    "site": site,
                    "task_id": self.task_id,
                    "source": CollectSource.SITESPIDER
                }
                item.update(page_map[url])

                utils.conn_db('url').insert_one(item)

    def brute_config(self):
        plugins = []
        brute_config = self.options.get("brute_config")
        for x in brute_config:
            if not x.get("enable"):
                continue
            plugins.append(x["plugin_name"])

        if not plugins:
            return
        targets = self.site_list.copy()
        targets += list(self.npoc_service_target_set)
        result = run_risk_cruising(targets=targets, plugins=plugins)
        for item in result:
            item["task_id"] = self.task_id
            item["save_date"] = utils.curr_date()
            utils.conn_db('vuln').insert_one(item)

    def run(self):
        self.update_task_field("start_time", utils.curr_date())
        '''***端口扫描开始***'''
        if self.options.get("port_scan"):
            self.update_task_field("status", "port_scan")
            t1 = time.time()
            self.port_scan()
            elapse = time.time() - t1
            self.update_services("port_scan", elapse)

        # 存储服务信息
        if self.options.get("service_detection"):
            self.save_service_info()

        '''***证书获取开始***'''
        if self.options.get("ssl_cert"):
            self.update_task_field("status", "ssl_cert")
            t1 = time.time()
            self.ssl_cert()
            elapse = time.time() - t1
            self.update_services("ssl_cert", elapse)

        self.update_task_field("status", "find_site")
        t1 = time.time()
        self.find_site()
        elapse = time.time() - t1
        self.update_services("find_site", elapse)

        '''***站点识别***'''
        if self.options.get("site_identify"):
            self.update_task_field("status", "site_identify")
            t1 = time.time()
            self.site_identify()
            elapse = time.time() - t1
            self.update_services("site_identify", elapse)


        self.update_task_field("status", "fetch_site")
        t1 = time.time()
        self.fetch_site()
        elapse = time.time() - t1
        self.update_services("fetch_site", elapse)

        '''***站点截图***'''
        if self.options.get("site_capture"):
            self.update_task_field("status", "site_capture")
            t1 = time.time()
            self.site_screenshot()
            elapse = time.time() - t1
            self.update_services("site_capture", elapse)

        '''站点爬虫'''
        if self.options.get("site_spider"):
            self.update_task_field("status", "site_spider")
            t1 = time.time()
            self.site_spider()
            elapse = time.time() - t1
            self.update_services("site_spider", elapse)

        """风险PoC任务"""
        if self.options.get("poc_config"):
            self.update_task_field("status", "PoC")
            t1 = time.time()
            self.risk_cruising()
            elapse = time.time() - t1
            self.update_services("poc_config", elapse)

        """服务识别（python）实现"""
        if self.options.get("npoc_service_detection"):
            self.update_task_field("status", "npoc_service_detection")
            t1 = time.time()
            self.npoc_service_detection()
            elapse = time.time() - t1
            self.update_services("npoc_service_detection", elapse)

        """弱口令爆破服务"""
        if self.options.get("brute_config"):
            self.update_task_field("status", "weak_brute")
            t1 = time.time()
            self.brute_config()
            elapse = time.time() - t1
            self.update_services("weak_brute", elapse)

        '''文件泄露'''
        if self.options.get("file_leak"):
            self.update_task_field("status", "file_leak")
            t1 = time.time()
            self.file_leak()
            elapse = time.time() - t1
            self.update_services("file_leak", elapse)

        self.insert_task_stat()

        self.insert_finger_stat()

        self.update_task_field("status", TaskStatus.DONE)
        self.update_task_field("end_time", utils.curr_date())


def ip_task(ip_target, task_id, options):
    d = IPTask(ip_target=ip_target, task_id=task_id, options=options)
    try:
        d.run()
    except Exception as e:
        logger.exception(e)
        d.update_task_field("status", "error")
