from bson import ObjectId
from flask_restx import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser
from app.services.npoc import NPoC
from app import utils, celerytask
from app.modules import ErrorMsg, TaskStatus, CeleryAction
import copy

ns = Namespace('poc', description="PoC信息")

logger = get_logger()

base_search_fields = {
    'plugin_name': fields.String(description="PoC 名称 ID"),
    'app_name': fields.String(description="应用名称"),
    'scheme': fields.String(description="支持的协议"),
    'vul_name': fields.String(description="漏洞名称"),
    'plugin_type': fields.String(description="插件类别", enum=['poc', 'brute']),
    'update_date': fields.String(description="更新时间"),
    'category': fields.String(description="PoC 分类")
}

base_search_fields.update(base_query_fields)


@ns.route('/')
class ARLPoC(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        PoC 信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args,  collection='poc')

        return data


@ns.route('/sync/')
class ARLPoCSync(ARLResource):

    @auth
    def get(self):
        """
        更新 PoC 信息
        """
        n = NPoC()
        plugin_cnt = len(n.plugin_name_list)
        n.sync_to_db()
        n.delete_db()

        return utils.build_ret(ErrorMsg.Success, {"plugin_cnt": plugin_cnt})


@ns.route('/delete/')
class ARLPoCDelete(ARLResource):

    @auth
    def get(self):
        """
        清空 PoC 信息
        """
        result = utils.conn_db('poc').delete_many({})

        delete_cnt = result.deleted_count

        return utils.build_ret(ErrorMsg.Success, {"delete_cnt": delete_cnt})


