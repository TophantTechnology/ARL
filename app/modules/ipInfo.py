from .baseInfo import BaseInfo
from app import utils


class IPInfo(BaseInfo):
    def __init__(self, ip, port_info, os_info, domain, cdn_name):
        self.ip = ip
        self.port_info_list = port_info
        self.os_info = os_info
        self.domain = domain
        self._geo_asn = None
        self._geo_city = None
        self._ip_type = None
        self.cdn_name = cdn_name

    @property
    def geo_asn(self):
        if self._geo_asn:
            return self._geo_asn

        else:
            if self.ip_type == "PUBLIC":
                self._geo_asn = utils.get_ip_asn(self.ip)
            else:
                self._geo_asn = {}

        return self._geo_asn

    @property
    def geo_city(self):
        if self._geo_city:
            return self._geo_city

        else:
            if self.ip_type == "PUBLIC":
                self._geo_city = utils.get_ip_city(self.ip)
            else:
                self._geo_city = {}

        return self._geo_city

    @property
    def ip_type(self):
        if self._ip_type:
            return self._ip_type

        else:
            self._ip_type = utils.get_ip_type(self.ip)

        return self._ip_type

    def __eq__(self, other):
        if isinstance(other, IPInfo):
            if self.ip == other.ip:
                return True

    def __hash__(self):
        return hash(self.ip)

    def _dump_json(self):
        port_info = []
        for x in self.port_info_list:
            port_info.append(x.dump_json(flag=False))

        item = {
            "ip": self.ip,
            "domain": self.domain,
            "port_info": port_info,
            "os_info": self.os_info,
            "ip_type": self.ip_type,
            "geo_asn": self.geo_asn,
            "geo_city": self.geo_city,
            "cdn_name": self.cdn_name
        }
        return item


class PortInfo(BaseInfo):
    def __init__(self, port_id, service_name = "", version = "", protocol = "tcp", product=""):
        self.port_id = port_id
        self.service_name = service_name
        self.version = version
        self.protocol = protocol
        self.product = product

    def __eq__(self, other):
        if isinstance(other, PortInfo):
            if self.port_id == other.port_id:
                return True

    def __hash__(self):
        return hash(self.port_id)


    def _dump_json(self):
        item = {
            "port_id": self.port_id,
            "service_name": self.service_name,
            "version": self.version,
            "protocol": self.protocol,
            "product": self.product
        }
        return item



