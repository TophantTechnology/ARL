from app import utils


def find_domain_by_scope_id(scope_id):
    query = {
        "scope_id": scope_id
    }
    items = utils.conn_db('asset_domain').distinct("domain", query)
    return list(items)




