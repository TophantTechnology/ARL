import unittest
from app.utils.github_task import submit_github_task
from app.celerytask import CeleryAction
from app.modules import TaskStatus


class TestGithubTask(unittest.TestCase):
    def test_submit_github_task(self):
        keyword = "password imhn1ms"
        task_data = {
            "name": "test github task",
            "keyword": keyword,
            "start_time": "-",
            "end_time": "-",
            "status": TaskStatus.WAITING,
        }
        submit_github_task(task_data=task_data, action=CeleryAction.GITHUB_TASK_TASK, delay_flag=False)

    def test_github_monitor_task(self):
        task_data = {
            "name": "test github cron",
            "keyword": "password imhn1ms",
            "start_time": "-",
            "end_time": "-",
            "github_scheduler_id": "60c99bea6591e74c1ddc1f46",
            "status": TaskStatus.WAITING,
        }
        # 下发周期运行任务
        submit_github_task(task_data=task_data, action=CeleryAction.GITHUB_TASK_MONITOR, delay_flag=False)


if __name__ == '__main__':
    unittest.main()
