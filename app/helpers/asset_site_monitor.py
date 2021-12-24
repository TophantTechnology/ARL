from app.modules import CeleryAction, SchedulerStatus, AssetScopeType, TaskStatus, TaskType
from app import celerytask, utils
from app.config import Config
logger = utils.get_logger()


def submit_asset_site_monitor_job(scope_id, name, scheduler_id):
    from app.helpers.task import submit_task

    task_data = {
        'name': name,
        'target': "资产站点更新",
        'start_time': '-',
        'status': TaskStatus.WAITING,
        'type':  TaskType.ASSET_SITE_UPDATE,
        "task_tag": TaskType.ASSET_SITE_UPDATE,
        'options': {
            "scope_id": scope_id,
            "scheduler_id": scheduler_id
        },
        "end_time": "-",
        "service": [],
        "celery_id": ""
    }

    submit_task(task_data)


black_asset_site_list = None


def is_black_asset_site(site):
    global black_asset_site_list
    if black_asset_site_list is None:
        with open(Config.black_asset_site) as f:
            black_asset_site_list = f.readlines()

    for item in black_asset_site_list:
        item = item.strip()
        if not item:
            continue
        if site.startswith(item):
            return True

    return False




