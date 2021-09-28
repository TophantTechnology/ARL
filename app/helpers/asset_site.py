from app import utils


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


