import logging

from app.services.dns_query import DNSQueryBase
from app import utils


class Query(DNSQueryBase):
    def __init__(self):
        super(Query, self).__init__()
        self.source_name = "passivetotal"
        self.subdomain_api = "https://api.passivetotal.org/v2/enrichment/subdomains"
        self.quota_api = "https://api.passivetotal.org/v2/account/quota"
        self.auth_email = None
        self.auth_key = None

    def sub_domains(self, target):
        try:
            count, limit = self.quota()
            quota = limit - count
            if quota == 0:
                raise Exception("{} api quota is zero {}".format(self.source_name, self.auth_email))

            self.logger.info("{} api quota:{}  [{}/{}][{}]".format(self.source_name,
                                                                   quota, count, limit, self.auth_email))

        except Exception as e:
            if "'user'" == str(e):
                raise Exception("{} api auth error ({}, {})".format(self.source_name, self.auth_email, self.auth_key))
            raise

        params = {
            "query": "*.{}".format(target)
        }
        auth = (self.auth_email, self.auth_key)
        conn = utils.http_req(self.subdomain_api,
                              params=params,
                              auth=auth,
                              timeout=(20, 120))
        data = conn.json()
        subdomains = []
        for item in data['subdomains']:
            # *** passivetotal 的数据被污染严重，先过滤掉
            if "." not in item and len(item) >= 18:
                continue

            if len(item) >= 25:
                continue

            domain = "{}.{}".format(item, target)
            subdomains.append(domain)

        return subdomains

    def init_key(self, auth_email=None, auth_key=None):
        self.auth_email = auth_email
        self.auth_key = auth_key

    def quota(self):
        auth = (self.auth_email, self.auth_key)
        conn = utils.http_req(self.quota_api, auth=auth)
        data = conn.json()
        count = data["user"]["counts"]["search_api"]
        limit = data["user"]["limits"]["search_api"]
        return count, limit

