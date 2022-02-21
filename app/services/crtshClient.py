from app import utils
logger = utils.get_logger()


class CrtshClient:
    def __init__(self):
        self.url = "https://crt.sh/"

    def search(self, domain):
        param = {
            "output": "json",
            "q": domain
        }

        data = utils.http_req(self.url, 'get', params=param, timeout=(30.1, 50.1)).json()
        return data


def crtsh_search(domain):
    name_list = []
    try:
        c = CrtshClient()
        items = c.search(domain)
        for item in items:
            for name in item["name_value"].split():
                name = name.strip()
                name = name.strip("*.")
                name = name.lower()

                if not utils.is_valid_domain(name):
                    continue

                # 屏蔽和谐域名和黑名单域名
                if utils.check_domain_black(name):
                    continue

                if name.endswith("."+domain):
                    name_list.append(name)

        name_list = list(set(name_list))
        logger.info("search crtsh {} {}".format(domain, len(name_list)))

    except Exception as e:
        logger.exception(e)

    return name_list

