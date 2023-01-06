from flask_restx import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser

ns = Namespace('npoc_service', description="系统服务(python)信息")

logger = get_logger()

base_search_fields = {
    'scheme': fields.String(description="系统服务名称"),
    'host': fields.String(required=False, description="host"),
    'port': fields.String(description="端口号"),
    'target': fields.String(description="目标"),
    "task_id": fields.String(description="任务ID")
}

base_search_fields.update(base_query_fields)


@ns.route('/')
class NpocService(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        服务信息(python)查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='npoc_service')

        return data
