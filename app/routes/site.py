import copy
from bson import ObjectId
from flask_restx import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from app.modules import ErrorMsg
from app import utils
from . import base_query_fields, ARLResource, get_arl_parser


ns = Namespace('site', description="站点信息")

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
    'tag': fields.String(description="标签列表")
}

site_search_fields = copy.copy(base_search_fields)

base_search_fields.update(base_query_fields)


@ns.route('/')
class ARLSite(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        站点信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args = args,  collection = 'site')

        return data


@ns.route('/export/')
class ARLSiteExport(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        站点导出
        """
        args = self.parser.parse_args()
        response = self.send_export_file(args=args, _type="site")

        return response


@ns.route('/save_result_set/')
class ARLSaveResultSet(ARLResource):
    parser = get_arl_parser(site_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        保存站点结果集
        """
        args = self.parser.parse_args()
        query = self.build_db_query(args)
        items = utils.conn_db('site').distinct("site", query)

        items = list(set([utils.url.cut_filename(x) for x in items]))

        if len(items) == 0:
            return utils.build_ret(ErrorMsg.QueryResultIsEmpty, {})

        data = {
            "items": items,
            "type": "site",
            "total": len(items)
        }
        result = utils.conn_db('result_set').insert_one(data)

        ret_data = {
            "result_set_id": str(result.inserted_id),
            "result_total": len(items),
            "type": "site",
        }

        return utils.build_ret(ErrorMsg.Success, ret_data)


add_site_tag_fields = ns.model('AddSiteTagFields',  {
    "tag": fields.String(required=True, description="添加站点标签"),
    "_id": fields.String(description="站点ID", required=True)
})


@ns.route('/add_tag/')
class AddSiteTagARL(ARLResource):

    @auth
    @ns.expect(add_site_tag_fields)
    def post(self):
        """
        站点添加Tag
        """
        args = self.parse_args(add_site_tag_fields)
        site_id = args.pop("_id")
        tag = args.pop("tag")

        query = {"_id": ObjectId(site_id)}
        data = utils.conn_db('site').find_one(query)
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

        utils.conn_db('site').update_one(query, {"$set": {"tag": tag_list}})

        return utils.build_ret(ErrorMsg.Success, {"tag": tag})


delete_site_tag_fields = ns.model('DeleteSiteTagFields',  {
    "tag": fields.String(required=True, description="删除站点标签"),
    "_id": fields.String(description="站点ID", required=True)
})


@ns.route('/delete_tag/')
class DeleteSiteTagARL(ARLResource):

    @auth
    @ns.expect(delete_site_tag_fields)
    def post(self):
        """
        删除站点Tag
        """
        args = self.parse_args(delete_site_tag_fields)
        site_id = args.pop("_id")
        tag = args.pop("tag")

        query = {"_id": ObjectId(site_id)}
        data = utils.conn_db('site').find_one(query)
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

        utils.conn_db('site').update_one(query, {"$set": {"tag": tag_list}})

        return utils.build_ret(ErrorMsg.Success, {"tag": tag})


delete_site_fields = ns.model('deleteSiteFields',  {
    '_id': fields.List(fields.String(required=True, description="站点 _id"))
})


@ns.route('/delete/')
class DeleteARLSite(ARLResource):
    @auth
    @ns.expect(delete_site_fields)
    def post(self):
        """
        删除站点
        """
        args = self.parse_args(delete_site_fields)
        id_list = args.pop('_id', [])
        for _id in id_list:
            query = {'_id': ObjectId(_id)}
            utils.conn_db('site').delete_one(query)

        return utils.build_ret(ErrorMsg.Success, {'_id': id_list})