import json
import os.path
import subprocess

from app.config import Config
from app import utils


logger = utils.get_logger()


class NucleiScan(object):
    def __init__(self, targets: list):
        self.targets = targets

        tmp_path = Config.TMP_PATH
        rand_str = utils.random_choices()

        self.nuclei_target_path = os.path.join(tmp_path,
                                               "nuclei_target_{}.txt".format(rand_str))

        self.nuclei_result_path = os.path.join(tmp_path,
                                               "nuclei_result_{}.json".format(rand_str))

        self.nuclei_bin_path = "nuclei"

        # 在nuclei 2.9.1 中 将-json 参数改成了 -jsonl 参数。
        self.nuclei_json_flag = None

    def _check_json_flag(self):
        json_flag = ["-json", "-jsonl"]
        for x in json_flag:
            command = [self.nuclei_bin_path, x]
            pro = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if pro.returncode == 0:
                self.nuclei_json_flag = x
                return

        assert self.nuclei_json_flag

    def _delete_file(self):
        try:
            os.unlink(self.nuclei_target_path)
            # 删除结果临时文件
            if os.path.exists(self.nuclei_result_path):
                os.unlink(self.nuclei_result_path)
        except Exception as e:
            logger.warning(e)

    def check_have_nuclei(self) -> bool:
        command = [self.nuclei_bin_path, "-version"]
        try:
            pro = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if pro.returncode == 0:
                return True
        except Exception as e:
            logger.debug("{}".format(str(e)))

        return False

    def _gen_target_file(self):
        with open(self.nuclei_target_path, "w") as f:
            for domain in self.targets:
                domain = domain.strip()
                if not domain:
                    continue
                f.write(domain + "\n")

    def dump_result(self) -> list:
        with open(self.nuclei_result_path, "r") as f:
            lines = f.readlines()

        results = []
        for line in lines:
            data = json.loads(line)
            item = {
                "template_url": data.get("template-url", ""),
                "template_id": data.get("template-id", ""),
                "vuln_name": data.get("info", {}).get("name", ""),
                "vuln_severity": data.get("info", {}).get("severity", ""),
                "vuln_url": data.get("matched-at", ""),
                "curl_command": data.get("curl-command", ""),
                "target": data.get("host", "")
            }
            results.append(item)

        return results

    def exec_nuclei(self):
        self._gen_target_file()

        command = [self.nuclei_bin_path, "-duc",
                   "-tags cve",
                   "-severity low,medium,high,critical",
                   "-type http",
                   "-l {}".format(self.nuclei_target_path),
                   self.nuclei_json_flag,  # 在nuclei 2.9.1 中 将 -json 参数改成了 -jsonl 参数
                   "-stats",
                   "-stats-interval 60",
                   "-o {}".format(self.nuclei_result_path),
                   ]

        logger.info(" ".join(command))
        utils.exec_system(command, timeout=12*60*60)

    def run(self):
        if not self.check_have_nuclei():
            logger.warning("not found nuclei")
            return []

        self._check_json_flag()

        self.exec_nuclei()

        results = self.dump_result()

        # 删除临时文件
        self._delete_file()

        return results


def nuclei_scan(targets: list):
    if not targets:
        return []

    n = NucleiScan(targets=targets)
    return n.run()

