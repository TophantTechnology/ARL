from bson import ObjectId
from app import utils
from app.services.commonTask import CommonTask, WebSiteFetch
from app.modules import TaskStatus
from app.helpers.message_notify import push_email, push_dingding
from app.tasks.poc import RiskCruising
from app.services import webhook
logger = utils.get_logger()


class AssetSiteUpdateTask(CommonTask):
    def __init__(self, task_id, scope_id):
        super().__init__(task_id=task_id)

        self.task_id = task_id
        self.scope_id = scope_id
        self.collection = "task"
        self.results = []

    def update_status(self, value):
        query = {"_id": ObjectId(self.task_id)}
        update = {"$set": {"status": value}}
        utils.conn_db(self.collection).update_one(query, update)

    def set_start_time(self):
        query = {"_id": ObjectId(self.task_id)}
        update = {"$set": {"start_time": utils.curr_date()}}
        utils.conn_db(self.collection).update_one(query, update)

    def set_end_time(self):
        query = {"_id": ObjectId(self.task_id)}
        update = {"$set": {"end_time": utils.curr_date()}}
        utils.conn_db(self.collection).update_one(query, update)

    def save_task_site(self, site_info_list):
        for site_info in site_info_list:
            site_info["task_id"] = self.task_id
            utils.conn_db('site').insert_one(site_info)
        logger.info("save {} to {}".format(len(site_info_list), self.task_id))

    def monitor(self):
        from app.services.asset_site_monitor import AssetSiteMonitor, Domain2SiteMonitor
        self.update_status("fetch site")
        monitor = AssetSiteMonitor(scope_id=self.scope_id)
        monitor.build_change_list()

        if monitor.site_change_info_list:
            self.save_task_site(monitor.site_change_info_list)

        self.update_status("domain site monitor")
        domain2site_monitor = Domain2SiteMonitor(scope_id=self.scope_id)
        if domain2site_monitor.run():
            self.save_task_site(domain2site_monitor.site_info_list)

        self.update_status("send notify")
        html_report = ""
        if monitor.site_change_info_list:
            html_report = monitor.build_html_report()

        if domain2site_monitor.site_info_list:
            html_report += "\n<br/>"
            html_report += domain2site_monitor.html_report

        if html_report:
            html_title = "[站点监控-{}] 灯塔消息推送".format(monitor.scope_name)
            push_email(title=html_title, html_report=html_report)

        markdown_report = ""
        if monitor.site_change_info_list:
            markdown_report = monitor.build_markdown_report()

        if domain2site_monitor.site_info_list:
            markdown_report += "\n"
            markdown_report += domain2site_monitor.dingding_markdown

        if markdown_report:
            push_dingding(markdown_report=markdown_report)

        if html_report or markdown_report:
            webhook.site_asset_web_hook(task_id=self.task_id, scope_id=self.scope_id)

    def run(self):
        self.set_start_time()
        self.monitor()
        self.insert_task_stat()
        self.update_status(TaskStatus.DONE)
        self.set_end_time()


def asset_site_update_task(task_id, scope_id, scheduler_id):
    from app.scheduler import update_job_run

    task = AssetSiteUpdateTask(task_id=task_id, scope_id=scope_id)
    try:
        update_job_run(job_id=scheduler_id)
        task.run()
    except Exception as e:
        logger.exception(e)

        task.update_status(TaskStatus.ERROR)
        task.set_end_time()


class AddAssetSiteTask(RiskCruising):
    def __init__(self, task_id):
        super().__init__(task_id=task_id)

    def asset_site_deduplication(self):
        related_scope_id = self.options.get("related_scope_id", "")
        if not related_scope_id:
            raise Exception("not found related_scope_id, task_id:{}".format(self.task_id))

        new_targets = []

        for url in self.targets:
            if "://" not in url:
                url = "http://" + url

            # 这里简单去下
            url = url.strip("/")
            site_data = utils.conn_db('asset_site').find_one({"site": url, "scope_id": related_scope_id})
            if site_data:
                logger.info("{} is in scope".format(url))
                continue
            new_targets.append(url)
        self.targets = new_targets

    def work(self):
        self.asset_site_deduplication()
        self.pre_set_site()
        if self.user_target_site_set:
            web_site_fetch = WebSiteFetch(task_id=self.task_id,
                                          sites=list(self.user_target_site_set),
                                          options=self.options)
            web_site_fetch.run()

        self.common_run()


def run_add_asset_site_task(task_id):
    query = {"_id": ObjectId(task_id)}
    task_data = utils.conn_db('task').find_one(query)

    if not task_data:
        return

    if task_data["status"] != "waiting":
        return

    r = AddAssetSiteTask(task_id)
    r.run()
