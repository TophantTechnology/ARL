import json
import time
import werkzeug
from urllib.parse import quote
from flask import make_response
from flask_restplus import Resource, Api, reqparse, fields, Namespace
from bson import ObjectId
from app.utils import get_logger, auth, parse_human_rule, transform_rule_map
from app import utils
from app.modules import ErrorMsg
from . import base_query_fields, ARLResource, get_arl_parser

ns = Namespace('fingerprint', description="指纹信息")

logger = get_logger()

base_search_fields = {
    'name': fields.String(required=False, description="名称"),
    "update_date__dgt": fields.String(description="更新时间大于"),
    "update_date__dlt": fields.String(description="更新时间小于")
}

base_search_fields.update(base_query_fields)


add_fingerprint_fields = ns.model('addFingerSite', {
    'name': fields.String(required=True, description="名称"),
    'human_rule': fields.String(required=True, description="规则"),
})


@ns.route('/')
class ARLFingerprint(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        指纹信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='fingerprint')

        return data

    @auth
    @ns.expect(add_fingerprint_fields)
    def post(self):
        """
        添加指纹信息
        """
        args = self.parse_args(add_fingerprint_fields)

        human_rule = args.pop('human_rule')
        name = args.pop('name')

        rule_map = parse_human_rule(human_rule)
        if rule_map is None:
            return utils.build_ret(ErrorMsg.RuleInvalid, {"rule": human_rule})

        data = {
            "name": name,
            "rule": rule_map,
            "human_rule": transform_rule_map(rule_map),
            "update_date": utils.curr_date_obj()
        }

        utils.conn_db('fingerprint').insert_one(data)

        finger_id = str(data.pop('_id'))

        data.pop('update_date')

        return utils.build_ret(ErrorMsg.Success, {"_id": finger_id, "data": data})


delete_finger_fields = ns.model('deleteFingerSite',  {
    '_id': fields.List(fields.String(required=True, description="指纹 _id"))
})


@ns.route('/delete/')
class DeleteARLFinger(ARLResource):
    @auth
    @ns.expect(delete_finger_fields)
    def post(self):
        """
        删除指纹
        """
        args = self.parse_args(delete_finger_fields)
        id_list = args.pop('_id', "")
        for _id in id_list:
            query = {'_id': ObjectId(_id)}
            utils.conn_db('fingerprint').delete_one(query)

        return utils.build_ret(ErrorMsg.Success, {'_id': id_list})


@ns.route('/export/')
class ExportARLFinger(ARLResource):

    @auth
    def get(self):
        """
        指纹导出
        """
        items = []
        results = list(utils.conn_db('fingerprint').find())
        for result in results:
            item = dict()
            item["rule"] = result["rule"]
            item["name"] = result["name"]
            items.append(item)

        data = json.dumps(items, indent=4, ensure_ascii=False)
        response = make_response(data)
        filename = "fingerprint_{}_{}.json".format(len(items), int(time.time()))
        response.headers['Content-Type'] = 'application/octet-stream'
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
        response.headers["Content-Disposition"] = "attachment; filename={}".format(quote(filename))

        return response


file_upload = reqparse.RequestParser()
file_upload.add_argument('file',
                         type=werkzeug.datastructures.FileStorage,
                         location='files',
                         required=True,
                         help='JSON file')


@ns.route('/upload/')
class UploadARLFinger(ARLResource):

    @auth
    @ns.expect(file_upload)
    def post(self):
        """
        指纹上传
        """
        args = file_upload.parse_args()
        file_data = args['file'].read()
        try:
            obj = json.loads(file_data)
            if not isinstance(obj, list):
                return utils.build_ret(ErrorMsg.Error, {'msg': "not list obj"})

            error_cnt = 0
            success_cnt = 0
            repeat_cnt = 0

            for rule in obj:
                human_rule = transform_rule_map(rule['rule'])
                rule_name = rule['name']
                if not human_rule:
                    error_cnt += 1
                    continue

                result = utils.conn_db('fingerprint').find_one({"human_rule": human_rule})
                if result:
                    repeat_cnt += 1
                    continue

                rule_map = parse_human_rule(human_rule)
                if rule_map is None:
                    error_cnt += 1
                    continue

                data = {
                    "name": rule_name,
                    "rule": rule_map,
                    "human_rule": human_rule,
                    "update_date": utils.curr_date_obj()
                }
                success_cnt += 1

                utils.conn_db('fingerprint').insert_one(data)

            return utils.build_ret(ErrorMsg.Success, {'error_cnt': error_cnt,
                                                      'repeat_cnt': repeat_cnt,'success_cnt': success_cnt})
        except Exception as e:
            return utils.build_ret(ErrorMsg.Error, {'msg': str(e)})


