from app import utils


def get_url_by_task_id(task_id):
    query = {
        "task_id": task_id
    }
    items = utils.conn_db('url').distinct("url", query)
    return list(items)
