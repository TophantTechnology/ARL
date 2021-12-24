from datetime import datetime
import os
from . import conn_db
from app.config import Config


def update_task_tag():
    """更新task任务tag信息"""
    table = "task"
    items = conn_db(table).find({})
    for item in items:
        task_tag = item.get("task_tag")
        query = {"_id": item["_id"]}
        if not task_tag:
            item["task_tag"] = "task"
            conn_db(table).find_one_and_replace(query, item)


def create_index():
    index_map = {
        "cert": "task_id",
        "domain": "task_id",
        "fileleak": "task_id",
        "ip": "task_id",
        "npoc_service": "task_id",
        "site": "task_id",
        "service": "task_id",
        "url": "task_id",
        "vuln": "task_id",
        "asset_ip": "scope_id",
        "asset_site": "scope_id",
        "asset_domain": "scope_id",
        "github_result": "github_task_id",
        "github_monitor_result": "github_scheduler_id"
    }
    for table in index_map:
        conn_db(table).create_index(index_map[table])


def arl_update():
    update_lock = os.path.join(Config.TMP_PATH, 'arl_update.lock')
    if os.path.exists(update_lock):
        return

    update_task_tag()
    create_index()

    open(update_lock, 'a').close()