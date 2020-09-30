from flask_restplus import Resource, Api, reqparse, fields, Namespace
from bson import ObjectId
from app import celerytask
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser, conn
from app import utils
from app.modules import TaskStatus

ns = Namespace('task')

logger = get_logger()

base_search_task_fields = {
    'name': fields.String(required=False, description="任务名"),
    'target': fields.String(description="任务目标"),
    'status': fields.String(description="任务状态"),
    '_id': fields.String(description="任务ID"),
    'options.domain_brute': fields.Boolean(description="是否开启域名爆破"),
    'options.domain_brute_type': fields.String(description="域名爆破类型"),
    'options.port_scan_type': fields.Boolean(description="端口扫描类型"),
    'options.port_scan': fields.Boolean(description="是否的端口扫描"),
    'options.service_detection': fields.Boolean(description="是否开启服务识别"),
    'options.service_brute': fields.Boolean(description="是否开启服务弱口令爆破"),
    'options.os_detection': fields.Boolean(description="是否开启操作系统识别"),
    'options.site_identify': fields.Boolean(description="是否开启站点识别"),
    'options.file_leak': fields.Boolean(description="是否开启文件泄露扫描"),
    'options.alt_dns': fields.Boolean(description="是否开启DNS字典智能生成"),
    'options.github_search_domain': fields.Boolean(description="是否开启GitHub搜索"),
    'options.fetch_api_path': fields.Boolean(description="是否开启JS PATH收集"),
    'options.fofa_search': fields.Boolean(description="是否开启Fofa IP 查询"),
    'options.sub_takeover': fields.Boolean(description="是否开启子域名劫持扫描"),
    'options.search_engines': fields.Boolean(description="是否开启搜索引擎调用"),
    'options.site_spider': fields.Boolean(description="是否开启站点爬虫"),
    'options.riskiq_search': fields.Boolean(description="是否开启 Riskiq 调用"),
    'options.arl_search': fields.Boolean(description="是否开启 ARL 历史查询")

}

base_search_task_fields.update(base_query_fields)

search_task_fields = ns.model('SearchTask', base_search_task_fields)

add_task_fields = ns.model('AddTask', {
    'name': fields.String(required=True, description="任务名"),
    'target': fields.String(required=True, description="目标"),
    "domain_brute": fields.Boolean(),
    'domain_brute_type': fields.String(),
    "port_scan_type": fields.String(description="目标"),
    "port_scan": fields.Boolean(),
    "service_detection": fields.Boolean(),
    "service_brute": fields.Boolean(example=False),
    "os_detection": fields.Boolean(example=False),
    "site_identify": fields.Boolean(example=False),
    "site_capture": fields.Boolean(example=False),
    "file_leak": fields.Boolean(example=False),
    "search_engines": fields.Boolean(example=False),
    "site_spider": fields.Boolean(example=False),
    "arl_search": fields.Boolean(example=False),
    "riskiq_search": fields.Boolean(example=False),
    "alt_dns": fields.Boolean(),
    "github_search_domain": fields.Boolean(),
    "url_spider": fields.Boolean(),
    "ssl_cert": fields.Boolean(),
    "fetch_api_path": fields.Boolean(),
    "fofa_search": fields.Boolean(),
    "sub_takeover": fields.Boolean()
})


