import re
import bson
from flask_restplus import Resource, Api, reqparse, fields, Namespace
from bson import ObjectId
from app import celerytask
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser, conn
from app import utils
from app.modules import TaskStatus, ErrorMsg, TaskSyncStatus, CeleryAction, TaskTag, TaskType
from app.helpers import get_options_by_policy_id, submit_task_task,\
    submit_risk_cruising, get_scope_by_scope_id, check_target_in_scope
from app.helpers.task import get_task_data, restart_task

ns = Namespace('task', description="资产发现任务信息")

logger = get_logger()

base_search_task_fields = {
    'name': fields.String(required=False, description="任务名"),
    'target': fields.String(description="任务目标"),
    'status': fields.String(description="任务状态"),
    '_id': fields.String(description="任务ID"),
    'task_tag': fields.String(description="监控任务和侦查任务tag"),
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
    # 'options.github_search_domain': fields.Boolean(description="是否开启GitHub搜索"),
    # 'options.fetch_api_path': fields.Boolean(description="是否开启JS PATH收集"),
    'options.search_engines': fields.Boolean(description="是否开启搜索引擎调用"),
    'options.site_spider': fields.Boolean(description="是否开启站点爬虫"),
    'options.riskiq_search': fields.Boolean(description="是否开启 Riskiq 调用"),
    'options.arl_search': fields.Boolean(description="是否开启 ARL 历史查询"),
    'options.crtsh_search': fields.Boolean(description="是否开启 crt.sh 查询"),
    'options.skip_scan_cdn_ip': fields.Boolean(description="是否跳过CDN IP端口扫描"),
    'options.findvhost': fields.Boolean(description="是否开启Host碰撞检测")

}

base_search_task_fields.update(base_query_fields)

search_task_fields = ns.model('SearchTask', base_search_task_fields)

