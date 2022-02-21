from app import utils
from app.config import Config

logger = utils.get_logger()

class RiskIQPassive():
    def __init__(self, auth_email, auth_key):
        self.auth_email = auth_email
        self.auth_key = auth_key
        self.subdomain_api = "https://api.passivetotal.org/v2/enrichment/subdomains"
        self.quota_api = "https://api.passivetotal.org/v2/account/quota"

    def search_subdomain(self, target):
        params = {
            "query": "*.{}".format(target)
        }
        auth = (self.auth_email, self.auth_key)
        conn = utils.http_req(self.subdomain_api,
                              params = params,
                              auth=auth,
                              timeout=(20, 120))
        data = conn.json()

        subdomains = []
        for item in data['subdomains']:
            item = item.strip("*.")
            item = item.lower()
            if not item:
                continue

            domain = "{}.{}".format(item, target)

            # 删除掉过长的域名
            if len(domain) >= Config.DOMAIN_MAX_LEN:
                continue

            if not utils.is_valid_domain(domain):
                continue

            # 屏蔽和谐域名和黑名单域名
            if utils.check_domain_black(domain):
                continue

            if utils.domain_parsed(domain):
                subdomains.append(domain)

        return list(set(subdomains))

    def quota(self):
        auth = (self.auth_email, self.auth_key)
        conn = utils.http_req(self.quota_api, auth=auth)
        data = conn.json()
        count = data["user"]["counts"]["search_api"]
        limit = data["user"]["limits"]["search_api"]
        return count, limit


def riskiq_search(domain):
    try:
        r = RiskIQPassive(Config.RISKIQ_EMAIL, Config.RISKIQ_KEY)
        count, limit = r.quota()
        logger.info("riskiq api quota [{}/{}] [{}]".format(count, limit, domain))
        if count < limit:
            return r.search_subdomain(domain)
    except Exception as e:
        if "'user'" == str(e):
            logger.warning("riskiq api auth error ({}, {})".format(Config.RISKIQ_EMAIL,
                                                                  Config.RISKIQ_KEY))

        else:
            logger.exception(e)

    return []


def riskiq_quota():
    try:
        r = RiskIQPassive(Config.RISKIQ_EMAIL, Config.RISKIQ_KEY)
        count, limit = r.quota()
        quota = limit - count
        if quota == 0:
            logger.info("riskiq api quota is zero {}".format(Config.RISKIQ_EMAIL))
        return quota
    except Exception as e:
        logger.exception(e)

    return 0