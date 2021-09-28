from bson import ObjectId
from .conn import conn_db
from .IPy import IP
import re

def get_task_ids(domain):
    query = {"target": domain}
    task_ids = []
    for item in conn_db('task').find(query):
        task_ids.append(str(item["_id"]))

    return task_ids


def get_domain_by_id(task_id):
    query = {"task_id": task_id}
    domains = []
    for item in conn_db('domain').find(query):
        domains.append(item["domain"])

    return domains


def arl_domain(domain):
    domains = []
    for task_id in get_task_ids(domain):
        for item in get_domain_by_id(task_id):
            if item.endswith("." + domain):
                domains.append(item)

    for scope_id in get_scope_ids(domain):
        for item in get_asset_domain_by_id(scope_id):
            if item.endswith("." + domain):
                domains.append(item)

    return list(set(domains))


def get_asset_domain_by_id(scope_id):
    query = {"scope_id": scope_id}
    domains = []
    for item in conn_db('asset_domain').find(query):
        domains.append(item["domain"])

    return domains


def get_monitor_domain_by_id(scope_id):
    query = {"scope_id": scope_id}
    items = conn_db('scheduler').find(query)
    domains = []
    for item in items:
        domains.append(item["domain"])
    return domains


def scope_data_by_id(scope_id):
    query = {"_id": ObjectId(scope_id)}
    item = conn_db('asset_scope').find_one(query)

    return item


def get_scope_ids(domain):
    query = {"scope_array": domain}
    scope_ids = []
    for item in conn_db('asset_scope').find(query):
        scope_ids.append(str(item["_id"]))

    return scope_ids


def task_statistic(task_id=None):
    """对任务中的资产信息进行统计"""
    query = dict()
    if isinstance(task_id, str) and len(task_id) == 24:
        query["task_id"] = task_id

    ret = dict()
    table_list = ['site', 'domain', 'ip', 'cert', 'service', 'fileleak']
    table_list.extend(['url', 'vuln', 'npoc_service', 'cip'])
    for table in table_list:
        cnt = conn_db(table).count_documents(query)
        stat_key = table + "_cnt"
        ret[stat_key] = cnt

    return ret


def gen_cip_map(task_id=None):
    query = dict()
    if isinstance(task_id, str) and len(task_id) == 24:
        query["task_id"] = task_id

    results = list(conn_db('ip').find(query, {"ip": 1, "domain": 1}))
    cip_map = dict()
    for result in results:
        if result.get("domain") is None:
            continue

        cip = result["ip"] + "/24"
        cip = IP(cip, make_net=True).strNormal(1)
        count_map = cip_map.get(cip)
        if count_map is None:
            cip_map[cip] = {
                "domain_set": set(result["domain"]),
                "ip_set": {result["ip"]}
            }
        else:
            count_map["domain_set"] |= set(result["domain"])
            count_map["ip_set"] |= {result["ip"]}

    return cip_map


def gen_stat_finger_map(task_id=None):
    query = dict()
    if isinstance(task_id, str) and len(task_id) == 24:
        query["task_id"] = task_id

    results = list(conn_db('site').find(query, {"finger": 1}))
    finger_map = dict()
    for result in results:
        if not isinstance(result.get("finger"), list):
            continue

        for finger in result["finger"]:
            key = finger["name"].lower()

            if key not in finger_map:
                finger_map[key] = {
                    "name": finger["name"],
                    "cnt": 1
                }
            else:
                finger_map[key]["cnt"] += 1

    return finger_map


def build_port_custom(port_custom):
    port_list = []
    splits = port_custom.split(",")
    if len(splits) < 1:
        return ""
    for item in splits:
        item = item.strip()
        if re.match(r"^[\d\-]+$", item):
            port_list.append(item)
        else:
            return item

    return port_list


