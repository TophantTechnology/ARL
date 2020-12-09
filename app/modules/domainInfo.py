from .baseInfo import BaseInfo


class DomainInfo(BaseInfo):
    def __init__(self, domain, record, type, ips):
        self.record_list = record
        self.domain = domain
        self.type = type
        self.ip_list = ips

    def __eq__(self, other):
        if isinstance(other, DomainInfo):
            if self.domain == other.domain:
                return True

    def __hash__(self):
        return hash(self.domain)

    def _dump_json(self):
        item = {
            "domain": self.domain,
            "record": self.record_list,
            "type": self.type,
            "ips": self.ip_list
        }
        return item