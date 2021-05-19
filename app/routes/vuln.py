from flask_restplus import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser

ns = Namespace('vuln', description="漏洞信息")

logger = get_logger()

base_search_fields = {
    'plg_name': fields.String(required=False, description="plugin ID"),
    'plg_type': fields.String(description="类别"),
    'vul_name': fields.String(description="漏洞名称"),
    'app_name': fields.String(description="应用名"),
    'target': fields.String(description="目标"),
    "task_id": fields.String(description="任务ID")
}

base_search_fields.update(base_query_fields)


@ns.route('/')
class ARLUrl(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        URL信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='vuln')

        return data



