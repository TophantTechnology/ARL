import time
from crontab import CronTab
from bson import ObjectId
from app.modules import CeleryAction, SchedulerStatus, TaskStatus
from app import celerytask, utils

logger = utils.get_logger()

action_map_collection = {
    CeleryAction.GITHUB_TASK_TASK: "github_task",
    CeleryAction.GITHUB_TASK_MONITOR: "github_task"
}


def submit_github_task(task_data, action, delay_flag=True):
    if action not in action_map_collection:
        return "Not in action_map"

    collection = action_map_collection[action]
    task_options = {
        "celery_action": action,
        "data": task_data
    }
    keyword = task_data["keyword"]
    task_data["celery_id"] = ""
    utils.conn_db(collection).insert_one(task_data)
    task_id = str(task_data.pop("_id"))
    task_data["task_id"] = task_id

    try:
        if delay_flag:
            celery_id = celerytask.arl_github.delay(options=task_options)
        else:
            celery_id = "fake_celery_id"
            celerytask.arl_github(options=task_options)

        logger.info("target:{} task_id:{} celery_id:{}".format(keyword, task_id, celery_id))
        values = {"$set": {"celery_id": str(celery_id)}}
        task_data["celery_id"] = str(celery_id)
        utils.conn_db(collection).update_one({"_id": ObjectId(task_id)}, values)

    except Exception as e:
        utils.conn_db(collection).delete_one({"_id": ObjectId(task_id)})
        logger.info("Github 任务下发失败 {}".format(keyword))
        return str(e)

    return task_data


# Github 监控任务下发
def github_cron_run(item):
    task_data = {
        "name": "GitHub监控-" + item["name"],
        "keyword": item["keyword"],
        "start_time": "-",
        "end_time": "-",
        "github_scheduler_id": str(item["_id"]),
        "status": TaskStatus.WAITING,
    }
    # 下发周期运行任务
    submit_github_task(task_data=task_data, action=CeleryAction.GITHUB_TASK_MONITOR)

    item["run_number"] = item["run_number"] + 1
    item["last_run_date"] = utils.curr_date()
    item["last_run_time"] = int(time.time())
    entry = CronTab(item["cron"])
    now_time = time.time() + 61
    next_sec = entry.next(now=now_time, default_utc=False)
    item["next_run_date"] = utils.time2date(now_time + next_sec - 60)

    query = {
        "_id": item["_id"]
    }
    utils.conn_db('github_scheduler').find_one_and_replace(query, item)


# Github 监控任务调度，有个循环
def github_task_scheduler():
    items = list(utils.conn_db('github_scheduler').find())
    for item in items:
        try:
            if item["status"] != SchedulerStatus.RUNNING:
                continue

            entry = CronTab(item["cron"])
            next_sec = entry.next(default_utc=False)
            if next_sec < 60 and abs(time.time() - item["last_run_time"]) > 60*3:
                logger.info("github_cron_run {} {}".format(item["keyword"], str(item["_id"])))
                github_cron_run(item)

        except Exception as e:
            logger.exception(e)


def find_github_scheduler(_id):
    query = {
        "_id": ObjectId(_id)
    }
    item = utils.conn_db('github_scheduler').find_one(query)
    return item


# 删除 Github 监控任务，还有结果和Hash
def delete_github_scheduler(_id):
    if len(_id) != 24:
        return

    query = {
        "_id": ObjectId(_id)
    }
    utils.conn_db('github_scheduler').delete_one(query)

    result_query = {
        "github_scheduler_id": _id
    }
    # 删除Github 结果 Hash
    utils.conn_db('github_hash').delete_many(result_query)
    # 删除Github 监控结果
    utils.conn_db('github_monitor_result').delete_many(result_query)


# 恢复 Github 监控任务，只是改变状态
def recover_task(_id):
    from app.modules import SchedulerStatus
    if len(_id) != 24:
        return

    item = find_github_scheduler(_id)
    item["status"] = SchedulerStatus.RUNNING
    entry = CronTab(item["cron"])
    next_sec = entry.next(default_utc=False)
    item["next_run_date"] = utils.time2date(time.time() + next_sec)

    query = {
        "_id": ObjectId(_id)
    }
    utils.conn_db('github_scheduler').find_one_and_replace(query, item)


# 停止Github 监控任务，只是改变状态
def stop_task(_id):
    from app.modules import SchedulerStatus
    if len(_id) != 24:
        return

    item = find_github_scheduler(_id)
    item["status"] = SchedulerStatus.STOP
    item["next_run_date"] = "-"

    query = {
        "_id": ObjectId(_id)
    }
    utils.conn_db('github_scheduler').find_one_and_replace(query, item)
