import os
import subprocess

from app.config import Config
from app.services.dns_query import DNSQueryBase
from app import utils


class Query(DNSQueryBase):
    def __init__(self):
        super(Query, self).__init__()
        self.api_key = None
        self.chaos_path = "chaos-client"

    def init_key(self, api_key=None):
        self.api_key = api_key

    def sub_domains(self, target: str) -> list:
        try:
            command = [self.chaos_path, "-d", target, "-key", self.api_key, "-silent", "-o", target + ".txt"]
            utils.exec_system(command, timeout=1 * 60)
        except Exception as e:
            self.logger.error("chaos error: {}".format(e))

        return self.read_run_result(target)

    def read_run_result(self, target: str) -> list:
        with open(target + ".txt", "r") as f:
            sub_domains = f.readlines()
        domains = []
        for domain in sub_domains:
            domain = domain.strip("\n")
            if domain.startswith("*"):
                pass
            domains.append(domain)
        os.remove(target + ".txt")
        return domains
