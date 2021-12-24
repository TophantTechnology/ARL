from celery import current_task
from bson import ObjectId
from app.utils import conn_db as conn
from .domain import DomainTask
from .ip import IPTask
from app import utils
from app.modules import TaskStatus, CollectSource, SchedulerStatus
from app.services import sync_asset, build_domain_info
logger = utils.get_logger()
import time
from app.scheduler import update_job_run


def domain_executors(base_domain=None, job_id=None, scope_id=None, options=None, name=""):
    logger.info("start domain_executors {} {} {}".format(base_domain, scope_id, options))
    try:
        query = {"_id": ObjectId(job_id)}
        item = utils.conn_db('scheduler').find_one(query)
        if not item:
            logger.info("stop  domain_executors {}  not found job_id {}".format(base_domain, job_id))
            return

        if item.get("status") == SchedulerStatus.STOP:
            logger.info("stop  ip_executors {}  job_id {} is stop ".format(base_domain, job_id))
            return

        wrap_domain_executors(base_domain=base_domain, job_id=job_id, scope_id=scope_id, options=options, name=name)
    except Exception as e:
        logger.exception(e)


def wrap_domain_executors(base_domain=None, job_id=None, scope_id=None, options=None, name=""):
    celery_id = "celery_id_placeholder"

    if current_task._get_current_object():
        celery_id = current_task.request.id

    task_data = {
        'name': name,
        'target': base_domain,
        'start_time': '-',
        'status': 'waiting',
        'type': 'domain',
        'task_tag': 'monitor',  #标记为监控任务
        'options': {
            'domain_brute': True,
            'domain_brute_type': 'test',
            'riskiq_search': False,
            'alt_dns': False,
            'arl_search': True,
            'port_scan_type': 'test',
            'port_scan': True,
            'service_detection': False,
            'service_brute': False,
            'os_detection': False,
            'site_identify': False,
            'site_capture': False,
            'file_leak': False,
            'site_spider': False,
            'search_engines': False,
            'ssl_cert': False,
            'fofa_search': False,
            'crtsh_search': True,
            'scope_id': scope_id
        },
        'celery_id': celery_id
    }
    if options is None:
        options = {}
    task_data["options"].update(options)

    conn('task').insert_one(task_data)
    task_id = str(task_data.pop("_id"))
    domain_executor = DomainExecutor(base_domain, task_id, task_data["options"])
    try:
        update_job_run(job_id)
        new_domain = domain_executor.run()
        if new_domain:
            sync_asset(task_id, scope_id, update_flag=True, push_flag=True, task_name=name)
    except Exception as e:
        logger.exception(e)
        domain_executor.update_task_field("status", TaskStatus.ERROR)
        domain_executor.update_task_field("end_time", utils.curr_date())

    logger.info("end domain_executors {} {} {}".format(base_domain, scope_id, options))


class DomainExecutor(DomainTask):
    def __init__(self, base_domain, task_id, options):
        super().__init__(base_domain, task_id, options)
        self.domain_set = set()
        self.scope_id = options["scope_id"]
        self.scope_domain_set = None
        self.new_domain_set = None
        self.task_tag = "monitor"
        self.wildcard_ip_set = None

    def run(self):
        self.update_task_field("start_time", utils.curr_date())
        self.domain_fetch()
        for domain_info in self.domain_info_list:
            self.domain_set.add(domain_info.domain)

        self.set_scope_domain()

        new_domain_set = self.domain_set - self.scope_domain_set
        self.new_domain_set = new_domain_set

        self.set_wildcard_ip_set()

        self.set_domain_info_list()

        #仅仅对新增域名保留
        self.start_ip_fetch()
        self.start_site_fetch()

        # cidr ip 结果统计，插入cip 集合中
        self.insert_cip_stat()

        # 任务结果统计
        self.insert_task_stat()
        # 任务指纹信息统计
        self.insert_finger_stat()

        self.update_task_field("status", TaskStatus.DONE)
        self.update_task_field("end_time", utils.curr_date())

        ret_new_domain_set = set()
        for domain_info in self.domain_info_list:
            ret_new_domain_set.add(domain_info.domain)

        return ret_new_domain_set

    def set_scope_domain(self):
        """
        查询资产库中域名
        """
        self.scope_domain_set = set(utils.get_asset_domain_by_id(self.scope_id))

    def set_domain_info_list(self):
        """
        将domain_info_list替换为仅仅包括新增域名
        """
        self.domain_info_list = []
        self.record_map = {}
        logger.info("start build domain monitor task, new domain {}".format(len(self.new_domain_set)))
        t1 = time.time()

        self.task_tag = "task" #标记为正常任务，让build_domain_info 工作
        new = self.build_domain_info(self.new_domain_set)
        new = self.clear_domain_info_by_record(new)
        self.task_tag = "monitor"

        if self.wildcard_ip_set:
            new = self.clear_wildcard_domain_info(new)

        elapse = time.time() - t1
        logger.info("end build domain monitor task  {}, elapse {}".format(
            len(new), elapse))

        #删除前面步骤插入的域名
        conn('domain').delete_many({"task_id": self.task_id})

        #重新保存新发现的域名
        self.save_domain_info_list(new, CollectSource.MONITOR)
        self.domain_info_list = new

    def set_wildcard_ip_set(self):
        cut_set = set()
        random_name = utils.random_choices(6)
        for domain in self.new_domain_set:
            cut_name = utils.domain.cut_first_name(domain)
            if cut_name:
                cut_set.add("{}.{}".format(random_name, cut_name))

        info_list = build_domain_info(cut_set)
        wildcard_ip_set = set()
        for info in info_list:
            wildcard_ip_set |= set(info.ip_list)

        self.wildcard_ip_set = wildcard_ip_set
        logger.info("start get wildcard_ip_set {}".format(len(self.wildcard_ip_set)))

    def clear_wildcard_domain_info(self, info_list):
        cnt = 0
        new = []
        for info in info_list:
            common_set = self.wildcard_ip_set & set(info.ip_list)
            if common_set:
                cnt += 1
                continue
            new.append(info)
        logger.info("clear_wildcard_domain_info {}".format(cnt))
        return new


