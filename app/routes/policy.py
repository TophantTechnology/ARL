from flask_restplus import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser
from app.modules import ErrorMsg
from app import utils
from bson import ObjectId

ns = Namespace('policy', description="策略信息")

logger = get_logger()

base_search_fields = {
    'name': fields.String(required=False, description="策略名称"),
    "_id": fields.String(description="策略ID")
}

base_search_fields.update(base_query_fields)


@ns.route('/')
class ARLPolicy(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        策略信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='policy')

        return data


'''域名相关配置选项'''
domain_config_fields = ns.model('domainConfig', {
    "domain_brute": fields.Boolean(description="域名爆破", default=True),
    "domain_brute_type": fields.String(description="域名爆破类型(big)", example="big"),
    "alt_dns": fields.Boolean(description="DNS字典智能生成", default=True),
    "riskiq_search": fields.Boolean(description="RiskIQ 调用", default=True),
    "arl_search": fields.Boolean(description="ARL 历史查询", default=True),
    "crtsh_search": fields.Boolean(description="crtsh 查询", default=True)
})

'''IP 相关配置选项'''
ip_config_fields = ns.model('ipConfig', {
    "port_scan": fields.Boolean(description="端口扫描", default=True),
    "port_scan_type": fields.String(description="端口扫描类型(test|top100|top1000|all|custom)", example="test"),
    "service_detection": fields.Boolean(description="服务识别", default=False),
    "os_detection": fields.Boolean(description="操作系统识别", default=False),
    "ssl_cert": fields.Boolean(description="SSL 证书获取", default=False),
    "skip_scan_cdn_ip": fields.Boolean(description="跳过 CDN IP扫描", default=True),  # 这个参数强制生效
    "port_custom": fields.String(description="自定义扫描端口", default="80,443"),  # 仅端口扫描类型为 custom 时生效
    "host_timeout_type": fields.String(description="主机超时时间类别（default|custom）", default="default"),
    "host_timeout": fields.Integer(description="主机超时时间(s)", default=900),
    "port_parallelism": fields.Integer(description="探测报文并行度", default=32),
    "port_min_rate": fields.Integer(description="最少发包速率", default=60)
})

'''站点相关配置选项'''
site_config_fields = ns.model('siteConfig', {
    "site_identify": fields.Boolean(description="站点识别", default=False),
    "site_capture": fields.Boolean(description="站点截图", default=False),
    "search_engines": fields.Boolean(description="搜索引擎调用", default=False),
    "site_spider": fields.Boolean(description="站点爬虫", default=False),
})


'''资产组关联配置'''
scope_config_fields = ns.model('scopeConfig', {
    "scope_id": fields.String(description="资产分组 ID", default=""),
})


add_policy_fields = ns.model('addPolicy',  {
    "name": fields.String(required=True, description="策略名称"),
    "desc": fields.String(description="策略描述信息"),
    "policy": fields.Nested(ns.model("policy", {
            "domain_config": fields.Nested(domain_config_fields),
            "ip_config": fields.Nested(ip_config_fields),
            "site_config": fields.Nested(site_config_fields),
            "file_leak": fields.Boolean(description="文件泄漏", default=False),
            "npoc_service_detection": fields.Boolean(description="服务识别（纯python实现）", default=False),
            "poc_config": fields.List(fields.Nested(ns.model('pocConfig', {
                "plugin_name": fields.String(description="poc 插件名称ID", default=False),
                "enable": fields.Boolean(description="是否启用", default=True)
            }))),
            "brute_config": fields.List(fields.Nested(ns.model('bruteConfig', {
                "plugin_name": fields.String(description="poc 插件名称ID", default=False),
                "enable": fields.Boolean(description="是否启用", default=True)
            }))),
            "scope_config": fields.Nested(scope_config_fields)
        }, required=True)
    )
})


@ns.route('/add/')
class AddARLPolicy(ARLResource):

    @auth
    @ns.expect(add_policy_fields)
    def post(self):
        """
        策略添加
        """
        args = self.parse_args(add_policy_fields)
        name = args.pop("name")
        policy = args.pop("policy", {})
        if policy is None:
            return utils.build_ret("Missing policy parameter", {})

        domain_config = policy.pop("domain_config", {})
        domain_config = self._update_arg(domain_config, domain_config_fields)
        ip_config = policy.pop("ip_config", {})
        port_scan_type = ip_config.get("port_scan_type", "test")
        if port_scan_type == "custom":
            port_custom = ip_config.get("port_custom", "80,443")
            port_list = utils.arl.build_port_custom(port_custom)
            if isinstance(port_list, str):
                return utils.build_ret(ErrorMsg.PortCustomInvalid, {"port_custom": port_list})

            ip_config["port_custom"] = ",".join(port_list)

        ip_config = self._update_arg(ip_config, ip_config_fields)

        site_config = policy.pop("site_config", {})
        site_config = self._update_arg(site_config, site_config_fields)

        poc_config = policy.pop("poc_config", [])
        if poc_config is None:
            poc_config = []

        poc_config = _update_plugin_config(poc_config)
        if isinstance(poc_config, str):
            return utils.build_ret(poc_config, {})

        brute_config = policy.pop("brute_config", [])
        if brute_config is None:
            brute_config = []
        brute_config = _update_plugin_config(brute_config)
        if isinstance(brute_config, str):
            return utils.build_ret(brute_config, {})

        file_leak = fields.boolean(policy.pop("file_leak", False))
        npoc_service_detection = fields.boolean(policy.pop("npoc_service_detection", False))
        desc = args.pop("desc", "")

        # 只要获得关联资产组的配置
        scope_config = policy.pop("scope_config", {})
        scope_config = self._update_arg(scope_config, scope_config_fields)

        item = {
            "name": name,
            "policy": {
                "domain_config": domain_config,
                "ip_config": ip_config,
                "site_config": site_config,
                "poc_config": poc_config,
                "brute_config": brute_config,
                "file_leak": file_leak,
                "npoc_service_detection": npoc_service_detection,
                "scope_config": scope_config
            },
            "desc": desc,
            "update_date": utils.curr_date()
        }
        utils.conn_db("policy").insert_one(item)

        return utils.build_ret(ErrorMsg.Success, {"policy_id": str(item["_id"])})

    def _update_arg(self, arg_dict, default_module):
        default_dict = get_dict_default_from_module(default_module)
        if arg_dict is None:
            return default_dict

        default_dict.update(arg_dict)

        for x in default_dict:
            default_dict[x] = default_module[x].format(default_dict[x])

        return default_dict


