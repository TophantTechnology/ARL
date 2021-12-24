import unittest
from app.utils.github_task import github_cron_run, find_github_scheduler


class TestGithubCronRun(unittest.TestCase):
    def test_github_search(self):
        scheduler_id = "61960f316591e72363cd64c8"
        item = find_github_scheduler(scheduler_id)
        self.assertTrue(item)

        github_cron_run(item)


if __name__ == '__main__':
    unittest.main()
