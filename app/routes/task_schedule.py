from bson import ObjectId
import time
from datetime import datetime
from flask_restx import fields, Namespace
from app.utils import get_logger, auth
from app import utils
from app.modules import ErrorMsg, TaskTag, TaskScheduleStatus
from . import base_query_fields, ARLResource, get_arl_parser
from app.helpers import task_schedule, task

ns = Namespace('task_schedule', description="计划任务")

logger = get_logger()

base_search_fields = {
    'name': fields.String(required=False, description="名称"),
    'target': fields.String(description="目标"),
    'policy_name': fields.String(description="策略名称"),
    'schedule_type': fields.String(description="计划类型"),
    'schedule_status': fields.String(description="状态")
}

base_search_fields.update(base_query_fields)


add_task_schedule_fields = ns.model('addTaskScheduleSite',  {
    'name': fields.String(required=True, description="名称"),
    'target': fields.String(required=True, description="目标"),
    'schedule_type': fields.String(required=True, description="计划类型（future_scan|recurrent_scan）"),
    'policy_id': fields.String(required=True, description="策略 ID"),
    'cron': fields.String(required=False, description="Cron"),
    'start_date': fields.String(required=False, description="开始时间"),
    'task_tag': fields.String(required=True, description="任务类别 （task|risk_cruising）")
})


@ns.route('/')
class ARLTaskScheduleResult(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        计划任务结果详情查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='task_schedule')

        return data

    @auth
    @ns.expect(add_task_schedule_fields)
    def post(self):
        """
        计划任务添加
        """
        args = self.parse_args(add_task_schedule_fields)
        schedule_type = args.pop('schedule_type', "")
        schedule_type = schedule_type.lower()
        target = args.pop('target')
        name = args.pop('name')
        cron = args.pop('cron')
        start_date = args.pop('start_date')
        policy_id = args.pop('policy_id')
        task_tag = args.pop("task_tag")

        avail_schedule_type = ["future_scan", "recurrent_scan"]
        if schedule_type not in avail_schedule_type:
            return utils.build_ret(ErrorMsg.TaskScheduleTypeInvalid, {"schedule_type": schedule_type})

        avail_task_tag = [TaskTag.TASK, TaskTag.RISK_CRUISING]
        if task_tag not in avail_task_tag:
            return utils.build_ret(ErrorMsg.TaskTagInvalid, {"task_tag": task_tag})

        try:
            # 资产发现任务
            if task_tag == TaskTag.TASK:
                ip_list, domain_list = task.get_ip_domain_list(target)
                if not ip_list and not domain_list:
                    return utils.build_ret(ErrorMsg.TaskTargetIsEmpty, {"target": target})

                target = "{} {}".format(" ".join(ip_list), " ".join(domain_list))

            # 风险巡航任务, 目标可以是URL
            if task_tag == TaskTag.RISK_CRUISING:
                targets = task.target2list(target)
                if not targets:
                    return utils.build_ret(ErrorMsg.TaskTargetIsEmpty, {"target": target})
                target = " ".join(targets)

        except Exception as e:
            return utils.build_ret(ErrorMsg.Error, {"error": str(e)})

        data = {
            "name": name,
            "target": target,
            "task_tag": task_tag,
            "schedule_type": schedule_type,
            "policy_id": policy_id,
            "cron": cron,
            "start_date": start_date,
            "status": TaskScheduleStatus.SCHEDULED,
            "run_number": 0,
            "last_run_time": 0,
            "last_run_date": "-"
        }

        # 定时扫描处理
        if schedule_type == "future_scan":
            try:
                start_time = utils.time.date2time(start_date)
                if start_time < time.time():
                    return utils.build_ret(ErrorMsg.FutureDateInvalid, {"start_date": start_date})

                data["start_time"] = start_time
                data["start_date"] = start_date
                data["next_run_date"] = start_date
                data["cron"] = ""
            except Exception as e:
                return utils.build_ret(ErrorMsg.DateInvalid, {"start_date": start_date})

        # 周期任务处理
        if schedule_type == "recurrent_scan":
            check_flag, msg = utils.check_cron_interval(cron)
            if not check_flag:
                return msg

            previous, next_sec, _ = utils.check_cron(cron)

            data["start_date"] = ""
            data["start_time"] = 0
            data["cron"] = cron
            data["next_run_date"] = utils.time2date(time.time() + next_sec)

        query = {'_id': ObjectId(policy_id)}
        item = utils.conn_db('policy').find_one(query)

        if not item:
            return utils.build_ret(ErrorMsg.PolicyIDNotFound, {})

        data["policy_name"] = item["name"]

        utils.conn_db('task_schedule').insert_one(data)

        data["_id"] = str(data["_id"])

        return utils.build_ret(ErrorMsg.Success, data)


delete_task_schedule_fields = ns.model('deleteTaskSchedule',  {
    "_id": fields.List(fields.String(description="计划任务ID列表"))
})


@ns.route('/delete/')
class DeleteARLTaskScheduler(ARLResource):

    @auth
    @ns.expect(delete_task_schedule_fields)
    def post(self):
        """
        删除计划任务
        """
        args = self.parse_args(delete_task_schedule_fields)
        job_id_list = args.get("_id", [])

        ret_data = {"_id": job_id_list}

        for job_id in job_id_list:
            item = task_schedule.find_task_schedule(job_id)
            if not item:
                return utils.build_ret(ErrorMsg.TaskScheduleNotFound, ret_data)

        for job_id in job_id_list:
            task_schedule.remove_task_schedule(job_id)

        return utils.build_ret(ErrorMsg.Success, ret_data)


stop_task_schedule_fields = ns.model('stopTaskSchedule',  {
    "_id": fields.List(fields.String(description="计划任务ID列表"))
})


@ns.route('/stop/')
class StopARLTaskScheduler(ARLResource):

    @auth
    @ns.expect(stop_task_schedule_fields)
    def post(self):
        """
        停止计划任务
        """
        args = self.parse_args(stop_task_schedule_fields)
        job_id_list = args.get("_id", [])

        ret_data = {"_id": job_id_list}

        for job_id in job_id_list:
            item = task_schedule.change_task_schedule_status(job_id, status=TaskScheduleStatus.STOP)
            if not item:
                return utils.build_ret(ErrorMsg.TaskScheduleNotFound, ret_data)

            if isinstance(item, str):
                return utils.build_ret(ErrorMsg.Error, {"error": item})

        return utils.build_ret(ErrorMsg.Success, ret_data)


recover_task_schedule_fields = ns.model('recoverTaskSchedule',  {
    "_id": fields.List(fields.String(description="计划任务ID列表"))
})


@ns.route('/recover/')
class RecoverARLTaskScheduler(ARLResource):

    @auth
    @ns.expect(recover_task_schedule_fields)
    def post(self):
        """
        恢复计划任务
        """
        args = self.parse_args(recover_task_schedule_fields)
        job_id_list = args.get("_id", [])

        ret_data = {"_id": job_id_list}

        for job_id in job_id_list:
            item = task_schedule.change_task_schedule_status(job_id, status=TaskScheduleStatus.SCHEDULED)
            if not item:
                return utils.build_ret(ErrorMsg.TaskScheduleNotFound, ret_data)

            if isinstance(item, str):
                return utils.build_ret(ErrorMsg.Error, {"error": item})

        return utils.build_ret(ErrorMsg.Success, ret_data)