def plugin_name_in_arl(name):
    query = {
        "plugin_name": name
    }
    item = utils.conn_db('poc').find_one(query)
    return item


def get_dict_default_from_module(module):
    ret = {}
    for x in module:
        v = module[x]
        ret[x] = None
        if v.default is not None:
            ret[x] = v.default

        if v.example is not None:
            ret[x] = v.example

    return ret


delete_policy_fields = ns.model('DeletePolicy',  {
    'policy_id': fields.List(fields.String(required=True, description="策略ID", example="603c65316591e73dd717d176"))
})


@ns.route('/delete/')
class DeletePolicy(ARLResource):
    @auth
    @ns.expect(delete_policy_fields)
    def post(self):
        """
        策略删除
        """
        args = self.parse_args(delete_policy_fields)
        policy_id_list = args.pop('policy_id')
        for policy_id in policy_id_list:
            if not policy_id:
                continue
            utils.conn_db('policy').delete_one({'_id': ObjectId(policy_id)})

        """这里直接返回成功了"""
        return utils.build_ret(ErrorMsg.Success, {})


edit_policy_fields = ns.model('editPolicy',  {
    'policy_id': fields.String(required=True, description="策略ID", example="603c65316591e73dd717d176"),
    'policy_data': fields.Nested(ns.model("policyData", {}))
})


@ns.route('/edit/')
class EditPolicy(ARLResource):
    @auth
    @ns.expect(edit_policy_fields)
    def post(self):
        """
        策略编辑
        """
        args = self.parse_args(edit_policy_fields)
        policy_id = args.pop('policy_id')
        policy_data = args.pop('policy_data', {})
        query = {'_id': ObjectId(policy_id)}
        item = utils.conn_db('policy').find_one(query)

        if not item:
            return utils.build_ret(ErrorMsg.PolicyIDNotFound, {})

        if not policy_data:
            return utils.build_ret(ErrorMsg.PolicyDataIsEmpty, {})
        item = change_dict(item, policy_data)

        poc_config = item["policy"].pop("poc_config", [])
        poc_config = _update_plugin_config(poc_config)
        if isinstance(poc_config, str):
            return utils.build_ret(poc_config, {})
        item["policy"]["poc_config"] = poc_config

        brute_config = item["policy"].pop("brute_config", [])
        brute_config = _update_plugin_config(brute_config)
        if isinstance(brute_config, str):
            return utils.build_ret(brute_config, {})
        item["policy"]["brute_config"] = brute_config

        item["update_date"] = utils.curr_date()
        utils.conn_db('policy').find_one_and_replace(query, item)
        item.pop('_id')

        return utils.build_ret(ErrorMsg.Success, {"data": item})


def _update_plugin_config(config):
    plugin_name_set = set()
    ret = []
    for item in config:
        plugin_name = str(item.get("plugin_name", ""))
        enable = item.get("enable", False)
        if plugin_name is None or enable is None:
            continue
        if plugin_name in plugin_name_set:
            continue

        plugin_info = plugin_name_in_arl(plugin_name)
        if not plugin_info:
            return "没有找到 {} 插件".format(plugin_name)

        config_item = {
            "plugin_name": plugin_name,
            "vul_name": plugin_info["vul_name"],
            "enable": bool(enable)
        }
        plugin_name_set.add(plugin_name)
        ret.append(config_item)

    return ret


def change_dict(old_data, new_data):
    if not isinstance(new_data, dict):
        return

    for key in old_data:
        if key in ["_id", "update_date"]:
            continue

        next_old_data = old_data[key]
        next_new_data = new_data.get(key)
        if next_new_data is None:
            continue

        next_new_data_type = type(next_new_data)
        next_old_data_type = type(next_old_data)

        if isinstance(next_old_data, dict):
            change_dict(next_old_data, next_new_data)

        elif isinstance(next_old_data, list) and isinstance(next_new_data, list):
            old_data[key] = next_new_data

        elif next_new_data_type == next_old_data_type:
            old_data[key] = next_new_data

    return old_data     # 返回data