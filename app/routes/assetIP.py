from bson import ObjectId
from flask_restplus import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser
from app.modules import ErrorMsg
from app import utils

ns = Namespace('asset_ip', description="资产组IP信息")

logger = get_logger()

base_search_fields = {
    'ip': fields.String(required=False, description="IP"),
    'domain': fields.String(description="域名"),
    'port_info.port_id': fields.Integer(description="端口号"),
    'port_info.service_name': fields.String(description="系统服务名称"),
    'port_info.version': fields.String(description="系统服务版本"),
    'port_info.product': fields.String(description="产品"),
    'os_info.name': fields.String(description="操作系统名称"),
    "task_id": fields.String(description="任务ID"),
    "update_date__dgt": fields.String(description="更新时间大于"),
    "update_date__dlt": fields.String(description="更新时间小于"),
    "scope_id": fields.String(description="资产范围ID"),
    "ip_type": fields.String(description="IP类型，公网(PUBLIC)和内网(PRIVATE)"),
    "cdn_name": fields.String(description="CDN 厂商名称")
}

base_search_fields.update(base_query_fields)


@ns.route('/')
class ARLAssetIP(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        IP信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='asset_ip')

        return data


@ns.route('/export/')
class ARLAssetIPExport(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        资产分组端口导出
        """
        args = self.parser.parse_args()
        response = self.send_export_file(args=args, _type="asset_ip")

        return response


delete_ip_fields = ns.model('deleteAssetIP',  {
    '_id': fields.List(fields.String(required=True, description="数据_id"))
})


@ns.route('/delete/')
class DeleteARLAssetIP(ARLResource):
    @auth
    @ns.expect(delete_ip_fields)
    def post(self):
        """
        删除资产组中的IP
        """
        args = self.parse_args(delete_ip_fields)
        id_list = args.pop('_id', "")
        for _id in id_list:
            query = {'_id': ObjectId(_id)}
            utils.conn_db('asset_ip').delete_one(query)

        return utils.build_ret(ErrorMsg.Success, {'_id': id_list})