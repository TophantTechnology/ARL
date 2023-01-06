import os
import json
from xing.core import PluginType, PluginRunner
from xing.utils import load_plugins
from xing.conf import Conf as npoc_conf
from app import utils
from app.modules import PoCCategory
from app.config import Config

logger = utils.get_logger()


class NPoC(object):
    """docstring for ClassName"""

    def __init__(self, concurrency=6, tmp_dir="./"):
        super(NPoC, self).__init__()
        self._plugins = None
        self._poc_info_list = None
        self.concurrency = concurrency
        self._plugin_name_list = None
        self.plugin_name_set = set()
        self._db_plugin_name_list = None
        self.tmp_dir = tmp_dir
        self.runner = None
        self.result = []
        self.brute_plugin_name_set = set()
        self.poc_plugin_name_set = set()
        self.sniffer_plugin_name_set = set()

    @property
    def plugin_name_list(self) -> list:
        """ xing 中插件名称列表 """

        if self._plugin_name_list is None:
            # 触发下调用
            x = self.poc_info_list
            self._plugin_name_list = list(self.plugin_name_set)

        return self._plugin_name_list

    @property
    def db_plugin_name_list(self) -> list:
        """ 数据库中插件名称列表 """
        if self._db_plugin_name_list is None:
            self._db_plugin_name_list = []
            for item in utils.conn_db('poc').find({}):
                self._db_plugin_name_list.append(item["plugin_name"])

        return self._db_plugin_name_list

    @property
    def plugins(self) -> list:
        """ xing 中插件实例列表 """
        if self._plugins is None:
            self._plugins = self.load_all_poc()

        return self._plugins

    @property
    def poc_info_list(self) -> list:
        """ xing 中插件信息列表 """
        if self._poc_info_list is None:
            self._poc_info_list = self.gen_poc_info()

        return self._poc_info_list

    def load_all_poc(self):
        plugins = load_plugins(os.path.join(npoc_conf.PROJECT_DIRECTORY, "plugins"))
        pocs = []
        for plugin in plugins:
            if plugin.plugin_type == PluginType.POC:
                pocs.append(plugin)

            if plugin.plugin_type == PluginType.BRUTE:
                pocs.append(plugin)

            if plugin.plugin_type == PluginType.SNIFFER:
                pocs.append(plugin)

        return pocs

    def gen_poc_info(self):
        info_list = []
        for p in self.plugins:
            info = dict()
            info["plugin_name"] = getattr(p, "_plugin_name", "")
            if p.plugin_type == PluginType.SNIFFER:
                self.sniffer_plugin_name_set.add(info["plugin_name"])
                continue

            info["app_name"] = p.app_name
            info["scheme"] = ",".join(p.scheme)
            info["vul_name"] = p.vul_name
            info["plugin_type"] = p.plugin_type

            if p.plugin_type == PluginType.POC:
                info["category"] = PoCCategory.POC
                self.poc_plugin_name_set.add(info["plugin_name"])

            if p.plugin_type == PluginType.BRUTE:
                self.brute_plugin_name_set.add(info["plugin_name"])
                if "http" in info["scheme"]:
                    info["category"] = PoCCategory.WEBB_RUTE
                else:
                    info["category"] = PoCCategory.SYSTEM_BRUTE

            if info["plugin_name"] in self.plugin_name_set:
                logger.warning("plugin {} already exists".format(info["plugin_name"]))
                continue
            self.plugin_name_set.add(info["plugin_name"])
            info_list.append(info)

        return info_list

    def sync_to_db(self):
        for old in self.poc_info_list:
            new = old.copy()
            plugin_name = old["plugin_name"]
            new["update_date"] = utils.curr_date()
            if plugin_name in self.db_plugin_name_list:
                continue

            logger.info("insert {} info to db".format(plugin_name))
            utils.conn_db('poc').insert_one(new)

        return True

    def delete_db(self):
        for name in self.db_plugin_name_list:
            if name not in self.plugin_name_list:
                query = {"plugin_name": name}
                utils.conn_db('poc').delete_one(query)

        return True

    def run_poc(self, plugin_name_list, targets):
        self.result = []
        npoc_conf.SAVE_TEXT_RESULT_FILENAME = ""
        random_file = os.path.join(self.tmp_dir, "npoc_result_{}.txt".format(utils.random_choices()))
        npoc_conf.SAVE_JSON_RESULT_FILENAME = random_file
        plugins = self.filter_plugin_by_name(plugin_name_list)

        runner = PluginRunner.PluginRunner(plugins=plugins, targets=targets, concurrency=self.concurrency)
        self.runner = runner
        runner.run()

        if not os.path.exists(random_file):
            return self.result

        for item in utils.load_file(random_file):
            self.result.append(json.loads(item))

        os.unlink(random_file)

        return self.result

    def run_all_poc(self, targets):
        return self.run_poc(self.plugin_name_list, targets)

    def filter_plugin_by_name(self, plugin_name_list):
        plugins = []
        for plugin in self.plugins:
            curr_name = getattr(plugin, "_plugin_name", "")
            if not curr_name:
                continue
            if curr_name in plugin_name_list:
                plugins.append(plugin)
        return plugins


def sync_to_db(del_flag=False):
    n = NPoC()
    n.sync_to_db()
    if del_flag:
        n.delete_db()
    return True


def run_risk_cruising(plugins, targets):
    n = NPoC(tmp_dir=Config.TMP_PATH, concurrency=8)
    return n.run_poc(plugins, targets)


def run_sniffer(targets):
    n = NPoC(concurrency=15, tmp_dir=Config.TMP_PATH)
    x = n.plugin_name_list
    new_targets = []

    #  跳过80 和 443 的识别
    for t in targets:
        t = t.strip()
        if t.endswith(":80"):
            continue
        if t.endswith(":443"):
            continue
        new_targets.append(t)

    items = n.run_poc(n.sniffer_plugin_name_set, new_targets)
    ret = []
    for x in items:
        target = x["verify_data"]
        if "://" not in target:
            continue

        split = target.split("://")
        scheme = split[0]
        split = split[1].split(":")

        host = split[0]
        port = split[1]
        item = {
            "scheme": scheme,
            "host": host,
            "port": port,
            "target": target
        }
        ret.append(item)

    return ret
