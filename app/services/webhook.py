from bson import ObjectId, json_util
from app import utils
from app.config import Config
from app.helpers.asset_site import build_show_filed_map
import json

logger = utils.get_logger()


class BaseAssetWebHook(object):
    def __init__(self, task_id: str, scope_id: str):
        self.task_id = task_id
        self.scope_id = scope_id
        self.limit_num = 100

    def get_domain_info(self):
        query = {
            "task_id": self.task_id
        }
        fields = ["domain", "record", "type", "ips"]
        show_map = build_show_filed_map(fields)
        items = utils.conn_db('domain').find(query, show_map).limit(self.limit_num)
        return list(items)

    def get_site_info(self):
        query = {
            "task_id": self.task_id
        }
        fields = ["site", "title", "status", "http_server", "body_length"]
        show_map = build_show_filed_map(fields)
        items = utils.conn_db('site').find(query, show_map).limit(self.limit_num)
        return list(items)

    def get_ip_info(self):
        query = {
            "task_id": self.task_id
        }
        fields = ["ip", "port_info", "ip_type", "geo_asn", "geo_city", "cdn_name"]
        show_map = build_show_filed_map(fields)
        items = utils.conn_db('ip').find(query, show_map).limit(self.limit_num)
        return list(items)

    def get_asset_scope_data(self):
        query = {
            "_id": ObjectId(self.scope_id)
        }
        fields = ["name", "scope_type"]
        show_map = build_show_filed_map(fields)
        item = utils.conn_db('asset_scope').find_one(query, show_map)
        if item:
            item.pop("_id")

        return item

    def get_task_data(self):
        query = {
            "_id": ObjectId(self.task_id)
        }
        fields = ["name", "target", "start_time", "status", "end_time", "options"]
        show_map = build_show_filed_map(fields)
        item = utils.conn_db('task').find_one(query, show_map)
        if item:
            item.pop("_id")
        return item


class DomainAssetWebHook(BaseAssetWebHook):
    def __init__(self, task_id: str, scope_id: str, web_hook_url: str, web_hook_token: str):
        super().__init__(task_id, scope_id)
        self.web_hook_url = web_hook_url
        self.web_hook_token = web_hook_token

    def build_data(self):
        data = {
            "type": "domain_monitor",
            "task_id": self.task_id,
            "task_data": self.get_task_data(),
            "scope_id": self.scope_id,
            "scope_data": self.get_asset_scope_data(),
            "asset": {
                "domain_info": self.get_domain_info(),
                "site_info": self.get_site_info(),
            }
        }

        return json.loads(json_util.dumps(data))

    def run_web_hook(self):
        headers = {
            "Token": self.web_hook_token
        }

        data = self.build_data()
        domain_info_list = data["asset"]["domain_info"]
        site_info_list = data["asset"]["site_info"]
        if domain_info_list or site_info_list:
            logger.info("send web_hook to {} domain_info:{}, site_info:{}".format(
                self.web_hook_url, len(domain_info_list), len(site_info_list)))
            utils.http_req(self.web_hook_url,
                           method="post",
                           json=self.build_data(),
                           headers=headers)


class IPAssetWebHook(BaseAssetWebHook):
    def __init__(self, task_id: str, scope_id: str, web_hook_url: str, web_hook_token: str):
        super().__init__(task_id, scope_id)
        self.web_hook_url = web_hook_url
        self.web_hook_token = web_hook_token

    def build_data(self):
        data = {
            "type": "ip_monitor",
            "task_id": self.task_id,
            "task_data": self.get_task_data(),
            "scope_id": self.scope_id,
            "scope_data": self.get_asset_scope_data(),
            "asset": {
                "ip_info": self.get_ip_info(),
                "site_info": self.get_site_info(),
            }
        }

        return json.loads(json_util.dumps(data))

    def run_web_hook(self):
        headers = {
            "Token": self.web_hook_token
        }

        data = self.build_data()
        ip_info_list = data["asset"]["ip_info"]
        site_info_list = data["asset"]["site_info"]
        if ip_info_list or site_info_list:
            logger.info("send web_hook to {} ip_info:{}, site_info:{}".format(
                self.web_hook_url, len(ip_info_list), len(site_info_list)))
            utils.http_req(self.web_hook_url,
                           method="post",
                           json=self.build_data(),
                           headers=headers)


class SiteAssetWebHook(BaseAssetWebHook):
    def __init__(self, task_id: str, scope_id: str, web_hook_url: str, web_hook_token: str):
        super().__init__(task_id, scope_id)
        self.web_hook_url = web_hook_url
        self.web_hook_token = web_hook_token

    def build_data(self):
        data = {
            "type": "site_monitor",
            "task_id": self.task_id,
            "task_data": self.get_task_data(),
            "scope_id": self.scope_id,
            "scope_data": self.get_asset_scope_data(),
            "asset": {
                "site_info": self.get_site_info(),
            }
        }

        return json.loads(json_util.dumps(data))

    def run_web_hook(self):
        headers = {
            "Token": self.web_hook_token
        }

        data = self.build_data()
        site_info_list = data["asset"]["site_info"]
        if site_info_list:
            logger.info("send web_hook to {} site_info:{}".format(
                self.web_hook_url, len(site_info_list)))
            utils.http_req(self.web_hook_url,
                           method="post",
                           json=self.build_data(),
                           headers=headers)


def domain_asset_web_hook(task_id: str, scope_id: str):
    try:
        url = Config.WEB_HOOK_URL
        token = Config.WEB_HOOK_TOKEN
        if url:
            d = DomainAssetWebHook(task_id=task_id, scope_id=scope_id,
                                   web_hook_url=url, web_hook_token=token)
            d.run_web_hook()
    except Exception as e:
        logger.error(str(e))


def ip_asset_web_hook(task_id: str, scope_id: str):
    try:
        url = Config.WEB_HOOK_URL
        token = Config.WEB_HOOK_TOKEN
        if url:
            d = IPAssetWebHook(task_id=task_id, scope_id=scope_id,
                               web_hook_url=url, web_hook_token=token)
            d.run_web_hook()
    except Exception as e:
        logger.error(str(e))


def site_asset_web_hook(task_id: str, scope_id: str):
    try:
        url = Config.WEB_HOOK_URL
        token = Config.WEB_HOOK_TOKEN
        if url:
            d = SiteAssetWebHook(task_id=task_id, scope_id=scope_id,
                                 web_hook_url=url, web_hook_token=token)
            d.run_web_hook()
    except Exception as e:
        logger.error(str(e))
