from bson import ObjectId
from flask_restplus import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser
from app.modules import ErrorMsg
from app import utils, services

ns = Namespace('asset_site', description="资产组站点信息")

logger = get_logger()

base_search_fields = {
    'site': fields.String(required=False, description="站点URL"),
    'hostname': fields.String(description="主机名"),
    'ip': fields.String(description="ip"),
    'title': fields.String(description="标题"),
    'http_server': fields.String(description="Web servers"),
    'headers': fields.String(description="headers"),
    'finger.name': fields.String(description="指纹"),
    'status': fields.Integer(description="状态码"),
    'favicon.hash': fields.Integer(description="favicon hash"),
    'task_id': fields.String(description="任务 ID"),
    'scope_id': fields.String(description="范围 ID"),
    "update_date__dgt": fields.String(description="更新时间大于"),
    "update_date__dlt": fields.String(description="更新时间小于")
}

site_search_fields = base_search_fields.copy()

base_search_fields.update(base_query_fields)

add_site_fields = ns.model('addAssetSite',  {
    'site': fields.String(required=True, description="站点"),
    'scope_id': fields.String(required=True, description="资产组范围ID"),
})


@ns.route('/')
class ARLDomain(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        域名信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='asset_site')

        return data

    @auth
    @ns.expect(add_site_fields)
    def post(self):
        """
        添加站点到资产组中
        """
        args = self.parse_args(add_site_fields)
        site = args.pop("site")
        scope_id = args.pop("scope_id")
        url = utils.normal_url(site).strip("/")
        if not url:
            return utils.build_ret(ErrorMsg.DomainInvalid, {"site": site})

        scope_data = utils.conn_db('asset_scope').find_one({"_id": ObjectId(scope_id)})
        if not scope_data:
            return utils.build_ret(ErrorMsg.NotFoundScopeID, {"scope_id": scope_id})

        fld = utils.get_fld(url)
        if not fld:
            return utils.build_ret(ErrorMsg.SiteURLNotDomain, {"site": url})

        if fld not in scope_data["scope"]:
            return utils.build_ret(ErrorMsg.DomainNotFoundViaScope, {"site": url})

        site_data = utils.conn_db('asset_site').find_one({"site": url, "scope_id": scope_id})
        if site_data:
            return utils.build_ret(ErrorMsg.SiteInScope, {"site": url})

        add_site_to_scope(url, scope_id)

        return utils.build_ret(ErrorMsg.Success, {"site": url})


@ns.route('/export/')
class ARLSiteExport(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        资产分组站点导出
        """
        args = self.parser.parse_args()
        response = self.send_export_file(args=args, _type="asset_site")

        return response


def add_site_to_scope(site, scope_id):
    fetch_site_data = services.fetch_site([site])
    web_analyze_data = services.web_analyze([site])
    finger = web_analyze_data.get(site, [])
    curr_date = utils.curr_date_obj()
    if fetch_site_data:
        item = fetch_site_data[0]
        item["finger"] = finger
        item["screenshot"] = ""
        item["scope_id"] = scope_id
        item["save_date"] = curr_date
        item["update_date"] = curr_date

        utils.conn_db('asset_site').insert_one(item)


delete_site_fields = ns.model('deleteAssetSite',  {
    '_id': fields.List(fields.String(required=True, description="数据_id"))
})


@ns.route('/delete/')
class DeleteARLAssetSite(ARLResource):
    @auth
    @ns.expect(delete_site_fields)
    def post(self):
        """
        删除资产组中的站点
        """
        args = self.parse_args(delete_site_fields)
        id_list = args.pop('_id', "")
        for _id in id_list:
            query = {'_id': ObjectId(_id)}
            utils.conn_db('asset_site').delete_one(query)

        return utils.build_ret(ErrorMsg.Success, {'_id': id_list})


@ns.route('/save_result_set/')
class ARLSaveResultSet(ARLResource):
    parser = get_arl_parser(site_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        保存资产站点到结果集
        """
        args = self.parser.parse_args()
        query = self.build_db_query(args)
        items = utils.conn_db('asset_site').distinct("site", query)

        items = list(set([utils.url.cut_filename(x) for x in items]))

        if len(items) == 0:
            return utils.build_ret(ErrorMsg.QueryResultIsEmpty, {})

        data = {
            "items": items,
            "type": "asset_site",
            "total": len(items)
        }
        result = utils.conn_db('result_set').insert_one(data)

        ret_data = {
            "result_set_id": str(result.inserted_id),
            "result_total": len(items),
            "type": "asset_site"
        }

        return utils.build_ret(ErrorMsg.Success, ret_data)