@ns.route('/')
class ARLTask(ARLResource):
    parser = get_arl_parser(search_task_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        任务信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='task')

        return data

    @auth
    @ns.expect(add_task_fields)
    def post(self):
        """
        任务提交
        """
        args = self.parse_args(add_task_fields)

        name = args.pop('name')
        target = args.pop('target')
        target = target.strip().lower()

        task_data = {
            "name": name,
            "target": target,
            "start_time": "-",
            "end_time": "-",
            "service": [],
            "status": "waiting",
            "options": args,
            "type": "domain"
        }

        logger.info(task_data)

        target_lists = target.split()
        ip_target_list = []
        ret_items = []
        for item in target_lists:
            if utils.is_valid_domain(item):
                ret_item = {
                    "target": item,
                    "type":"domain"
                }
                domain_task_data = task_data.copy()
                domain_task_data["target"] = item
                _task_data = submit_task(domain_task_data)
                ret_item["task_id"] = _task_data.get("task_id", "")
                ret_item["celery_id"] = _task_data.get("celery_id", "")
                ret_items.append(ret_item)

            elif utils.is_vaild_ip_target(item):
                if utils.not_in_black_ips(item):
                    ip_target_list.append(item)
                else:
                    ret_item = {
                        "target": item,
                        "type": "in black ip list",
                        "task_id": "",
                        "celery_id": ""
                    }
                    ret_items.append(ret_item)

            else:
                ret_item = {
                    "target": item,
                    "type": "unknown",
                    "task_id": "",
                    "celery_id": ""
                }
                ret_items.append(ret_item)



        if ip_target_list:
            ip_task_data = task_data.copy()
            ip_task_data["target"] = " ".join(ip_target_list)
            ip_task_data["type"] = "ip"

            ret_item = {
                "target": ip_task_data["target"],
                "type": ip_task_data["type"]
            }

            _task_data = submit_task(ip_task_data)

            ret_item["task_id"] = _task_data.get("task_id", "")
            ret_item["celery_id"] = _task_data.get("celery_id", "")
            ret_items.append(ret_item)

        ret_data = {
            "items": ret_items,
            "options": args,
            "message": "success",
            "code": 200
        }

        return ret_data


def submit_task(task_data):
    target = task_data["target"]
    conn('task').insert_one(task_data)
    task_id = str(task_data.pop("_id"))
    task_data["task_id"] = task_id
    celery_id = celerytask.arl_task.delay(options=task_data)

    logger.info("target:{} task_id:{} celery_id:{}".format(target, task_id, celery_id))

    values = {"$set": {"celery_id": str(celery_id)}}
    task_data["celery_id"] = str(celery_id)
    conn('task').update_one({"_id": ObjectId(task_id)}, values)

    return task_data


@ns.route('/stop/<string:task_id>')
class StopTask(ARLResource):
    @auth
    def get(self, task_id=None):
        """
        任务停止
        """
        done_status = [TaskStatus.DONE, TaskStatus.STOP, TaskStatus.ERROR]

        task_data = utils.conn_db('task').find_one({'_id': ObjectId(task_id)})
        if not task_data:
            return {"message": "not found task", "task_id": task_id, "code":100}

        if task_data["status"] in done_status:
            return {"message": "error, task is done", "task_id": task_id, "code":101}

        celery_id = task_data.get("celery_id")
        if not celery_id:
            return {"message": "not found celery_id", "task_id": task_id, "code": 102}

        control = celerytask.celery.control

        control.revoke(celery_id, signal='SIGTERM', terminate=True)

        utils.conn_db('task').update_one({'_id': ObjectId(task_id)}, {"$set": {"status": TaskStatus.STOP}})

        utils.conn_db('task').update_one({'_id': ObjectId(task_id)}, {"$set": {"end_time": utils.curr_date()}})

        return {"message": "success", "task_id": task_id, "code":200}


delete_task_fields = ns.model('DeleteTask',  {
    'del_task_data': fields.String(required=False, description="是否删除任务数据")
})


@ns.route('/delete/<string:task_id>')
class DeleteTask(ARLResource):
    parser = get_arl_parser(delete_task_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self, task_id=None):
        """
        任务删除
        """
        done_status = [TaskStatus.DONE, TaskStatus.STOP, TaskStatus.ERROR]
        args = self.parser.parse_args()

        del_task_data_flag = str(args.pop('del_task_data', "false")).lower()

        task_data = utils.conn_db('task').find_one({'_id': ObjectId(task_id)})
        if not task_data:
            return {"message": "not found task", "task_id": task_id, "code": 103}

        if task_data["status"] not in done_status:
            return {"message": "task is running", "task_id": task_id, "code": 104}

        utils.conn_db('task').delete_many({'_id': ObjectId(task_id)})
        table_list = ["cert", "domain", "fileleak", "ip", "service", "site", "url"]
        if del_task_data_flag == "true":
            for name in table_list:
                utils.conn_db(name).delete_many({'task_id': task_id})

        return {"message": "success", "task_id": task_id, "code": 200}