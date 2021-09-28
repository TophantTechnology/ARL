from threading import Thread
from app import utils
from app.modules import TaskStatus
from app.services import npoc
from app.config import Config
import time
logger = utils.get_logger()
from bson import ObjectId
from urllib.parse import urlparse
from app import services
from app.services.commonTask import CommonTask


def run_risk_cruising(task_id):
    query = {"_id": ObjectId(task_id)}
    task_data = utils.conn_db('task').find_one(query)

    if not task_data:
        return
    if task_data["status"] != "waiting":
        return

    r = RiskCruising(task_id)
    r.run()


class RiskCruising(CommonTask):
    def __init__(self, task_id):
        super().__init__(task_id=task_id)

        self.task_id = task_id
        query = {"_id": ObjectId(task_id)}
        self.query = query
        task_data = utils.conn_db('task').find_one(query)
        self.task_data = task_data
        self.options = self.task_data.get("options", {})

        self.poc_plugin_name = []
        self.brute_plugin_name = []
        self.result_set_id = self.task_data.get("result_set_id")
        self.targets = self.task_data.get("cruising_target")
        self.sniffer_target_set = set()
        self.npoc_service_target_set = set()
        self.user_target_site_set = set()  # 用户提交的目录站点
        self.site_list = []
        self.site_302_list = []

    def init_plugin_name(self):
        poc_config = self.options.get("poc_config", [])
        plugin_name = []
        for item in poc_config:
            if item.get("enable"):
                plugin_name.append(item["plugin_name"])

        self.poc_plugin_name = plugin_name

        brute_config = self.options.get("brute_config", [])
        plugin_name = []
        for item in brute_config:
            if item.get("enable"):
                plugin_name.append(item["plugin_name"])

        self.brute_plugin_name = plugin_name

    def set_relay_targets(self):
        if self.targets:
            for x in self.targets:
                o = urlparse(x)
                if not o.scheme and x:
                    self.sniffer_target_set.add(x)
                    continue

                if o.scheme in ["http", "https"]:
                    continue

                if o.netloc:
                    self.sniffer_target_set.add(o.netloc)

        if not self.result_set_id:
            return
        query_result_set = {"_id": ObjectId(self.result_set_id)}
        item = utils.conn_db('result_set').find_one(query_result_set)
        targets = item["items"]
        utils.conn_db('result_set').delete_one(query_result_set)
        self.targets = targets

    def npoc_service_detection(self):
        logger.info("start npoc_service_detection {}".format(len(self.sniffer_target_set)))
        result = npoc.run_sniffer(self.sniffer_target_set)
        for item in result:
            self.npoc_service_target_set.add(item["target"])
            item["task_id"] = self.task_id
            item["save_date"] = utils.curr_date()
            utils.conn_db('npoc_service').insert_one(item)

    def run_poc(self):
        """运行poc，获取进度"""
        targets = self.site_list + list(self.npoc_service_target_set)
        logger.info("start run poc {}*{}".format(len(self.poc_plugin_name), len(targets)))

        run_total = len(self.poc_plugin_name) * len(targets)
        npoc_instance = npoc.NPoC(tmp_dir=Config.TMP_PATH, concurrency=10)
        run_thread = Thread(target=npoc_instance.run_poc, args=(self.poc_plugin_name, targets))
        run_thread.start()
        while run_thread.is_alive():
            time.sleep(5)
            status = "poc {}/{}".format(npoc_instance.runner.runner_cnt, run_total)
            logger.info("[{}]runner cnt {}/{}".format(self.task_id,
                                                      npoc_instance.runner.runner_cnt, run_total))
            self.update_task_field("status", status)

        result = npoc_instance.result
        for item in result:
            item["task_id"] = self.task_id
            item["save_date"] = utils.curr_date()
            utils.conn_db('vuln').insert_one(item)

    def run_brute(self):
        """运行爆破，获取进度"""
        target = self.site_list + list(self.npoc_service_target_set)
        plugin_name = self.brute_plugin_name
        logger.info("start run brute {}*{}".format(len(plugin_name), len(target)))
        run_total = len(plugin_name) * len(target)

        npoc_instance = npoc.NPoC(tmp_dir=Config.TMP_PATH, concurrency=10)
        run_thread = Thread(target=npoc_instance.run_poc, args=(plugin_name, target))
        run_thread.start()
        while run_thread.is_alive():
            time.sleep(5)
            status = "brute {}/{}".format(npoc_instance.runner.runner_cnt, run_total)
            logger.info("[{}]runner cnt {}/{}".format(self.task_id,
                                                      npoc_instance.runner.runner_cnt, run_total))
            self.update_task_field("status", status)

        result = npoc_instance.result
        for item in result:
            item["task_id"] = self.task_id
            item["save_date"] = utils.curr_date()
            utils.conn_db('vuln').insert_one(item)

    def find_site(self):
        for x in self.targets:
            if "://" not in x:
                self.user_target_site_set.add("http://{}".format(x))
                continue

            if not x.startswith("http"):
                continue

            cut_target = utils.url.cut_filename(x)
            if cut_target:
                self.user_target_site_set.add(cut_target)

    def fetch_site(self):
        site_info_list = services.fetch_site(self.user_target_site_set)
        for site_info in site_info_list:
            curr_site = site_info["site"]

            self.site_list.append(curr_site)

            if curr_site not in self.user_target_site_set:
                self.site_302_list.append(curr_site)
            site_path = "/image/" + self.task_id
            file_name = '{}/{}.jpg'.format(site_path, utils.gen_filename(curr_site))
            site_info["task_id"] = self.task_id
            site_info["screenshot"] = file_name
            site_info["finger"] = []
            utils.conn_db('site').insert_one(site_info)

    def file_leak(self):
        for site in self.site_list:
            pages = services.file_leak([site], utils.load_file(Config.FILE_LEAK_TOP_2k))
            for page in pages:
                item = page.dump_json()
                item["task_id"] = self.task_id
                item["site"] = site

                utils.conn_db('fileleak').insert_one(item)

    def update_services(self, status, elapsed):
        elapsed = "{:.2f}".format(elapsed)
        self.update_task_field("status", status)
        update = {"$push": {"service": {"name": status, "elapsed": float(elapsed)}}}
        utils.conn_db('task').update_one(self.query, update)

    def update_task_field(self, field = None, value = None):
        update = {"$set": {field: value}}
        utils.conn_db('task').update_one(self.query, update)

    def work(self):

        self.set_relay_targets()
        self.init_plugin_name()

        self.update_task_field("status", "fetch site")
        t1 = time.time()
        self.find_site()
        self.fetch_site()
        elapse = time.time() - t1
        self.update_services("fetch site", elapse)

        if self.options.get("npoc_service_detection"):
            self.update_task_field("status", "npoc_service_detection")
            t1 = time.time()
            self.npoc_service_detection()
            elapse = time.time() - t1
            self.update_services("npoc_service_detection", elapse)

        if self.brute_plugin_name:
            self.update_task_field("status", "weak_brute")
            t1 = time.time()
            self.run_brute()
            elapse = time.time() - t1
            self.update_services("weak_brute", elapse)

        if self.poc_plugin_name:
            self.update_task_field("status", "PoC")
            t1 = time.time()
            self.run_poc()
            elapse = time.time() - t1
            self.update_services("PoC", elapse)

        if self.options.get("file_leak"):
            self.update_task_field("status", "file_leak")
            t1 = time.time()
            self.file_leak()
            elapse = time.time() - t1
            self.update_services("file_leak", elapse)

        self.insert_task_stat()

    def run(self):
        try:
            self.update_task_field("start_time", utils.curr_date())
            self.work()
            self.update_task_field("status", TaskStatus.DONE)
        except Exception as e:
            self.update_task_field("status", TaskStatus.ERROR)
            logger.exception(e)

        self.update_task_field("end_time", utils.curr_date())
