import os
import signal
import psutil
from app.config import  Config
from celery import Celery, platforms
from app import utils
from app import tasks as wrap_tasks
logger = utils.get_logger()

celery = Celery('task', broker=Config.CELERY_BROKER_URL)


class CeleryConfig:
    CELERY_ACKS_LATE=False
    CELERYD_PREFETCH_MULTIPLIER=1


celery.config_from_object(CeleryConfig)
platforms.C_FORCE_ROOT = True



@celery.task(queue='arltask')
def arl_task(options):
    signal.signal(signal.SIGTERM, utils.exit_gracefully)
    try:
        target = options["target"]
        task_options = options["options"]
        task_id = options["task_id"]
        logger.info(options)
        task_type = options["type"]
        if task_type == "domain":
            wrap_tasks.domain_task(target, task_id, task_options)
        if task_type == "ip":
            wrap_tasks.ip_task(target, task_id, task_options)

    except Exception as e:
        logger.exception(e)
