import sys
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


# 对site 集合中少数字段创建索引
def create_site_index():
    fields = ["status", "title", "hostname", "site", "http_server"]
    for field in fields:
        conn_db("site").create_index(field)


def arl_update():
    if is_run_flask_routes():
        return

    update_lock = os.path.join(Config.TMP_PATH, 'arl_update.lock')
    if os.path.exists(update_lock):
        return

    update_task_tag()
    create_index()
    create_site_index()

    open(update_lock, 'a').close()


# 判断是否是-m flask routes 模式运行
def is_run_flask_routes():
    if len(sys.argv) == 2:
        if "flask/__main__.py" in sys.argv[0]:
            if sys.argv[1] == "routes":
                return True

    return False
