import unittest
from app import utils
from app.modules import TaskStatus, TaskType
from app import tasks as wrap_tasks


class TestDomainTaskSearchSpider(unittest.TestCase):
    def test_domain_task_search_spider(self):
        target = "tophant.com"
        task_id, task_options = insert_task_data(target)

        wrap_tasks.domain_task(target, task_id, task_options)


def insert_task_data(target):
    options = {
        "domain_brute": True,
        "domain_brute_type": "test",
        'port_scan': True,
        'port_scan_type': 'custom',
        'port_custom': '80,443,22',
        "service_detection": False,
        "service_brute": False,
        "os_detection": False,
        "site_identify": False,
        "site_capture": False,
        "file_leak": False,
        "alt_dns": False,
        "site_spider": True,
        "search_engines": True,
        "ssl_cert": False,
        "fofa_search": False,
        "dns_query_plugin": False,
    }

    task_data = {
        'name': "自动化测试",
        'target': target,
        'start_time': '-',
        'status': TaskStatus.WAITING,
        'type': TaskType.DOMAIN,
        "task_tag": TaskType.DOMAIN,
        'options': options,
        "end_time": "-",
        "service": [],
        "celery_id": "fake"
    }
    utils.conn_db('task').insert_one(task_data)
    task_id = str(task_data.pop("_id"))

    return task_id, options


if __name__ == '__main__':
    unittest.main()
