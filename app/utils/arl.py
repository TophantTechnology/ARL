from bson import ObjectId
from .conn import conn_db


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
