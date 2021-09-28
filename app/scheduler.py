import sys
from bson import ObjectId
from app.utils import conn_db as conn
from app import utils
from app import celerytask
import time
from app.modules import CeleryAction, SchedulerStatus, AssetScopeType
from app.helpers import task_schedule, asset_site_monitor

logger = utils.get_logger()

domain_monitor_options = {
    'domain_brute': True,
    'domain_brute_type': 'big',
    'riskiq_search': True,
    'alt_dns': False,
    'arl_search': True,
    'port_scan_type': 'test',
    'port_scan': True,
    'crtsh_search': True,
    'site_identify': False
}

ip_monitor_options = {
    'port_scan_type': 'test',
    'port_scan': True,
    'site_identify': False
}


def add_job(domain, scope_id, options=None, interval=60 * 1, name="", scope_type=AssetScopeType.DOMAIN):
    logger.info("add {} job {} {} {}".format(scope_type, interval, domain, scope_id))
    if options is None:
        if scope_type == AssetScopeType.DOMAIN:
            options = domain_monitor_options
        if scope_type == AssetScopeType.IP:
            options = ip_monitor_options

    # 对IP任务域名监测选项设置为False
    disable_options = {
        "domain_brute": False,
        "alt_dns": False,
        "riskiq_search": False,
        "arl_search": False
    }

    if scope_type == AssetScopeType.IP:
        options.update(disable_options)

    current_time = int(time.time()) + 30
    item = {
        "domain": domain,
        "scope_id": scope_id,
        "interval": interval,
        "next_run_time": current_time,
        "next_run_date": utils.time2date(current_time),
        "last_run_time": 0,
        "last_run_date": "-",
        "run_number": 0,
        "status": SchedulerStatus.RUNNING,
        "monitor_options": options,
        "name": name,
        "scope_type": scope_type

    }
    conn('scheduler').insert(item)

    return str(item["_id"])


def add_asset_site_monitor_job(scope_id, name, interval=60 * 1):
    current_time = int(time.time()) + 30

    item = {
        "domain": "资产站点更新",
        "scope_id": scope_id,
        "interval": interval,
        "next_run_time": current_time,
        "next_run_date": utils.time2date(current_time),
        "last_run_time": 0,
        "last_run_date": "-",
        "run_number": 0,
        "status": SchedulerStatus.RUNNING,
        "monitor_options": {},
        "name": name,
        "scope_type": "site_update_monitor"
    }
    conn('scheduler').insert(item)

    return str(item["_id"])


def delete_job(job_id):
    ret = conn("scheduler").delete_one({"_id": ObjectId(job_id)})
    return ret


def stop_job(job_id):
    item = find_job(job_id)
    item["next_run_date"] = "-"
    item["next_run_time"] = sys.maxsize
    item["status"] = SchedulerStatus.STOP
    query = {"_id": ObjectId(job_id)}
    ret = conn('scheduler').find_one_and_replace(query, item)
    return ret


def recover_job(job_id):
    current_time = int(time.time()) + 30
    item = find_job(job_id)

    next_run_time = current_time + item["interval"]
    item["next_run_date"] = utils.time2date(next_run_time)
    item["next_run_time"] = next_run_time
    item["status"] = SchedulerStatus.RUNNING
    query = {"_id": ObjectId(job_id)}
    ret = conn('scheduler').find_one_and_replace(query, item)
    return ret


def find_job(job_id):
    query = {"_id": ObjectId(job_id)}
    item = conn('scheduler').find_one(query)
    return item


def all_job():
    items = []
    for item in conn('scheduler').find():
        items.append(item)
    return items


def submit_job(domain, job_id, scope_id, options=None, name="", scope_type=AssetScopeType.DOMAIN):
    monitor_options = domain_monitor_options.copy()
    if scope_type == AssetScopeType.IP:
        monitor_options = ip_monitor_options.copy()

    if options is None:
        options = {}

    monitor_options.update(options)

    task_data = {
        "domain": domain,
        "scope_id": scope_id,
        "job_id": job_id,
        "type": scope_type,
        "monitor_options": monitor_options,
        "name": name
    }

    if scope_type == AssetScopeType.DOMAIN:
        task_options = {
            "celery_action": CeleryAction.DOMAIN_EXEC_TASK,
            "data": task_data
        }
        celery_id = celerytask.arl_task.delay(options=task_options)
        logger.info("submit domain job {} {} {}".format(celery_id, domain, scope_id))

    if scope_type == AssetScopeType.IP:
        task_options = {
            "celery_action": CeleryAction.IP_EXEC_TASK,
            "data": task_data
        }
        celery_id = celerytask.arl_task.delay(options=task_options)
        logger.info("submit ip job {} {} {}".format(celery_id, domain, scope_id))


def update_job_run(job_id):
    curr_time = int(time.time())
    item = find_job(job_id)
    if not item:
        return
    item["next_run_time"] = curr_time + item["interval"]
    item["next_run_date"] = utils.time2date(item["next_run_time"])
    item["last_run_time"] = curr_time
    item["last_run_date"] = utils.time2date(curr_time)
    item["run_number"] += 1
    query = {"_id": item["_id"]}
    conn('scheduler').find_one_and_replace(query, item)


def asset_monitor_scheduler():
    curr_time = int(time.time())
    for item in all_job():
        try:
            if item.get("status") == SchedulerStatus.STOP:
                continue
            if item["next_run_time"] <= curr_time:
                domain = item["domain"]
                scope_id = item["scope_id"]
                options = item["monitor_options"]
                name = item["name"]
                scope_type = item.get("scope_type")

                if not scope_type:
                    scope_type = AssetScopeType.DOMAIN

                if scope_type == "site_update_monitor":
                    asset_site_monitor.submit_asset_site_monitor_job(scope_id=scope_id,
                                                                     name=name,
                                                                     scheduler_id=str(item["_id"]))

                else:
                    submit_job(domain=domain, job_id=str(item["_id"]),
                               scope_id=scope_id, options=options,
                               name=name, scope_type=scope_type)

                item["next_run_time"] = curr_time + item["interval"]
                item["next_run_date"] = utils.time2date(item["next_run_time"])
                query = {"_id": item["_id"]}
                conn('scheduler').find_one_and_replace(query, item)

        except Exception as e:
            logger.exception(e)


def run_forever():
    from app.utils.github_task import github_task_scheduler
    logger.info("start scheduler server ")
    while True:
        # 资产监控任务调度
        asset_monitor_scheduler()

        # Github 监控任务调度
        github_task_scheduler()

        # 计划任务调度
        task_schedule.task_scheduler()

        # logger.debug(time.time())
        # sleep 时间不能超过60S，Github 里的任务可能运行不了。
        time.sleep(58)


if __name__ == '__main__':
    run_forever()
