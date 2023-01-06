from bson import ObjectId
from flask_restx import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from app import utils
from app.modules import ErrorMsg
from . import base_query_fields, ARLResource, get_arl_parser

ns = Namespace('domain', description="域名信息")

logger = get_logger()

base_search_fields = {
    'domain': fields.String(required=False, description="域名"),
    'record': fields.String(description="解析值"),
    'type': fields.String(description="解析类型"),
    'ips': fields.String(description="IP"),
    'source': fields.String(description="来源"),
    "task_id": fields.String(description="任务ID")
}

base_search_fields.update(base_query_fields)


@ns.route('/')
class ARLDomain(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        域名信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='domain')

        return data


@ns.route('/export/')
class ARLDomainExport(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        域名导出
        """
        args = self.parser.parse_args()
        response = self.send_export_file(args=args, _type="domain")

        return response


delete_domain_fields = ns.model('deleteDomainFields',  {
    '_id': fields.List(fields.String(required=True, description="域名 _id"))
})


@ns.route('/delete/')
class DeleteARLDomain(ARLResource):
    @auth
    @ns.expect(delete_domain_fields)
    def post(self):
        """
        删除 域名
        """
        args = self.parse_args(delete_domain_fields)
        id_list = args.pop('_id', [])
        for _id in id_list:
            query = {'_id': ObjectId(_id)}
            utils.conn_db('domain').delete_one(query)

        return utils.build_ret(ErrorMsg.Success, {'_id': id_list})
