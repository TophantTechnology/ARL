import unittest
from app import celerytask
from app.utils import conn_db as conn
from app.modules import CeleryAction

task_data = {
    'name': '自动化测试',
    'target': '10.0.80.107',
    'start_time': '-',
    'status': 'waiting',
    'type': 'ip',
    "task_tag": "task",
    'options': {
        'domain_brute': True,
        'domain_brute_type': 'test',
        'port_scan_type': 'custom',
        'port_custom': '80,443,9100',
        'host_timeout_type': 'custom',
        'host_timeout': 130,
        'port_parallelism': 12,
        'port_min_rate': 13,
        'port_scan': True,
        'service_detection': False,
        'service_brute': False,
        'os_detection': False,
        'site_identify': True,
        'site_capture': True,
        'file_leak': False,
        'site_spider': False,
        'nuclei_scan': True,
        'ssl_cert': False,
    },
    "celery_id": "fake celery_id"
}


def submit_task(task_data):
    conn('task').insert_one(task_data)
    task_id = str(task_data.pop("_id"))
    task_data["task_id"] = task_id

    celery_action = CeleryAction.DOMAIN_TASK
    if task_data["type"] == "domain":
        celery_action = CeleryAction.DOMAIN_TASK
    elif task_data["type"] == "ip":
        celery_action = CeleryAction.IP_TASK
    task_options = {
        "celery_action": celery_action,
        "data": task_data
    }
    celerytask.arl_task(options=task_options)

    return task_data


class TestExecTask(unittest.TestCase):
    def test_exec_task(self):
        submit_task(task_data)
        query = {"task_id": task_data["task_id"]}

        if task_data["options"]["port_scan"]:
            self.assertTrue(len(list(conn("site").find(query))) >= 1)
            self.assertTrue(len(list(conn("ip").find(query))) >= 1)


if __name__ == '__main__':
    unittest.main()