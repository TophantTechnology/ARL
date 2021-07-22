from flask_restplus import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser

ns = Namespace('cip', description="C段 ip 统计信息")

logger = get_logger()

base_search_fields = {
    'cidr_ip': fields.String(required=False, description="C段"),
    "task_id": fields.String(description="任务 ID"),
    "ip_count": fields.Integer(description="IP 个数"),
    "domain_count": fields.Integer(description="解析到该 C 段域名个数")
}

base_search_fields.update(base_query_fields)


@ns.route('/')
class ARLFingerprint(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        C 段统计信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='cip')

        return data

