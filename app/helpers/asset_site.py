from app import utils
from .scope import get_scope_by_scope_id


def build_show_filed_map(fields):
    q = {}
    for field in fields:
        q[field] = 1

    return q


def find_site_info_by_scope_id(scope_id):
    query = {
        "scope_id": scope_id
    }
    fields = ["site", "title", "status"]
    show_map = build_show_filed_map(fields)
    items = utils.conn_db('asset_site').find(query, show_map)
    return list(items)


def find_site_by_scope_id(scope_id):
    query = {
        "scope_id": scope_id
    }
    items = utils.conn_db('asset_site').distinct("site", query)
    return list(items)


# 检查用户提交的站点，判断是否符合范围,
def check_asset_site_in_scope(site: str, scope_array: list) -> bool:
    for scope in scope_array:
        # 简单判断下
        if scope in site:
            return True
    return False


# 用户提交的站点，判断出哪些是不符合范围的
def find_asset_site_not_in_scope(sites: list, scope_id: str) -> list:
    ret = []
    scopes = get_scope_by_scope_id(scope_id)
    scope_array = scopes.get("scope_array", [])
    for site in sites:
        if not check_asset_site_in_scope(site, scope_array):
            ret.append(site)

    return ret

