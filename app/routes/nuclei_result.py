from bson import ObjectId
from flask_restx import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser
from app import utils
from app.modules import ErrorMsg

ns = Namespace('nuclei_result', description="nuclei 扫描结果")

logger = get_logger()

base_search_fields = {
    'template_url': fields.String(required=False, description="模版文件URL"),
    'template_id': fields.String(description="模版id"),
    'vuln_name': fields.String(description="漏洞名称"),
    'vuln_severity': fields.String(description="漏洞等级"),
    'vuln_url': fields.String(description="漏洞URL"),
    'curl_command': fields.String(description="curl 命令"),
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
        nuclei 扫描结果查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='nuclei_result')

        return data


delete_nuclei_result_fields = ns.model('deleteNucleiResultFields',  {
    '_id': fields.List(fields.String(required=True, description="nuclei 扫描结果 _id"))
})


@ns.route('/delete/')
class DeleteNucleiResult(ARLResource):
    @auth
    @ns.expect(delete_nuclei_result_fields)
    def post(self):
        """
        删除 nuclei 扫描结果
        """
        args = self.parse_args(delete_nuclei_result_fields)
        id_list = args.pop('_id', [])
        for _id in id_list:
            query = {'_id': ObjectId(_id)}
            utils.conn_db('nuclei_result').delete_one(query)

        return utils.build_ret(ErrorMsg.Success, {'_id': id_list})

