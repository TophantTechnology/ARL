from app.services.dns_query import DNSQueryBase
from app import utils


class Query(DNSQueryBase):
    def __init__(self):
        super(Query, self).__init__()
        self.source_name = "crtsh"
        self.api_url = "https://crt.sh/"

    def sub_domains(self, target):
        param = {
            "output": "json",
            "q": target,
            "exclude": "expired"   # 排除过期的证书
        }

        items = utils.http_req(self.api_url, 'get', params=param, timeout=(30.1, 50.1)).json()
        results = []
        for item in items:
            for name in item["name_value"].split():
                if name.endswith("." + target):
                    results.append(name)

        return list(set(results))

