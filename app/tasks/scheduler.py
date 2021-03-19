from celery import current_task
from bson import ObjectId
from app.utils import conn_db as conn
from .domain import DomainTask
from app import utils
from app.modules import TaskStatus, CollectSource
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





