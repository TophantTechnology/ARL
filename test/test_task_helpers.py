import unittest
from app.helpers.task import restart_task


class TestTaskHelpers(unittest.TestCase):
    def test_restart_task_error(self):
        task_id = "618121a56591e7084d649acb"
        try:
            restart_task(task_id)
        except Exception as e:
            self.assertTrue(task_id in str(e))

    def test_restart_task(self):
        task_id = "618267646591e708cdff207f"
        data = restart_task(task_id)
        self.assertTrue(isinstance(data, dict))


if __name__ == '__main__':
    unittest.main()
