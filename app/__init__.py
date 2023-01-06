import warnings

# 关闭警告
warnings.filterwarnings("ignore", category=UserWarning,
                        message="Python 3.6 is no longer supported by the Python core team")

# 关闭高权限使用celery警告
warnings.filterwarnings("ignore", category=UserWarning,
                        message="You're running the worker with superuser privileges")

