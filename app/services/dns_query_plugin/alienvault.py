from app.services.dns_query import DNSQueryBase
from app import utils


class Query(DNSQueryBase):
    def __init__(self):
        super(Query, self).__init__()
        self.source_name = "alienvault"
        self.api_url = "https://otx.alienvault.com/"

    def sub_domains(self, target):
        url = "{}api/v1/indicators/domain/{}/passive_dns".format(self.api_url, target)
        items = utils.http_req(url, 'get', timeout=(30.1, 50.1)).json()
        results = []
        for item in items["passive_dns"]:
            results.append(item["hostname"])

        return list(set(results))

