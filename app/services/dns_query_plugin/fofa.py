from app.services.dns_query import DNSQueryBase
from app import utils
from app.services.fofaClient import fofa_query


class Query(DNSQueryBase):
    def __init__(self):
        super(Query, self).__init__()
        self.source_name = "fofa"
        self.api_url = "https://crt.sh/"

    def sub_domains(self, target):
        data = fofa_query("domain=\"{}\"".format(target), 9999)
        results = []
        if isinstance(data, dict):
            if data['error']:
                raise Exception(data['error'])

            for item in data["results"]:
                domain_data = item[0]
                if ":" in domain_data:
                    results.append(domain_data.split(":")[1].strip("/"))
                else:
                    results.append(domain_data)

        else:
            raise Exception(data)

        return list(set(results))

