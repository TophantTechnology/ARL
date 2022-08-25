import unittest
from app import celerytask
from app.utils import conn_db as conn
from app.modules import CeleryAction

task_data = {
    'name': '自动化测试',
    'target': '目标：1， PoC：0',
    'start_time': '-',
    'status': 'waiting',
    'type': 'risk_cruising',
    "task_tag": "risk_cruising",
    'options': {
        'site_identify': True,
        'site_capture': True,
        'file_leak': False,
        'site_spider': True,
        'policy_name': '站点',
        "related_scope_id": "",
        "npoc_service_detection": False,
        "poc_config": [],
        "brute_config": []
    },
    "cruising_target": [
        "https://www.baidu.com"
    ]
}


def submit_task(task_data):
    conn('task').insert_one(task_data)
    task_id = str(task_data.pop("_id"))
    task_data["task_id"] = task_id

    task_options = {
        "celery_action": CeleryAction.RUN_RISK_CRUISING,
        "data": task_data
    }
    celerytask.arl_task(options=task_options)

    return task_data


class TestExecTask(unittest.TestCase):
    def test_exec_task(self):
        submit_task(task_data)
        query = {"task_id": task_data["task_id"]}
        self.assertTrue(len(list(conn("site").find(query))) >= 1)


if __name__ == '__main__':
    unittest.main()
