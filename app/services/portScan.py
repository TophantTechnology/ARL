from app import utils
from app.utils import nmap
from app.config import Config

logger = utils.get_logger()


class PortScan:
    def __init__(self, targets, ports=None, service_detect = False, os_detect = False):
        self.targets = " ".join(targets)
        self.ports = ports
        self.alive_port = "22,80,443,3389,8007-8011,8443,9090,8080-8091,8093,8099,5000-5004,2222,3306,1433,21,25"
        self.nmap_arguments = "-sS -n --open --defeat-rst-ratelimit"
        self.max_retries = 3
        self.host_timeout = 60*5
        if service_detect:
            self.host_timeout += 60 * 5
            self.nmap_arguments += " -sV"

        if os_detect:
            self.host_timeout += 60 * 4
            self.nmap_arguments += " -O"

        if len(self.ports.split(",")) > 60:
            self.nmap_arguments += " -PE -PS{}".format(self.alive_port)
            self.max_retries = 2
        else:
            if self.ports != "0-65535":
                self.nmap_arguments += " -Pn"

        if self.ports == "0-65535":
            self.nmap_arguments += " -PE -PS{}".format(self.alive_port)
            self.host_timeout += 60 * 20
            self.max_retries = 2

        self.nmap_arguments += " --max-rtt-timeout 320ms  --initial-rtt-timeout 100ms"
        self.nmap_arguments += " --min-rate 64"
        self.nmap_arguments += " --script-timeout 6s"
        self.nmap_arguments += " --host-timeout {}s".format(self.host_timeout)
        self.nmap_arguments += " --min-hostgroup 64 --min-parallelism 64"
        self.nmap_arguments += " --max-retries {}".format(self.max_retries)

    def run(self):
        logger.info("nmap target {}  ports {}  arguments {}".format(
            self.targets[:20], self.ports[:20], self.nmap_arguments))
        nm = nmap.PortScanner()
        nm.scan(hosts=self.targets, ports=self.ports, arguments=self.nmap_arguments)
        ip_info_list = []
        for host in nm.all_hosts():
            port_info_list = []
            for proto in nm[host].all_protocols():
                for port in nm[host][proto]:
                    port_info = nm[host][proto][port]
                    item = {
                        "port_id": port,
                        "service_name": port_info["name"],
                        "version": port_info["version"],
                        "product": port_info["product"],
                        "protocol": proto
                    }

                    port_info_list.append(item)

            osmatch_list = nm[host].get("osmatch", [])
            os_info = self.os_match_by_accuracy(osmatch_list)

            ip_info = {
                "ip": host,
                "port_info": port_info_list,
                "os_info": os_info
            }
            ip_info_list.append(ip_info)

        return ip_info_list

    def os_match_by_accuracy(self, os_match_list):
        for os_match in os_match_list:
            accuracy = os_match.get('accuracy', '0')
            if int(accuracy) > 90:
                return os_match

        return {}


def port_scan(targets, ports=Config.TOP_10, service_detect=False, os_detect=False):
    targets = list(set(targets))
    targets = list(filter(utils.not_in_black_ips, targets))
    ps = PortScan(targets, ports, service_detect, os_detect)
    return ps.run()