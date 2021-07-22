import re
from bson import ObjectId
from flask_restplus import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from app import utils
from . import base_query_fields, ARLResource, get_arl_parser
from app.utils import conn_db as conn
from app.modules import ErrorMsg, AssetScopeType

ns = Namespace('asset_scope', description="资产组范围")

logger = get_logger()

base_fields = {
    'name': fields.String(description="资产组名称"),
    'scope': fields.String(description="资产范围"),
    "black_scope": fields.String(description="资产黑名单"),
    "scope_type": fields.String(description="资产范围类别")
}

add_asset_scope_fields = ns.model('addAssetScope', base_fields)

base_fields.update({
    "_id": fields.String(description="资产范围 ID")
})

base_fields.update(base_query_fields)


@ns.route('/')
class ARLAssetScope(ARLResource):
    parser = get_arl_parser(base_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        资产组查看
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='asset_scope')

        return data

    @auth
    @ns.expect(add_asset_scope_fields)
    def post(self):
        """
        资产组添加
        """
        args = self.parse_args(add_asset_scope_fields)
        name = args.pop('name')
        scope = args.pop('scope')
        black_scope = args.pop('black_scope')
        scope_type = args.pop('scope_type')

        if scope_type not in [AssetScopeType.IP, AssetScopeType.DOMAIN]:
            scope_type = AssetScopeType.DOMAIN

        black_scope_array = []
        if black_scope:
            black_scope_array = re.split(r",|\s", black_scope)

        scope_array = re.split(r",|\s", scope)
        # 清除空白符
        scope_array = list(filter(None, scope_array))
        new_scope_array = []
        for x in scope_array:
            if scope_type == AssetScopeType.DOMAIN:
                if not utils.is_valid_domain(x):
                    return utils.build_ret(ErrorMsg.DomainInvalid, {"scope": x})

                new_scope_array.append(x)

            if scope_type == AssetScopeType.IP:
                transfer = utils.ip.transfer_ip_scope(x)
                if transfer is None:
                    return utils.build_ret(ErrorMsg.ScopeTypeIsNotIP, {"scope": x})

                new_scope_array.append(transfer)

        if not new_scope_array:
            return utils.build_ret(ErrorMsg.DomainInvalid, {"scope": ""})

        scope_data = {
            "name": name,
            "scope_type": scope_type,
            "scope": ",".join(new_scope_array),
            "scope_array": new_scope_array,
            "black_scope": black_scope,
            "black_scope_array": black_scope_array,
        }
        conn('asset_scope').insert(scope_data)

        scope_id = str(scope_data.pop("_id"))
        scope_data["scope_id"] = scope_id

        return utils.build_ret(ErrorMsg.Success, scope_data)


delete_task_get_fields = ns.model('DeleteScopeByID',  {
    'scope': fields.String(description="删除资产范围", required=True),
    'scope_id': fields.String(description="资产范围id", required=True)
})


delete_task_post_fields = ns.model('DeleteScope',  {
    'scope_id': fields.List(fields.String(description="删除资产范围", required=True), required=True)
})


@ns.route('/delete/')
class DeleteARLAssetScope(ARLResource):
    parser = get_arl_parser(delete_task_get_fields, location='args')

    _table = 'asset_scope'

    @auth
    @ns.expect(parser)
    def get(self):
        """
        针对资产组删除范围
        """
        args = self.parser.parse_args()
        scope = str(args.pop('scope', "")).lower()
        scope_id = str(args.pop('scope_id', "")).lower()

        scope_data = self.get_scope_data(scope_id)
        if not scope_data:
            return utils.build_ret(ErrorMsg.NotFoundScopeID, {"scope_id": scope_id})

        query = {'_id': ObjectId(scope_id)}
        if scope not in scope_data.get("scope_array", []):
            return utils.build_ret(ErrorMsg.NotFoundScope, {"scope_id": scope_id, "scope":scope})

        scope_data["scope_array"].remove(scope)
        scope_data["scope"] = ",".join(scope_data["scope_array"])
        utils.conn_db(self._table).find_one_and_replace(query, scope_data)

        return utils.build_ret(ErrorMsg.Success, {"scope_id": scope_id, "scope":scope})

    def get_scope_data(self, scope_id):
        query = {'_id': ObjectId(scope_id)}
        scope_data = utils.conn_db(self._table).find_one(query)
        return scope_data

    @auth
    @ns.expect(delete_task_post_fields)
    def post(self):
        """
        删除资产组和资产组中的资产
        """
        args = self.parse_args(delete_task_post_fields)
        scope_id_list = args.pop('scope_id')
        for scope_id in scope_id_list:
            if not self.get_scope_data(scope_id):
                return utils.build_ret(ErrorMsg.NotFoundScopeID, {"scope_id": scope_id})

        table_list = ["asset_domain", "asset_site", "asset_ip", "scheduler"]

        for scope_id in scope_id_list:
            utils.conn_db(self._table).delete_many({'_id': ObjectId(scope_id)})

            for name in table_list:
                utils.conn_db(name).delete_many({'scope_id': scope_id})

        return utils.build_ret(ErrorMsg.Success, {"scope_id": scope_id_list})


add_scope_fields = ns.model('AddScope',  {
    'scope': fields.String(description="添加资产范围"),
    "scope_id": fields.String(description="添加资产范围")
})


@ns.route('/add/')
class AddARLAssetScope(ARLResource):
    @auth
    @ns.expect(add_scope_fields)
    def post(self):
        """
        添加资产范围
        """
        args = self.parse_args(add_scope_fields)
        scope = str(args.pop('scope', "")).lower()

        scope_id = args.pop('scope_id', "")

        table = 'asset_scope'
        query = {'_id': ObjectId(scope_id)}
        scope_data = utils.conn_db(table).find_one(query)
        if not scope_data:
            return utils.build_ret(ErrorMsg.NotFoundScopeID, {"scope_id": scope_id, "scope": scope})

        scope_type = scope_data.get("scope_type")
        if scope_type not in [AssetScopeType.IP, AssetScopeType.DOMAIN]:
            scope_type = AssetScopeType.DOMAIN

        scope_array = re.split(r",|\s", scope)
        # 清除空白符
        scope_array = list(filter(None, scope_array))
        if not scope_array:
            return utils.build_ret(ErrorMsg.DomainInvalid, {"scope": ""})

        for x in scope_array:
            new_scope = x
            if scope_type == AssetScopeType.DOMAIN:
                if not utils.is_valid_domain(x):
                    return utils.build_ret(ErrorMsg.DomainInvalid, {"scope": x})

            if scope_type == AssetScopeType.IP:
                transfer = utils.ip.transfer_ip_scope(x)
                if transfer is None:
                    return utils.build_ret(ErrorMsg.ScopeTypeIsNotIP, {"scope": x})
                new_scope = transfer

            if new_scope in scope_data.get("scope_array", []):
                return utils.build_ret(ErrorMsg.ExistScope, {"scope_id": scope_id, "scope": x})

            scope_data["scope_array"].append(new_scope)

        scope_data["scope"] = ",".join(scope_data["scope_array"])
        utils.conn_db(table).find_one_and_replace(query, scope_data)

        return utils.build_ret(ErrorMsg.Success, {"scope_id": scope_id, "scope": scope})