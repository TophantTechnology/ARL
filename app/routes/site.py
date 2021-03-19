import copy
from flask_restplus import Resource, Api, reqparse, fields, Namespace
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
