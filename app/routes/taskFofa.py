from flask_restplus import Namespace, fields
from app.utils import get_logger, auth, build_ret, conn_db
from app.modules import ErrorMsg, CeleryAction
from app.services.fofaClient import fofa_query, fofa_query_result
from app import celerytask
from bson import ObjectId
from . import ARLResource


ns = Namespace('task_fofa', description="Fofa 任务下发")

logger = get_logger()


test_fofa_fields = ns.model('taskFofaTest',  {
    'query': fields.String(required=True, description="Fofa 查询语句")
})


@ns.route('/test')
class TaskFofaTest(ARLResource):

    @auth
    @ns.expect(test_fofa_fields)
    def post(self):
        """
        测试Fofa查询连接
        """
        args = self.parse_args(test_fofa_fields)
        query = args.pop('query')
        data = fofa_query(query, page_size=1)
        if isinstance(data, str):
            return build_ret(ErrorMsg.FofaConnectError, {'error': data})

        if data.get("error"):
            return build_ret(ErrorMsg.FofaKeyError, {'error': data.get("errmsg")})

        item = {
            "size": data["size"],
            "query": data["query"]
        }

        return build_ret(ErrorMsg.Success, item)


add_fofa_fields = ns.model('addTaskFofa', {
    'query': fields.String(required=True, description="Fofa 查询语句"),
    'name': fields.String(required=True, description="任务名"),
    'policy_id': fields.String(description="策略 ID")
})


@ns.route('/submit')
class AddFofaTask(ARLResource):

    @auth
    @ns.expect(add_fofa_fields)
    def post(self):
        """
        提交Fofa查询任务
        """
        args = self.parse_args(add_fofa_fields)
        query = args.pop('query')
        name = args.pop('name')
        policy_id = args.get('policy_id')

        task_options = {
            "port_scan_type": "test",
            "port_scan": True,
            "service_detection": False,
            "service_brute": False,
            "os_detection": False,
            "site_identify": False,
            "file_leak": False,
            "ssl_cert": False
        }

        data = fofa_query(query, page_size=1)
        if isinstance(data, str):
            return build_ret(ErrorMsg.FofaConnectError, {'error': data})

        if data.get("error"):
            return build_ret(ErrorMsg.FofaKeyError, {'error': data.get("errmsg")})

        if data["size"] <= 0:
            return build_ret(ErrorMsg.FofaResultEmpty, {})

        fofa_ip_list = fofa_query_result(query)
        if isinstance(fofa_ip_list, str):
            return build_ret(ErrorMsg.FofaConnectError, {'error': data})

        if policy_id and len(policy_id) == 24:
            task_options.update(policy_2_task_options(policy_id))

        task_data = {
            "name": name,
            "target": "Fofa ip {}".format(len(fofa_ip_list)),
            "start_time": "-",
            "end_time": "-",
            "task_tag": "task",
            "service": [],
            "status": "waiting",
            "options": task_options,
            "type": "fofa",
            "fofa_ip": fofa_ip_list
        }
        task_data = submit_fofa_task(task_data)

        return build_ret(ErrorMsg.Success, task_data)


def policy_2_task_options(policy_id):
    options = {}
    query = {
        "_id": ObjectId(policy_id)
    }
    data = conn_db('policy').find_one(query)
    if not data:
        return options

    policy_options = data["policy"]
    policy_options.pop("domain_config")

    ip_config = policy_options.pop("ip_config")
    site_config = policy_options.pop("site_config")

    options.update(ip_config)
    options.update(site_config)
    options.update(policy_options)

    return options


def submit_fofa_task(task_data):
    conn_db('task').insert_one(task_data)
    task_id = str(task_data.pop("_id"))
    task_data["task_id"] = task_id

    task_options = {
        "celery_action": CeleryAction.FOFA_TASK,
        "data": task_data
    }

    celery_id = celerytask.arl_task.delay(options=task_options)

    logger.info("target:{} celery_id:{}".format(task_id, celery_id))

    values = {"$set": {"celery_id": str(celery_id)}}
    task_data["celery_id"] = str(celery_id)
    conn_db('task').update_one({"_id": ObjectId(task_id)}, values)

    return task_data

