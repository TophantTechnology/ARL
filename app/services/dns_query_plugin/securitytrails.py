from app.services.dns_query import DNSQueryBase
from app import utils


class Query(DNSQueryBase):
    def __init__(self):
        super(Query, self).__init__()
        self.source_name = "securitytrails"
        self.api_url = "https://api.securitytrails.com/"
        self.api_key = None

    def init_key(self, api_key=None):
        self.api_key = api_key

    def sub_domains(self, target):
        params = {
            "children_only": "false",
            "include_inactive": "true",
        }

        url = "{}v1/domain/{}/subdomains".format(self.api_url, target)

        headers = {
            "Accept": "application/json",
            "APIKEY": self.api_key
        }

        conn = utils.http_req(url,
                              params=params,
                              headers=headers,
                              timeout=(20, 120))
        data = conn.json()
        message = data.get("message")
        if message:
            self.logger.error(f"{self.source_name} error: {message}")
            return []

        subdomains = []
        for item in data['subdomains']:
            domain = "{}.{}".format(item, target)
            subdomains.append(domain)

        return list(set(subdomains))

