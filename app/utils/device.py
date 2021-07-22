import psutil


def device_info():
    ret = dict()
    ret["cpu"] = {
        "count": psutil.cpu_count(),
        "percent": psutil.cpu_percent()
    }

    v_mem = psutil.virtual_memory()
    ret["virtual_memory"] = {
        "total": human_size(v_mem.total),
        "used": human_size(v_mem.total - v_mem.available),
        "percent": v_mem.percent
    }

    disk = psutil.disk_usage("/")
    ret["disk_usage"] = {
        "total": human_size(disk.total),
        "used": human_size(disk.used),
        "percent": human_size(disk.percent)
    }
    return ret


def human_size(byte):
    for x in ["", "K", "M", "G", "T"]:
        if byte < 1024:
            return f"{byte:.2f}{x}"
        byte = byte/1024

