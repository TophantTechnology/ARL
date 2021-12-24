from app import utils


def have_same_site_update_monitor(scope_id):
    query = {
        "scope_id": scope_id,
        "scope_type": "site_update_monitor"
    }

    result = utils.conn_db('scheduler').find_one(query)
    if result:
        return True

    return False
