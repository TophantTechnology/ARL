from bson import ObjectId
from app import utils
from app.modules import TaskStatus
from app.services.asset_site_monitor import AssetSiteMonitor
from app.helpers.message_notify import push_email, push_dingding

logger = utils.get_logger()


class AssetSiteUpdateTask(object):
    def __init__(self, task_id, scope_id):
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

    def monitor(self):
        self.update_status("fetch site")
        monitor = AssetSiteMonitor(scope_id=self.scope_id)
        monitor.build_change_list()

        if not monitor.status_change_list and not monitor.title_change_list:
            logger.info("not found change by {}".format(self.scope_id))
            return

        self.update_status("send notify")
        html_report = monitor.build_html_report()
        html_title = "[站点监控-{}] 灯塔消息推送".format(monitor.scope_name)
        push_email(title=html_title, html_report=html_report)

        markdown_report = monitor.build_markdown_report()
        push_dingding(markdown_report=markdown_report)

    def run(self):
        self.set_start_time()
        self.monitor()
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
