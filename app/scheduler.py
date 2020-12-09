import sys
from bson import ObjectId
from app.utils import conn_db as conn
from app import utils
from app import celerytask
import time
from app.modules import CeleryAction, SchedulerStatus

logger = utils.get_logger()

domain_monitor_options = {
    'domain_brute': True,
    'domain_brute_type': 'big',
    'riskiq_search': True,
    'alt_dns': True,
    'arl_search': True,
    'port_scan_type': 'test',
    'port_scan': True,
    'site_identify': True
}


def add_job(domain, scope_id, options=None, interval=60*1, name=""):
    logger.info("add job {} {} {}".format(interval, domain, scope_id))
    if options is None:
        options = domain_monitor_options

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
        "name": name

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


def submit_job(domain, job_id, scope_id, options=None, name=""):
    monitor_options = domain_monitor_options.copy()
    if options is None:
        options = {}

    monitor_options.update(options)
    task_data = {
        "domain": domain,
        "scope_id": scope_id,
        "job_id": job_id,
        "type": "domain",
        "monitor_options": monitor_options,
        "name": name
    }

    task_options = {
        "celery_action": CeleryAction.DOMAIN_EXEC_TASK,
        "data": task_data
    }
    celery_id = celerytask.arl_task.delay(options=task_options)
    logger.info("submit job {} {} {}".format(celery_id, domain, scope_id))


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


def run_forever():
    logger.info("start scheduler server ")
    while True:
        curr_time = int(time.time())
        for item in all_job():
            if item.get("status") == SchedulerStatus.STOP:
                continue
            if item["next_run_time"] <= curr_time:
                domain = item["domain"]
                scope_id = item["scope_id"]
                options = item["monitor_options"]
                name = item["name"]
                submit_job(domain=domain, job_id=str(item["_id"]),
                           scope_id=scope_id, options=options, name=name)
                item["next_run_time"] = curr_time + item["interval"]
                item["next_run_date"] = utils.time2date(item["next_run_time"])
                query = {"_id": item["_id"]}
                conn('scheduler').find_one_and_replace(query, item)

        logger.info(time.time())
        time.sleep(30)



if __name__ == '__main__':
    run_forever()