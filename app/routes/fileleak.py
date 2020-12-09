from flask_restplus import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser

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
