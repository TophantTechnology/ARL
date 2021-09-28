from app.modules import CeleryAction, SchedulerStatus, AssetScopeType, TaskStatus, TaskType
from app import celerytask, utils

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

