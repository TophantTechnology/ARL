import re
from bson import ObjectId
from flask_restx import Resource, Api, reqparse, fields, Namespace
from app import utils
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser
from app.modules import ErrorMsg
from app.helpers import submit_task_task, get_ip_domain_list, get_options_by_policy_id
from app.modules import TaskTag

ns = Namespace('asset_domain', description="资产组域名信息")

logger = get_logger()

base_search_fields = {
    'domain': fields.String(required=False, description="域名"),
    'record': fields.String(description="解析值"),
    'type': fields.String(description="解析类型"),
    'ips': fields.String(description="IP"),
    'source': fields.String(description="来源"),
    "task_id": fields.String(description="来源任务 ID"),
    "update_date__dgt": fields.String(description="更新时间大于"),
    "update_date__dlt": fields.String(description="更新时间小于"),
    'scope_id': fields.String(description="范围 ID")
}

base_search_fields.update(base_query_fields)


add_domain_fields = ns.model('addAssetDomain',  {
    'domain': fields.String(required=True, description="域名"),
    'scope_id': fields.String(required=True, description="资产组范围ID"),
    'policy_id': fields.String(description="策略 ID"),
})


@ns.route('/')
class ARLAssetDomain(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        域名信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='asset_domain')

        return data

    @auth
    @ns.expect(add_domain_fields)
    def post(self):
        """
        添加域名到资产组中
        """
        args = self.parse_args(add_domain_fields)
        raw_domain = args.pop("domain")
        scope_id = args.pop("scope_id")
        policy_id = args.pop("policy_id")

        try:
            _, domain_list = get_ip_domain_list(raw_domain)
        except Exception as e:
            return utils.build_ret(ErrorMsg.Error, {"error": str(e)})

        scope_data = utils.conn_db('asset_scope').find_one({"_id": ObjectId(scope_id)})
        if not scope_data:
            return utils.build_ret(ErrorMsg.NotFoundScopeID, {"scope_id": scope_id})

        scope_type = scope_data.get("scope_type", "domain")
        if scope_type != 'domain':
            return utils.build_ret(ErrorMsg.Error, {"error": "目前仅域名资产组可添加子域名"})

        domain_in_scope_list = []
        add_domain_list = []
        for domain in domain_list:
            if utils.get_fld(domain) not in scope_data["scope"]:
                return utils.build_ret(ErrorMsg.DomainNotFoundViaScope, {"domain": domain})

            domain_data = utils.conn_db("asset_domain").find_one({"domain": domain, "scope_id": scope_id})
            if domain_data:
                domain_in_scope_list.append(domain)
                continue
            add_domain_list.append(domain)

        ret_data = {
            "domain": ",".join(add_domain_list),
            "scope_id": scope_id,
            "domain_in_scope": ",".join(domain_in_scope_list),
            "add_domain_len": len(add_domain_list)
        }

        if len(add_domain_list) == 0:
            return utils.build_ret(ErrorMsg.DomainNotFoundNotInScope, ret_data)

        target = " ".join(add_domain_list)
        name = "添加域名-{}".format(scope_data["name"])

        options = {
            'domain_brute': True,
            'domain_brute_type': 'test',
            'port_scan_type': 'test',
            'port_scan': True,
            'service_detection': False,
            'service_brute': False,
            'os_detection': False,
            'site_identify': False,
            'site_capture': False,
            'file_leak': False,
            'alt_dns': False,
            'site_spider': False,
            'search_engines': False,
            'ssl_cert': False,
            'fofa_search': False,
            'dns_query_plugin': False,
            'related_scope_id': scope_id
        }

        try:
            if policy_id and len(policy_id) == 24:
                policy_options = get_options_by_policy_id(policy_id=policy_id, task_tag=TaskTag.TASK)
                if policy_options:
                    policy_options["related_scope_id"] = scope_id
                    options.update(policy_options)

            submit_task_task(target=target, name=name, options=options)
        except Exception as e:
            logger.exception(e)
            return utils.build_ret(ErrorMsg.Error, {"error": str(e)})

        return utils.build_ret(ErrorMsg.Success, ret_data)


delete_domain_fields = ns.model('deleteAssetDomain',  {
    '_id': fields.List(fields.String(required=True, description="数据_id"))
})


@ns.route('/delete/')
class DeleteARLAssetDomain(ARLResource):
    @auth
    @ns.expect(delete_domain_fields)
    def post(self):
        """
        删除资产组中的域名
        """
        args = self.parse_args(delete_domain_fields)
        id_list = args.pop('_id', "")
        for _id in id_list:
            query = {'_id': ObjectId(_id)}
            utils.conn_db('asset_domain').delete_one(query)

        return utils.build_ret(ErrorMsg.Success, {'_id': id_list})


@ns.route('/export/')
class ARLAssetDomainExport(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        资产分组域名导出
        """
        args = self.parser.parse_args()
        response = self.send_export_file(args=args, _type="asset_domain")

        return response
