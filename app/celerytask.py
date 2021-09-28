import signal
import time
from bson import ObjectId
from app.config import Config
from celery import Celery, platforms
from app import utils
from app import tasks as wrap_tasks
from app.modules import CeleryAction, TaskSyncStatus
logger = utils.get_logger()

celery = Celery('task', broker=Config.CELERY_BROKER_URL)


class CeleryConfig:
    CELERY_ACKS_LATE = False
    CELERYD_PREFETCH_MULTIPLIER = 1
    BROKER_TRANSPORT_OPTIONS = {"max_retries": 3, "interval_start": 0, "interval_step": 0.2, "interval_max": 0.5}


celery.config_from_object(CeleryConfig)
platforms.C_FORCE_ROOT = True


@celery.task(queue='arltask')
def arl_task(options):
    signal.signal(signal.SIGTERM, utils.exit_gracefully)

    action = options.get("celery_action")
    data = options.get("data")
    action_map = {
        CeleryAction.DOMAIN_TASK_SYNC_TASK: domain_task_sync,
        CeleryAction.DOMAIN_EXEC_TASK: domain_exec,
        CeleryAction.IP_EXEC_TASK: ip_exec,
        CeleryAction.DOMAIN_TASK: domain_task,
        CeleryAction.IP_TASK: ip_task,
        CeleryAction.RUN_RISK_CRUISING: run_risk_cruising,
        CeleryAction.FOFA_TASK: fofa_task,
        CeleryAction.GITHUB_TASK_TASK: github_task_task,
        CeleryAction.GITHUB_TASK_MONITOR: github_task_monitor,
        CeleryAction.ASSET_SITE_UPDATE: asset_site_update
    }
    logger.info(options)
    start_time = time.time()
    logger.info("start {} time: {}".format(action, start_time))
    try:
        fun = action_map.get(action)
        if fun:
            fun(data)
        else:
            logger.warning("not found {} action".format(action))
    except Exception as e:
        logger.exception(e)

    elapsed = time.time() - start_time
    logger.info("end {} elapsed: {}".format(action, elapsed))


def domain_exec(options):
    """域名监测任务"""
    scope_id = options.get("scope_id")
    domain = options.get("domain")
    job_id = options.get("job_id")
    monitor_options = options.get("monitor_options")
    name = options.get("name")
    wrap_tasks.domain_executors(base_domain=domain, job_id=job_id,
                                scope_id=scope_id, options=monitor_options, name=name)


def domain_task_sync(options):
    """域名同步任务"""
    scope_id = options.get("scope_id")
    task_id = options.get("task_id")
    query = {"_id": ObjectId(task_id)}
    try:
        update = {"$set": {"sync_status": TaskSyncStatus.RUNNING}}
        utils.conn_db('task').update_one(query, update)

        wrap_tasks.sync_asset(task_id, scope_id, update_flag=False)

        update = {"$set": {"sync_status": TaskSyncStatus.DEFAULT}}
        utils.conn_db('task').update_one(query, update)
    except Exception as e:
        update = {"$set": {"sync_status": TaskSyncStatus.ERROR}}
        utils.conn_db('task').update_one(query, update)
        logger.exception(e)


def domain_task(options):
    """常规域名任务"""
    target = options["target"]
    task_options = options["options"]
    task_id = options["task_id"]
    item = utils.conn_db('task').find_one({"_id": ObjectId(task_id)})
    if not item:
        logger.info("domain_task not found {} {}".format(target, item))
        return
    wrap_tasks.domain_task(target, task_id, task_options)


def ip_task(options):
    """常规IP任务"""
    target = options["target"]
    task_options = options["options"]
    task_id = options["task_id"]
    wrap_tasks.ip_task(target, task_id, task_options)


def run_risk_cruising(options):
    task_id = options["task_id"]
    wrap_tasks.run_risk_cruising(task_id)


def fofa_task(options):
    task_id = options["task_id"]
    task_options = options["options"]
    target = " ".join(options["fofa_ip"])
    wrap_tasks.ip_task(target, task_id, task_options)


def ip_exec(options):
    """
    IP 监测任务
    """
    scope_id = options.get("scope_id")
    target = options.get("domain")
    job_id = options.get("job_id")
    monitor_options = options.get("monitor_options")
    name = options.get("name")
    wrap_tasks.ip_executor(target=target, scope_id=scope_id,
                           task_name=name, job_id=job_id,
                           options=monitor_options)


def github_task_task(options):
    task_id = options["task_id"]
    keyword = options["keyword"]
    wrap_tasks.github_task_task(task_id=task_id, keyword=keyword)


def github_task_monitor(options):
    task_id = options["task_id"]
    keyword = options["keyword"]
    scheduler_id = options["github_scheduler_id"]
    wrap_tasks.github_task_monitor(task_id=task_id, keyword=keyword, scheduler_id=scheduler_id)


def asset_site_update(options):
    task_id = options["task_id"]
    task_options = options["options"]
    scope_id = task_options["scope_id"]
    scheduler_id = task_options["scheduler_id"]
    wrap_tasks.asset_site_update_task(task_id=task_id,
                                      scope_id=scope_id, scheduler_id=scheduler_id)

