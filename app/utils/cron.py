from crontab import CronTab
import time


def check_cron(cron):
    try:
        entry = CronTab(cron)
        previous = entry.previous(default_utc=False)
        next_sec = entry.next(default_utc=False)
        next_next_sec = entry.next(default_utc=False, now=time.time() + next_sec)
        return abs(previous), next_sec, next_next_sec + next_sec
    except Exception as e:
        return str(e), 0, 0


min_interval = 60 * 60 * 6


def check_cron_interval(cron):
    from app import utils
    from app.modules import ErrorMsg

    previous, next_sec, next_next_sec = check_cron(cron)
    if isinstance(previous, str):
        return False, utils.build_ret(ErrorMsg.CronError, data={"error": previous})

    # 这里进行双重检查
    if ((previous + next_sec + 1) < min_interval) and ((next_next_sec - next_sec + 1) < min_interval):
        return False, utils.build_ret(ErrorMsg.IntervalLessThan3600, data={"val": min_interval})

    return True, True