add_task_fields = ns.model('AddTask', {
    'name': fields.String(required=True, description="任务名"),
    'target': fields.String(required=True, description="目标"),
    "domain_brute": fields.Boolean(),
    'domain_brute_type': fields.String(),
    "port_scan_type": fields.String(description="端口扫描类型"),
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
    "ssl_cert": fields.Boolean(),
    "fetch_api_path": fields.Boolean(),
    "crtsh_search": fields.Boolean(example=True, default=True),
    "skip_scan_cdn_ip": fields.Boolean(),
    "findvhost": fields.Boolean()
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

        try:
            task_data_list = submit_task_task(target=target, name=name, options=args)
        except Exception as e:
            logger.exception(e)
            return utils.build_ret(ErrorMsg.Error, {"error": str(e)})

        if not task_data_list:
            return utils.build_ret(ErrorMsg.TaskTargetIsEmpty, {"target": target})

        ret = {
            "code": 200,
            "message": "success",
            "items": task_data_list
        }
        return ret

        # return utils.build_ret(ErrorMsg.Success, {"items": task_data_list})


batch_stop_fields = ns.model('BatchStop',  {
    "task_id": fields.List(fields.String(description="任务 ID"), required=True),
})


@ns.route('/batch_stop/')
class BatchStopTask(ARLResource):

    @auth
    @ns.expect(batch_stop_fields)
    def post(self):
        """
        任务批量停止
        """
        args = self.parse_args(batch_stop_fields)
        task_id_list = args.pop("task_id", [])

        for task_id in task_id_list:
            if not task_id:
                continue
            stop_task(task_id)

        """这里直接返回成功了"""
        return utils.build_ret(ErrorMsg.Success, {})


@ns.route('/stop/<string:task_id>')
class StopTask(ARLResource):
    @auth
    def get(self, task_id=None):
        """
        任务停止
        """
        return stop_task(task_id=task_id)


def stop_task(task_id):
    """任务停止"""
    done_status = [TaskStatus.DONE, TaskStatus.STOP, TaskStatus.ERROR]

    task_data = utils.conn_db('task').find_one({'_id': ObjectId(task_id)})
    if not task_data:
        return utils.build_ret(ErrorMsg.NotFoundTask, {"task_id": task_id})

    if task_data["status"] in done_status:
        return utils.build_ret(ErrorMsg.TaskIsDone, {"task_id": task_id})

    celery_id = task_data.get("celery_id")
    if not celery_id:
        return utils.build_ret(ErrorMsg.CeleryIdNotFound, {"task_id": task_id})

    control = celerytask.celery.control

    control.revoke(celery_id, signal='SIGTERM', terminate=True)

    utils.conn_db('task').update_one({'_id': ObjectId(task_id)}, {"$set": {"status": TaskStatus.STOP}})

    utils.conn_db('task').update_one({'_id': ObjectId(task_id)}, {"$set": {"end_time": utils.curr_date()}})

    return utils.build_ret(ErrorMsg.Success, {"task_id": task_id})


delete_task_fields = ns.model('DeleteTask',  {
    'del_task_data': fields.Boolean(required=False, default=False, description="是否删除任务数据"),
    'task_id': fields.List(fields.String(required=True, description="任务ID"))
})


@ns.route('/delete/')
class DeleteTask(ARLResource):
    @auth
    @ns.expect(delete_task_fields)
    def post(self):
        """
        任务删除
        """
        done_status = [TaskStatus.DONE, TaskStatus.STOP, TaskStatus.ERROR]
        args = self.parse_args(delete_task_fields)
        task_id_list = args.pop('task_id')
        del_task_data_flag = args.pop('del_task_data')

        for task_id in task_id_list:
            task_data = utils.conn_db('task').find_one({'_id': ObjectId(task_id)})
            if not task_data:
                return utils.build_ret(ErrorMsg.NotFoundTask, {"task_id": task_id})

            if task_data["status"] not in done_status:
                return utils.build_ret(ErrorMsg.TaskIsRunning, {"task_id": task_id})

        for task_id in task_id_list:
            utils.conn_db('task').delete_many({'_id': ObjectId(task_id)})
            table_list = ["cert", "domain", "fileleak", "ip", "service", "site", "url", "vuln", "cip"]
            if del_task_data_flag:
                for name in table_list:
                    utils.conn_db(name).delete_many({'task_id': task_id})

        return utils.build_ret(ErrorMsg.Success, {"task_id": task_id_list})


sync_task_fields = ns.model('SyncTask',  {
    'task_id': fields.String(required=True, description="任务ID"),
    'scope_id': fields.String(required=True, description="资产范围ID"),
})


@ns.route('/sync/')
class SyncTask(ARLResource):
    @auth
    @ns.expect(sync_task_fields)
    def post(self):
        """
        将任务结果同步到资产组
        """
        done_status = [TaskStatus.DONE, TaskStatus.STOP, TaskStatus.ERROR]
        args = self.parse_args(sync_task_fields)
        task_id = args.pop('task_id')
        scope_id = args.pop('scope_id')

        query = {'_id': ObjectId(task_id)}
        task_data = utils.conn_db('task').find_one(query)
        if not task_data:
            return utils.build_ret(ErrorMsg.NotFoundTask, {"task_id": task_id})

        asset_scope_data = utils.conn_db('asset_scope').find_one({'_id': ObjectId(scope_id)})
        if not asset_scope_data:
            return utils.build_ret(ErrorMsg.NotFoundScopeID, {"task_id": task_id})

        if task_data.get("type") != "domain":
            return utils.build_ret(ErrorMsg.TaskTypeIsNotDomain, {"task_id": task_id})

        if not utils.is_in_scopes(task_data["target"], asset_scope_data["scope_array"]):
            return utils.build_ret(ErrorMsg.TaskTargetNotInScope, {"task_id": task_id})

        if task_data["status"] not in done_status:
            return utils.build_ret(ErrorMsg.TaskIsRunning, {"task_id": task_id})

        task_sync_status = task_data.get("sync_status", TaskSyncStatus.DEFAULT)

        if task_sync_status not in [TaskSyncStatus.DEFAULT, TaskSyncStatus.ERROR]:
            return utils.build_ret(ErrorMsg.TaskSyncDealing, {"task_id": task_id})

        task_data["sync_status"] = TaskSyncStatus.WAITING

        options = {
            "celery_action": CeleryAction.DOMAIN_TASK_SYNC_TASK,
            "data": {
                "task_id": task_id,
                "scope_id": scope_id
            }
        }
        celerytask.arl_task.delay(options=options)

        conn('task').find_one_and_replace(query, task_data)

        return utils.build_ret(ErrorMsg.Success, {"task_id": task_id})


sync_scope_fields = ns.model('SyncScope',  {
    'target': fields.String(required=True, description="需要同步的目标"),
})


# ******* 根据目标找到要同步的资产分组ID *********
@ns.route('/sync_scope/')
class Target2Scope(ARLResource):
    parser = get_arl_parser(sync_scope_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        从目标映反查资产分组
        """
        args = self.parser.parse_args()
        target = args.pop("target")
        if not utils.is_valid_domain(target):
            return utils.build_ret(ErrorMsg.DomainInvalid, {"target": target})

        args["scope_array"] = utils.get_fld(target)
        args["size"] = 100
        args["order"] = "_id"

        data = self.build_data(args=args, collection='asset_scope')
        ret = []
        for item in data["items"]:
            if utils.is_in_scopes(target, item["scope_array"]):
                ret.append(item)

        data["items"] = ret
        data["total"] = len(ret)
        return data


'''任务通过策略下发字段'''
task_by_policy_fields = ns.model('TaskByPolicy', {
    "name": fields.String(description="任务名称", default=True, required=True),
    "task_tag": fields.String(description="任务类型标签", enum=["task", "risk_cruising"], required=True),
    "target": fields.String(description="任务目标", example="", required=False),
    "policy_id": fields.String(description="策略 ID", example="603c65316591e73dd717d176", required=True),
    "result_set_id": fields.String(description="结果集 ID", example="603c65316591e73dd717d176", required=False)
})


# ******* 通过指定策略ID 下发任务 *********
@ns.route('/policy/')
class TaskByPolicy(ARLResource):
    @auth
    @ns.expect(task_by_policy_fields)
    def post(self):
        """
        任务通过策略下发
        """
        args = self.parse_args(task_by_policy_fields)
        name = args.pop("name")
        policy_id = args.pop("policy_id")
        target = args.pop("target")
        task_tag = args.pop("task_tag")
        result_set_id = args.pop("result_set_id")
        task_tag_enum = task_by_policy_fields["task_tag"].enum

        if task_tag not in task_tag_enum:
            return utils.build_ret("task_tag 只能取 {}".format(",".join(task_tag_enum)), {})

        options = get_options_by_policy_id(policy_id, task_tag)

        if not options:
            return utils.build_ret(ErrorMsg.PolicyIDNotFound, {"policy_id": policy_id})

        task_data_list = []
        try:
            if task_tag == TaskTag.TASK:
                # 对于资产发现任务检验通过策略关联的资产组
                related_scope_id = options.get("related_scope_id", "")
                if related_scope_id:
                    scope_data = get_scope_by_scope_id(scope_id=related_scope_id)
                    if not scope_data:
                        return utils.build_ret(ErrorMsg.NotFoundScopeID, {"scope_id": related_scope_id})
                    
                    check_target_in_scope(target=target, scope_list=scope_data["scope_array"])

                task_data_list = submit_task_task(target=target, name=name, options=options)
                if not task_data_list:
                    return utils.build_ret(ErrorMsg.TaskTargetIsEmpty, {"target": target})

            if task_tag == TaskTag.RISK_CRUISING:
                if result_set_id:
                    query = {"_id": ObjectId(result_set_id)}
                    item = utils.conn_db('result_set').find_one(query, {"total": 1})
                    if not item:
                        return utils.build_ret(ErrorMsg.ResultSetIDNotFound, {"result_set_id": result_set_id})

                    target_len = item["total"]

                    if target_len == 0:
                        return utils.build_ret(ErrorMsg.ResultSetIsEmpty, {"result_set_id": result_set_id})

                    options["result_set_id"] = result_set_id
                    options["result_set_len"] = target_len

                    task_data_list = submit_risk_cruising(target=target, name=name, options=options)
                    if not task_data_list:
                        return utils.build_ret(ErrorMsg.Error, {"result_set_id": result_set_id})

                else:
                    task_data_list = submit_risk_cruising(target=target, name=name, options=options)
                    if not task_data_list:
                        return utils.build_ret(ErrorMsg.TaskTargetIsEmpty, {"target": target})
        except Exception as e:
            logger.exception(e)
            return utils.build_ret(ErrorMsg.Error, {"error": str(e)})

        return utils.build_ret(ErrorMsg.Success, {"items": task_data_list})


restart_task_fields = ns.model('DeleteTask',  {
    'task_id': fields.List(fields.String(required=True, description="任务ID"))
})


# ******* 重新下发任务功能 *********
@ns.route('/restart/')
class TaskRestart(ARLResource):
    @auth
    @ns.expect(restart_task_fields)
    def post(self):
        """
        任务重启
        """
        done_status = [TaskStatus.DONE, TaskStatus.STOP, TaskStatus.ERROR]
        args = self.parse_args(restart_task_fields)
        task_id_list = args.pop('task_id')

        try:
            for task_id in task_id_list:
                task_data = get_task_data(task_id)
                if not task_data:
                    return utils.build_ret(ErrorMsg.NotFoundTask, {"task_id": task_id})

                if task_data["status"] not in done_status:
                    return utils.build_ret(ErrorMsg.TaskIsRunning, {"task_id": task_id})

                restart_task(task_id)

        except Exception as e:
            return utils.build_ret(ErrorMsg.Error, {"error": str(e)})

        return utils.build_ret(ErrorMsg.Success, {"task_id": task_id_list})


