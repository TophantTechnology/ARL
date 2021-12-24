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


# 参考： https://github.com/PyGithub/PyGithub/blob/0245b758ca323dfa18cd7910d50300ca42514999/github/GithubObject.py#L173
def parse_datetime(s):
    if len(s) == 24:
        return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.000Z")

    elif len(s) >= 25:
        return datetime.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S") + (
            1 if s[19] == "-" else -1
        ) * datetime.timedelta(hours=int(s[20:22]), minutes=int(s[23:25]))

    else:
        date1 = datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
        return date1 + datetime.timedelta(hours=8)
