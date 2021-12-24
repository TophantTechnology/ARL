import time
from flask_restplus import Resource, Api, reqparse, fields, Namespace
from app.utils import auth
from app import utils
from . import ARLResource

ns = Namespace('batch_export', description="批量导出")


batch_export_fields = ns.model('BatchExport',  {
    "task_id": fields.List(fields.String(description="任务 ID"), required=True),
})


@ns.route('/site/')
class BatchExportSite(ARLResource):

    @auth
    @ns.expect(batch_export_fields)
    def post(self):
        """
        站点批量导出
        """
        args = self.parse_args(batch_export_fields)
        task_id_list = args.pop("task_id", [])
        response = self.send_batch_export_file(task_id_list, "site")

        return response


@ns.route('/domain/')
class BatchExportDomain(ARLResource):

    @auth
    @ns.expect(batch_export_fields)
    def post(self):
        """
        域名批量导出
        """
        args = self.parse_args(batch_export_fields)
        task_id_list = args.get("task_id", [])

        response = self.send_batch_export_file(task_id_list, "domain")

        return response


@ns.route('/ip/')
class BatchExportIP(ARLResource):

    @auth
    @ns.expect(batch_export_fields)
    def post(self):
        """
        IP 批量导出
        """
        args = self.parse_args(batch_export_fields)
        task_id_list = args.get("task_id", [])

        response = self.send_batch_export_file(task_id_list, "ip")

        return response


@ns.route('/url/')
class BatchExportURL(ARLResource):

    @auth
    @ns.expect(batch_export_fields)
    def post(self):
        """
        URL 批量导出
        """
        args = self.parse_args(batch_export_fields)
        task_id_list = args.get("task_id", [])

        response = self.send_batch_export_file(task_id_list, "url")

        return response


@ns.route('/ip_port/')
class BatchExportIpPort(ARLResource):

    @auth
    @ns.expect(batch_export_fields)
    def post(self):
        """
        IP 端口批量导出
        """
        args = self.parse_args(batch_export_fields)
        task_id_list = args.get("task_id", [])

        items_set = set()
        for task_id in task_id_list:
            if not task_id:
                continue

            query = {"task_id": task_id}
            items = list(utils.conn_db('ip').find(query, {"ip": 1, "port_info": 1}))

            for item in items:
                curr_ip = item["ip"]
                for port_info in item.get("port_info", []):
                    items_set.add("{}:{}".format(curr_ip, port_info["port_id"]))

        response = self.send_file(items_set, "ip_port")

        return response


@ns.route('/cip/')
class BatchExportCIP(ARLResource):

    @auth
    @ns.expect(batch_export_fields)
    def post(self):
        """
        C段 批量导出
        """
        args = self.parse_args(batch_export_fields)
        task_id_list = args.get("task_id", [])

        response = self.send_batch_export_file(task_id_list, "cip")

        return response


scope_batch_export_fields = ns.model('ScopeBatchExport',  {
    "scope_id": fields.List(fields.String(description="资产分组 ID"), required=True),
})


@ns.route('/asset_ip/')
class BatchExportAssetIP(ARLResource):

    @auth
    @ns.expect(scope_batch_export_fields)
    def post(self):
        """
        资产分组中IP批量导出
        """
        args = self.parse_args(scope_batch_export_fields)
        scope_id_list = args.get("scope_id", [])

        response = self.send_scope_batch_export_file(scope_id_list, "asset_ip")

        return response


@ns.route('/asset_domain/')
class BatchExportAssetIP(ARLResource):

    @auth
    @ns.expect(scope_batch_export_fields)
    def post(self):
        """
        资产分组中域名批量导出
        """
        args = self.parse_args(scope_batch_export_fields)
        scope_id_list = args.get("scope_id", [])

        response = self.send_scope_batch_export_file(scope_id_list, "asset_domain")

        return response


@ns.route('/asset_site/')
class BatchExportAssetIP(ARLResource):

    @auth
    @ns.expect(scope_batch_export_fields)
    def post(self):
        """
        资产分组中站点批量导出
        """
        args = self.parse_args(scope_batch_export_fields)
        scope_id_list = args.get("scope_id", [])

        response = self.send_scope_batch_export_file(scope_id_list, "asset_site")

        return response
