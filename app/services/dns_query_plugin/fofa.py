from app.services.dns_query import DNSQueryBase
from app import utils
from app.services.fofaClient import fofa_query
import re

class Query(DNSQueryBase):
    def __init__(self):
        super(Query, self).__init__()
        self.source_name = "fofa"

    def sub_domains(self, target):
        # 这里换成host 用domain 二级域名查不来数据。
        query = "host~=\".+\\.{}\"".format(re.escape(target))
        data = fofa_query(query, 9999)
        results = []
        if isinstance(data, dict):
            if data['error']:
                raise Exception(data['error'])

            for item in data["results"]:
                domain_data = item[0]
                if "://" in domain_data:
                    domain_data = domain_data.split(":")[1].strip("/")

                results.append(domain_data.split(":")[0])

        else:
            raise Exception(data)

        return list(set(results))

