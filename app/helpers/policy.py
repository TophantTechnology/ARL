import bson
from app import utils
from app.modules import TaskTag


def get_options_by_policy_id(policy_id, task_tag):
    query = {
        "_id": bson.ObjectId(policy_id)
    }
    data = utils.conn_db("policy").find_one(query)
    if not data:
        return

    policy = data["policy"]
    options = {
        "policy_name": data["name"]
    }
    domain_config = policy.pop("domain_config")
    ip_config = policy.pop("ip_config")
    site_config = policy.pop("site_config")

    if "scope_config" in policy:
        scope_config = policy.pop("scope_config")
        options["related_scope_id"] = scope_config["scope_id"]

    """仅仅资产发现任务需要这些"""
    if task_tag == TaskTag.TASK:
        options.update(domain_config)
        options.update(ip_config)

    options.update(site_config)

    options.update(policy)
    return options
