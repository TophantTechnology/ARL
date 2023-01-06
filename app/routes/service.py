from flask_restx import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser

ns = Namespace('service', description="系统服务信息")

logger = get_logger()

base_search_fields = {
    'service_name': fields.String(description="系统服务名称"),
    'service_info.ip': fields.String(required=False, description="IP"),
    'service_info.port_id': fields.Integer(description="端口号"),
    'service_info.version': fields.String(description="系统服务版本"),
    'service_info.product': fields.String(description="产品"),
    "task_id": fields.String(description="任务ID")
}

base_search_fields.update(base_query_fields)


@ns.route('/')
class ARLService(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        服务信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='service')

        return data
