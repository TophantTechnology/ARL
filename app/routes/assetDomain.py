from bson import ObjectId
from flask_restplus import Resource, Api, reqparse, fields, Namespace
from app import utils
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser
from app.modules import ErrorMsg, CeleryAction
from app import celerytask

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
        domain = args.pop("domain")
        scope_id = args.pop("scope_id")
        if not utils.is_valid_domain(domain):
            return utils.build_ret(ErrorMsg.DomainInvalid, {"domain": domain})

        scope_data = utils.conn_db('asset_scope').find_one({"_id": ObjectId(scope_id)})
        if not scope_data:
            return utils.build_ret(ErrorMsg.NotFoundScopeID, {"scope_id": scope_id})

        if utils.get_fld(domain) not in scope_data["scope"]:
            return utils.build_ret(ErrorMsg.DomainNotFoundViaScope, {"domain": domain})

        domain_data = utils.conn_db("asset_domain").find_one({"domain": domain, "scope_id": scope_id})
        if domain_data:
            return utils.build_ret(ErrorMsg.DomainInScope, {"domain": domain})

        options = {
            "celery_action": CeleryAction.ADD_DOMAIN_TO_SCOPE,
            "data": {
                "domain": domain,
                "scope_id": scope_id
            }
        }
        celerytask.arl_task.delay(options=options)
        return utils.build_ret(ErrorMsg.Success, options["data"])


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