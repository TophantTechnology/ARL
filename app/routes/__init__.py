import re
from flask_restplus import Resource, Api, reqparse, fields
from app import modules
from bson.objectid import ObjectId
from datetime import datetime
from urllib.parse import quote
from flask import make_response
import time

from app.utils import conn_db as conn
base_query_fields = {
    'page': fields.Integer(description="当前页数", example=1),
    'size': fields.Integer(description="页面大小", example=10),
    'order': fields.String(description="排序字段", example='_id'),
}

# 只能用等号进行mongo查询的字段
EQUAL_FIELDS = ["task_id", "task_tag", "ip_type", "scope_id"]


class ARLResource(Resource):
    def get_parser(self, model, location='json'):
        parser = reqparse.RequestParser(bundle_errors=True)
        for name in model:
            curr_field = model[name]

            parser.add_argument(name,
                                required=curr_field.required,
                                type=curr_field.format,
                                help=curr_field.description,
                                location=location)
        return parser

    def parse_args(self, model, location='json'):
        parser = self.get_parser(model, location)
        args = parser.parse_args()
        return args

    def build_db_query(self, args):
        query_args = {}
        for key in args:
            if key in base_query_fields:
                continue

            if key == '_id':
                if args[key]:
                    query_args[key] = ObjectId(args[key])

                continue

            if args[key] is None:
                continue

            if key.endswith("__dgt"):
                real_key = key.split('__dgt')[0]
                raw_value = query_args.get(real_key, {})
                raw_value.update({
                    "$gt": datetime.strptime(args[key],
                                             "%Y-%m-%d %H:%M:%S")
                })
                query_args[real_key] = raw_value

            elif key.endswith("__dlt"):
                real_key = key.split('__dlt')[0]
                raw_value = query_args.get(real_key, {})
                raw_value.update({
                    "$lt": datetime.strptime(args[key],
                                             "%Y-%m-%d %H:%M:%S")
                })
                query_args[real_key] = raw_value

            elif isinstance(args[key], str):
                if key in EQUAL_FIELDS:
                    query_args[key] = args[key]
                else:
                    query_args[key] = {
                        "$regex": re.escape(args[key]),
                        '$options': "i"
                    }
            else:
                query_args[key] = args[key]


        return query_args

    def build_return_items(self, data):
        items = []

        special_keys = ["_id", "save_date", "update_date"]

        for item in data:
            for key in item:
                if key in special_keys:
                    item[key] = str(item[key])

            items.append(item)

        return items

    def build_data(self, args= None , collection = None):

        default_field = self.get_default_field(args)
        page = default_field.get("page", 1)
        size = default_field.get("size", 10)
        orderby_list = default_field.get('order', [("_id", -1)])
        query = self.build_db_query(args)
        result = conn(collection).find(query).sort(orderby_list).skip(size*(page-1)).limit(size)
        count = conn(collection).count(query)
        items = self.build_return_items(result)

        special_keys = ["_id", "save_date", "update_date"]
        for key in query:
            if key in special_keys:
                query[key] = str(query[key])

        data = {
            "page": page,
            "size": size,
            "total": count,
            "items": items,
            "query": query,
            "code": 200
        }
        return data

    '''
    取默认字段的值，并且删除
    '''
    def get_default_field(self, args):
        default_field_map = {
            "page": 1,
            "size": 10,
            "order": "-_id"
        }

        ret = default_field_map.copy()

        for x in default_field_map:
            if x in args and args[x]:
                ret[x] =  args.pop(x)
                if x == "size":
                    if ret[x]<=0:
                        ret[x] = 10
                    if ret[x]>= 10000:
                        ret[x] = 10000

                if x == "page":
                    if ret[x]<=0:
                        ret[x] = 1

        orderby_list = []
        orderby_field = ret.get("order", "-_id")
        for field in orderby_field.split(","):
            field = field.strip()
            if field.startswith("-"):
                orderby_list.append((field.split("-")[1], -1))
            elif field.startswith("+"):
                orderby_list.append((field.split("+")[1], 1))
            else:
                orderby_list.append((field, 1))

        ret['order'] = orderby_list
        return ret

    def send_export_file(self, args, _type):
        _type_map_field_name = {
            "site": "site",
            "domain": "domain",
            "ip": "ip",
            "asset_site": "site",
            "asset_domain": "domain",
            "asset_ip": "ip",
            "url": "url"
        }
        data = self.build_data(args=args, collection=_type)["items"]
        items_set = set()
        for item in data:
            filed_name = _type_map_field_name.get(_type, "")
            if filed_name and filed_name in item:
                if filed_name == "ip":
                    curr_ip = item[filed_name]
                    for port_info in item.get("port_info", []):
                        items_set.add("{}:{}".format(curr_ip, port_info["port_id"]))
                else:
                    items_set.add(item[filed_name])

        return self.send_file(items_set, _type)

    def send_batch_export_file(self, task_id_list,  _type):
        _type_map_field_name = {
            "site": "site",
            "domain": "domain",
            "ip": "ip",
            "url": "url",
            "cip": "cidr_ip"
        }
        items_set = set()
        filed_name = _type_map_field_name.get(_type, "")

        for task_id in task_id_list:
            if not filed_name:
                continue
            if not task_id:
                continue
            query = {"task_id": task_id}
            items = conn(_type).distinct(filed_name, query)
            items_set |= set(items)

        return self.send_file(items_set, _type)

    def send_scope_batch_export_file(self, scope_id_list,  _type):
        _type_map_field_name = {
            "asset_site": "site",
            "asset_domain": "domain",
            "asset_ip": "ip"
        }

        items_set = set()
        filed_name = _type_map_field_name.get(_type, "")

        for scope_id in scope_id_list:
            if not filed_name:
                continue
            if not scope_id:
                continue
            query = {"scope_id": scope_id}
            items = conn(_type).distinct(filed_name, query)
            items_set |= set(items)

        return self.send_file(items_set, _type)

    def send_file(self, items_set, _type):
        response = make_response("\r\n".join(items_set))
        filename = "{}_{}_{}.txt".format(_type, len(items_set), int(time.time()))
        response.headers['Content-Type'] = 'application/octet-stream'
        response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
        response.headers["Content-Disposition"] = "attachment; filename={}".format(quote(filename))
        return response


def get_arl_parser(model, location='args'):
    r = ARLResource()
    return r.get_parser(model, location)


from .task import ns as task_ns
from .domain import ns as domain_ns
from .site import ns as site_ns
from .ip import ns as ip_ns
from .url import ns as url_ns
from .user import ns as user_ns
from .image import ns as image_ns
from .cert import ns as cert_ns
from .service import ns as service_ns
from .fileleak import ns as fileleak_ns
from .export import ns as export_ns
from .assetScope import ns as asset_scope_ns
from .assetDomain import ns as asset_domain_ns
from .assetIP import ns as asset_ip_ns
from .assetSite import ns as asset_site_ns
from .scheduler import ns as scheduler_ns
from .poc import ns as poc_ns
from .vuln import ns as vuln_ns
from .batchExport import ns as batch_export_ns
from .policy import ns as policy_ns
from .npoc_service import ns as npoc_service_ns
from .taskFofa import ns as task_fofa_ns
from .console import ns as console_ns
from .cip import ns as cip_ns
from .fingerprint import ns as fingerprint_ns
from .stat_finger import ns as stat_finger_ns
from .github_task import ns as github_task_ns
from .github_result import ns as github_result_ns
from .github_monitor_result import ns as github_monitor_result_ns
from .github_scheduler import ns as github_scheduler_ns
from .task_schedule import ns as task_schedule_ns
