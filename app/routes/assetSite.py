from bson import ObjectId
from flask_restplus import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser
from app.modules import ErrorMsg, TaskTag
from app import utils, services
from app.helpers.asset_site import find_asset_site_not_in_scope
from app.helpers.task import target2list, submit_add_asset_site_task
from app.helpers.policy import get_options_by_policy_id

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
    "update_date__dlt": fields.String(description="更新时间小于"),
    'tag': fields.String(description="标签列表")
}

site_search_fields = base_search_fields.copy()

base_search_fields.update(base_query_fields)

add_site_fields = ns.model('addAssetSite',  {
    'site': fields.String(required=True, description="站点"),
    'scope_id': fields.String(required=True, description="资产组范围ID"),
    'policy_id': fields.String(description="策略 ID"),
})


@ns.route('/')
class ARLAssetSite(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        资产站点信息查询
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
        site = args.pop("site")  # 这里可能提交大量的
        scope_id = args.pop("scope_id")
        policy_id = args.pop("policy_id")

        scope_data = utils.conn_db('asset_scope').find_one({"_id": ObjectId(scope_id)})
        if not scope_data:
            return utils.build_ret(ErrorMsg.NotFoundScopeID, {"scope_id": scope_id})

        scope_type = scope_data.get("scope_type", "domain")
        if scope_type == "ip":
            return utils.build_ret(ErrorMsg.AddAssetSiteNotSupportIP, {})

        sites = target2list(site)
        if not sites:
            return utils.build_ret(ErrorMsg.URLInvalid, {"site": site})

        not_in_scope_sites = find_asset_site_not_in_scope(sites, scope_id)
        if not_in_scope_sites:
            return utils.build_ret(ErrorMsg.TaskTargetNotInScope, {"not_in_scope_sites": site})

        name = "添加站点-{}".format(scope_data["name"])

        options = {
            'site_identify': False,
            'site_capture': False,
            'file_leak': False,
            'site_spider': False,
            'search_engines': False,
            'related_scope_id': scope_id
        }

        try:
            if policy_id and len(policy_id) == 24:
                policy_options = get_options_by_policy_id(policy_id=policy_id, task_tag=TaskTag.RISK_CRUISING)
                if policy_options:
                    policy_options["related_scope_id"] = scope_id
                    options.update(policy_options)

            task_data = submit_add_asset_site_task(task_name=name, target=sites, options=options)
        except Exception as e:
            logger.exception(e)
            return utils.build_ret(ErrorMsg.Error, {"error": str(e)})

        return utils.build_ret(ErrorMsg.Success, task_data)


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


delete_asset_site_fields = ns.model('deleteAssetSite',  {
    '_id': fields.List(fields.String(required=True, description="站点 _id"))
})


@ns.route('/delete/')
class DeleteARLAssetSite(ARLResource):
    @auth
    @ns.expect(delete_asset_site_fields)
    def post(self):
        """
        删除资产组中的站点
        """
        args = self.parse_args(delete_asset_site_fields)
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


add_asset_site_tag_fields = ns.model('AddAssetSiteTagFields',  {
    "tag": fields.String(required=True, description="添加站点标签"),
    "_id": fields.String(description="资产站点ID", required=True)
})


@ns.route('/add_tag/')
class AddAssetSiteTagARL(ARLResource):

    @auth
    @ns.expect(add_asset_site_tag_fields)
    def post(self):
        """
        资产站点添加Tag
        """
        args = self.parse_args(add_asset_site_tag_fields)
        site_id = args.pop("_id")
        tag = args.pop("tag")

        query = {"_id": ObjectId(site_id)}
        data = utils.conn_db('asset_site').find_one(query)
        if not data:
            return utils.build_ret(ErrorMsg.SiteIdNotFound, {"site_id": site_id})

        tag_list = []
        old_tag = data.get("tag")
        if old_tag:
            if isinstance(old_tag, str):
                tag_list.append(old_tag)

            if isinstance(old_tag, list):
                tag_list.extend(old_tag)

        if tag in tag_list:
            return utils.build_ret(ErrorMsg.SiteTagIsExist, {"tag": tag})

        tag_list.append(tag)

        utils.conn_db('asset_site').update_one(query, {"$set": {"tag": tag_list}})

        return utils.build_ret(ErrorMsg.Success, {"tag": tag})


delete_asset_site_tag_fields = ns.model('delete_asset_site_tag_fields',  {
    "tag": fields.String(required=True, description="删除资产站点标签"),
    "_id": fields.String(description="资产站点ID", required=True)
})


@ns.route('/delete_tag/')
class DeleteAssetSiteTagARL(ARLResource):

    @auth
    @ns.expect(delete_asset_site_tag_fields)
    def post(self):
        """
        删除资产站点Tag
        """
        args = self.parse_args(delete_asset_site_tag_fields)
        site_id = args.pop("_id")
        tag = args.pop("tag")

        query = {"_id": ObjectId(site_id)}
        data = utils.conn_db('asset_site').find_one(query)
        if not data:
            return utils.build_ret(ErrorMsg.SiteIdNotFound, {"site_id": site_id})

        tag_list = []
        old_tag = data.get("tag")
        if old_tag:
            if isinstance(old_tag, str):
                tag_list.append(old_tag)

            if isinstance(old_tag, list):
                tag_list.extend(old_tag)

        if tag not in tag_list:
            return utils.build_ret(ErrorMsg.SiteTagNotExist, {"tag": tag})

        tag_list.remove(tag)

        utils.conn_db('asset_site').update_one(query, {"$set": {"tag": tag_list}})

        return utils.build_ret(ErrorMsg.Success, {"tag": tag})