class IPExecutor(IPTask):
    def __init__(self, target, scope_id, task_name,  options):
        super().__init__(ip_target=target, task_id=None, options=options)
        self.scope_id = scope_id
        self.task_name = task_name
        self.task_tag = "monitor"  # 标记为监控任务

    def insert_task_data(self):
        celery_id = ""
        if current_task._get_current_object():
            celery_id = current_task.request.id

        task_data = {
            'name': self.task_name,
            'target': self.ip_target,
            'start_time': '-',
            'end_time': '-',
            'status': TaskStatus.WAITING,
            'type': 'ip',
            'task_tag': 'monitor',  # 标记为监控任务
            'options': {
                "port_scan_type": "test",
                "port_scan": True,
                "service_detection": False,
                "os_detection": False,
                "site_identify": False,
                "site_capture": False,
                "file_leak": False,
                "site_spider": False,
                "ssl_cert": False,
                'scope_id': self.scope_id
            },
            'celery_id': celery_id
        }

        if self.options is None:
            self.options = {}

        task_data["options"].update(self.options)
        conn('task').insert_one(task_data)
        self.task_id = str(task_data.pop("_id"))

    def set_asset_ip(self):
        if self.task_tag != 'monitor':
            return

        query = {"scope_id": self.scope_id}
        items = list(utils.conn_db('asset_ip').find(query, {"ip": 1, "port_info": 1}))
        for item in items:
            self.asset_ip_info_map[item["ip"]] = item
            for port_info in item["port_info"]:
                ip_port = "{}:{}".format(item["ip"], port_info["port_id"])
                self.asset_ip_port_set.add(ip_port)

    def async_ip_info(self):
        new_ip_info_list = []
        for ip_info in self.ip_info_list:
            curr_ip = ip_info["ip"]
            curr_date_obj = utils.curr_date_obj()

            # 新发现的IP ，直接入资产集合
            if curr_ip not in self.asset_ip_info_map:
                asset_ip_info = ip_info.copy()
                asset_ip_info["scope_id"] = self.scope_id
                asset_ip_info["domain"] = []
                asset_ip_info["save_date"] = curr_date_obj
                asset_ip_info["update_date"] = curr_date_obj
                utils.conn_db('asset_ip').insert_one(asset_ip_info)
                utils.conn_db('ip').insert_one(ip_info)
                new_ip_info_list.append(ip_info)
                continue

            # 保存新发现的端口
            new_port_info_list = []
            for port_info in ip_info["port_info"]:
                ip_port = "{}:{}".format(curr_ip, port_info["port_id"])
                if ip_port in self.asset_ip_port_set:
                    continue

                new_port_info_list.append(port_info)

            if new_port_info_list:
                asset_ip_info = self.asset_ip_info_map[curr_ip]
                asset_ip_info["port_info"].extend(new_port_info_list)

                update_info = dict()
                update_info["update_date"] = utils.curr_date_obj()
                update_info["port_info"] = asset_ip_info["port_info"]
                query = {"_id": asset_ip_info["_id"]}
                utils.conn_db('asset_ip').update_one(query, {"$set": update_info})

                # 只是保存新发现的端口
                ip_info["port_info"] = new_port_info_list
                utils.conn_db('ip').insert_one(ip_info)

                new_ip_info_list.append(ip_info)
                continue

        self.ip_info_list = new_ip_info_list
        logger.info("found new ip_info {}".format(len(self.ip_info_list)))

    def async_site_info(self, site_info_list):
        """
        用来同步发现的 site 中的信息，仅仅在监控阶段使用
        """
        new_site_info_list = []
        for site_info in site_info_list:
            curr_date_obj = utils.curr_date_obj()
            query = {"site":site_info["site"], "scope_id": self.scope_id}
            data = utils.conn_db('asset_site').find_one(query)
            if data:
                continue

            new_site_info_list.append(site_info)
            site_info["save_date"] = curr_date_obj
            site_info["update_date"] = curr_date_obj
            site_info["scope_id"] = self.scope_id
            utils.conn_db('asset_site').insert_one(site_info)

        new_asset_map = {
            "site": new_site_info_list[:10],
            "ip": self.ip_info_list[:10],
            "task_name": self.task_name
        }
        new_asset_counter = {
            "site": len(new_site_info_list),
            "ip": len(self.ip_info_list)
        }

        if len(self.ip_info_list) > 0:
            utils.message_push(asset_map=new_asset_map, asset_counter=new_asset_counter)


def ip_executor(target, scope_id, task_name, job_id, options):
    try:
        query = {"_id": ObjectId(job_id)}
        item = utils.conn_db('scheduler').find_one(query)
        if not item:
            logger.info("stop  ip_executors {}  not found job_id {}".format(target, job_id))
            return

        if item.get("status") == SchedulerStatus.STOP:
            logger.info("stop  ip_executors {}  job_id {} is stop ".format(target, job_id))
            return

        update_job_run(job_id)
    except Exception as e:
        logger.exception(e)
        return

    executor = IPExecutor(target, scope_id, task_name,  options)
    try:
        executor.insert_task_data()
        executor.run()
    except Exception as e:
        logger.warning("error on ip_executor {}".format(executor.ip_target))
        logger.exception(e)
        executor.update_task_field("status", TaskStatus.ERROR)