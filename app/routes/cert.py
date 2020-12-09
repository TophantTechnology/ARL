from flask_restplus import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser

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
        data = self.build_data(args = args,  collection = 'cert')

        return data


