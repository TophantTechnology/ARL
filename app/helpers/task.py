import bson
import re
from app import utils
from app.modules import TaskStatus, TaskTag, TaskType, CeleryAction
from app import celerytask

logger = utils.get_logger()


def target2list(target):
    target = target.strip().lower()
    target_lists = re.split(r",|\s", target)
    # 清除空白符
    target_lists = list(filter(None, target_lists))
    target_lists = list(set(target_lists))

    return target_lists


def get_ip_domain_list(target):
    target_lists = target2list(target)
    ip_list = set()
    domain_list = set()
    for item in target_lists:
        if not item:
            continue

        if utils.is_vaild_ip_target(item):
            if not utils.not_in_black_ips(item):
                raise Exception("{} 在黑名单IP中".format(item))
            ip_list.add(item)

        elif utils.domain.is_forbidden_domain(item):
            raise Exception("{} 包含在禁止域名内".format(item))

        elif utils.is_valid_domain(item):
            domain_list.add(item)

        elif utils.is_valid_fuzz_domain(item):
            domain_list.add(item)
        else:
            raise Exception("{} 无效的目标".format(item))

    return ip_list, domain_list


def build_task_data(task_name, task_target, task_type, task_tag, options):

    # 检查是不是IP ,域名任务等
    avail_task_type = [TaskType.IP, TaskType.DOMAIN, TaskType.RISK_CRUISING]
    if task_type not in avail_task_type:
        raise Exception("{} 无效的 task_type".format(task_type))

    # 检查是不是风险巡航任务等
    avail_task_tag = [TaskTag.RISK_CRUISING, TaskTag.MONITOR, TaskTag.TASK]
    if task_tag not in avail_task_tag:
        raise Exception("{} 无效的 task_tag".format(task_type))

    if not isinstance(options, dict):
        raise Exception("{} 不是 dict".format(options))

    options_cp = options.copy()

    # 针对IP 任务关闭下面的选项
    if task_type == TaskType.IP:
        disable_options = {
            "domain_brute": False,
            "alt_dns": False,
            "riskiq_search": False,
            "arl_search": False
        }
        options_cp.update(disable_options)

    task_data = {
        'name': task_name,
        'target': task_target,
        'start_time': '-',
        'status': TaskStatus.WAITING,
        'type': task_type,
        "task_tag": task_tag,
        'options': options_cp,
        "end_time": "-",
        "service": [],
        "celery_id": ""
    }

    # 单独对风险巡航任务处理
    if task_tag == TaskType.RISK_CRUISING:
        poc_config = options.get("poc_config", [])

        if options.get("result_set_id"):
            result_set_id = options.pop("result_set_id")
            result_set_len = options.pop("result_set_len")
            target_field = "目标：{}， PoC：{}".format(result_set_len, len(poc_config))
            task_data["result_set_id"] = result_set_id
        else:
            target_field = "目标：{}， PoC：{}".format(len(task_target), len(poc_config))
            task_data["cruising_target"] = task_target

        task_data["target"] = target_field

    return task_data


def submit_task(task_data):
    target = task_data["target"]
    utils.conn_db('task').insert_one(task_data)
    task_id = str(task_data.pop("_id"))
    task_data["task_id"] = task_id

    celery_action = ""
    type_map_action = {
        TaskType.DOMAIN: CeleryAction.DOMAIN_TASK,
        TaskType.IP: CeleryAction.IP_TASK,
        TaskType.RISK_CRUISING: CeleryAction.RUN_RISK_CRUISING,
        TaskType.ASSET_SITE_UPDATE: CeleryAction.ASSET_SITE_UPDATE,
        TaskType.FOFA: CeleryAction.FOFA_TASK
    }

    task_type = task_data["type"]
    if task_type in type_map_action:
        celery_action = type_map_action[task_type]

    assert celery_action

    task_options = {
        "celery_action": celery_action,
        "data": task_data
    }

    try:
        celery_id = celerytask.arl_task.delay(options=task_options)
        logger.info("target:{} task_id:{} celery_id:{}".format(target, task_id, celery_id))

        values = {"$set": {"celery_id": str(celery_id)}}
        task_data["celery_id"] = str(celery_id)
        utils.conn_db('task').update_one({"_id": bson.ObjectId(task_id)}, values)

    except Exception as e:
        utils.conn_db('task').delete_one({"_id": bson.ObjectId(task_id), "status": TaskStatus.WAITING})
        logger.info("下发失败 {}".format(target))
        raise e

    return task_data


# 直接根据目标下发任务
def submit_task_task(target, name, options):
    task_data_list = []

    ip_list, domain_list = get_ip_domain_list(target)

    if ip_list:
        ip_target = " ".join(ip_list)
        task_data = build_task_data(task_name=name, task_target=ip_target,
                                    task_type=TaskType.IP, task_tag=TaskTag.TASK,
                                    options=options)

        task_data = submit_task(task_data)
        task_data_list.append(task_data)

    if domain_list:
        for domain_target in domain_list:
            task_data = build_task_data(task_name=name, task_target=domain_target,
                                        task_type=TaskType.DOMAIN, task_tag=TaskTag.TASK,
                                        options=options)
            task_data = submit_task(task_data)
            task_data_list.append(task_data)

    return task_data_list


# 风险巡航任务下发
def submit_risk_cruising(target, name, options):
    target_items = []
    target_lists = target2list(target)
    for x in target_lists:
        if not x:
            continue
        if "://" not in x:
            target_items.append(x)
            continue

        item = utils.url.cut_filename(x)
        if item:
            target_items.append(item)

    target_items = list(set(target_items))

    task_data_list = []
    task_data = build_task_data(task_name=name, task_target=target_items,
                                task_type=TaskType.RISK_CRUISING, task_tag=TaskTag.RISK_CRUISING,
                                options=options)

    task_data = submit_task(task_data)
    task_data_list.append(task_data)

    return task_data_list


def get_task_data(task_id):
    task_data = utils.conn_db('task').find_one({'_id': bson.ObjectId(task_id)})
    return task_data


def restart_task(task_id):
    name_pre = "重新运行-"
    task_data = get_task_data(task_id)
    if not task_data:
        raise Exception("没有找到 task_id : {}".format(task_id))

    # 把一些基础字段初始化
    task_data.pop("_id")
    task_data["start_time"] = "-"
    task_data["status"] = TaskStatus.WAITING
    task_data["end_time"] = "-"
    task_data["service"] = []
    task_data["celery_id"] = ""
    if "statistic" in task_data:
        task_data.pop("statistic")

    name = task_data["name"]
    if name_pre not in name:
        task_data["name"] = name_pre + name

    task_type = task_data["type"]
    task_tag = task_data.get("task_tag", "")

    # 特殊情况单独判断
    if task_type == TaskType.RISK_CRUISING and task_tag == TaskTag.RISK_CRUISING:
        if task_data.get("result_set_id"):
            raise Exception("task_id : {}, 不支持该任务重新运行".format(task_id))

    # 监控任务的重新下发有点麻烦
    if task_type == TaskType.DOMAIN and task_tag == TaskTag.MONITOR:
        raise Exception("task_id : {}, 不支持该任务重新运行".format(task_id))

    elif task_type == TaskType.IP and task_data["options"].get("scope_id"):
        raise Exception("task_id : {}, 不支持该任务重新运行".format(task_id))

    submit_task(task_data)

    return task_data
