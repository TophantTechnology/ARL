import time
import datetime


def time2date(secs):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(secs))


def time2hms(secs):
    return str(datetime.timedelta(seconds=secs))


def date2time(date):
    struct = time.strptime(date, '%Y-%m-%d %H:%M:%S')
    return time.mktime(struct)


def curr_date():
    return time2date(time.time())


def curr_date_obj():
    return datetime.datetime.now().replace(microsecond=0)