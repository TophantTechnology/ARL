from bson import ObjectId
from flask_restx import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser
from app import utils
from app.modules import ErrorMsg

ns = Namespace('fileleak', description="文件泄漏信息")

logger = get_logger()

base_search_fields = {
    'url': fields.String(required=False, description="URL"),
    'site': fields.String(description="站点"),
    'content_length': fields.Integer(description="body 长度"),
    'status_code': fields.Integer(description="状态码"),
    'title': fields.String(description="标题"),
    "task_id": fields.String(description="任务ID")
}

base_search_fields.update(base_query_fields)


@ns.route('/')
class ARLFileLeak(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        文件泄露信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='fileleak')

        return data


delete_fileleak_fields = ns.model('deleteFileleakFields',  {
    '_id': fields.List(fields.String(required=True, description="文件泄漏 _id"))
})


@ns.route('/delete/')
class DeleteARLFileleak(ARLResource):
    @auth
    @ns.expect(delete_fileleak_fields)
    def post(self):
        """
        删除 文件泄漏
        """
        args = self.parse_args(delete_fileleak_fields)
        id_list = args.pop('_id', [])
        for _id in id_list:
            query = {'_id': ObjectId(_id)}
            utils.conn_db('fileleak').delete_one(query)

        return utils.build_ret(ErrorMsg.Success, {'_id': id_list})

