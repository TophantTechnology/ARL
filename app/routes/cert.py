from bson import ObjectId
from flask_restx import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser
from app import utils
from app.modules import ErrorMsg

ns = Namespace('cert', description="证书信息")

logger = get_logger()

base_search_fields = {
    'ip': fields.String(description="ip"),
    'port': fields.Integer(description="端口"),
    'cert.subject_dn': fields.String(description="主题名称"),
    'cert.issuer_dn': fields.String(description="签发者名称"),
    'cert.serial_number ': fields.String(description="序列号"),
    'cert.validity.start': fields.String(description="开始时间"),
    'cert.validity.end': fields.String(description="结束时间"),
    'cert.fingerprint.sha256': fields.String(description="SHA-256"),
    'cert.fingerprint.sha1': fields.String(description="SHA-1"),
    'cert.fingerprint.md5': fields.String(description="MD5"),
    'cert.extensions.subjectAltName': fields.String(description="备用名称"),
    'task_id': fields.String(description="任务 ID"),
}

base_search_fields.update(base_query_fields)


@ns.route('/')
class ARLCert(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        SSL证书查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args,  collection='cert')

        return data


delete_cert_fields = ns.model('deleteCertFields',  {
    '_id': fields.List(fields.String(required=True, description="证书 _id"))
})


@ns.route('/delete/')
class DeleteARLCert(ARLResource):
    @auth
    @ns.expect(delete_cert_fields)
    def post(self):
        """
        删除 SSL 证书信息
        """
        args = self.parse_args(delete_cert_fields)
        id_list = args.pop('_id', [])
        for _id in id_list:
            query = {'_id': ObjectId(_id)}
            utils.conn_db('cert').delete_one(query)

        return utils.build_ret(ErrorMsg.Success, {'_id': id_list})