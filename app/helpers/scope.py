import bson
from app import utils
from app.utils.ip import ip_in_scope
from app.utils.domain import is_in_scopes


def check_target_in_scope(target, scope_list):
    from .task import get_ip_domain_list
    ip_list, domain_list = get_ip_domain_list(target)
    for ip in ip_list:
        if not ip_in_scope(ip, scope_list):
            raise Exception("{}不在范围{}中".format(ip, ",".join(scope_list)))

    for domain in domain_list:
        if not is_in_scopes(domain, scope_list):
            raise Exception("{}不在范围{}中".format(domain, ",".join(scope_list)))

    return ip_list, domain_list


def get_scope_by_scope_id(scope_id):
    query = {
        "_id": bson.ObjectId(scope_id)
    }
    data = utils.conn_db("asset_scope").find_one(query)
    return data


