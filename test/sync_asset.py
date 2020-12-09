import unittest
from app.modules import CeleryAction
from app.celerytask import arl_task



class TestScheduler(unittest.TestCase):
    def test_01_sync_asset(self):
        data = {
            "task_id": "5f4500a26591e72f54e071ec",
            "scope_id": "5fbcc1436591e76488735c3a"
        }
        task_options = {
            "celery_action": CeleryAction.DOMAIN_TASK_SYNC_TASK,
            "data": data
        }
        arl_task(task_options)


if __name__ == '__main__':
    unittest.main()