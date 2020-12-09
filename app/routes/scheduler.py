from flask_restplus import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from app.modules import ErrorMsg
from . import base_query_fields, ARLResource, get_arl_parser
from app import scheduler as app_scheduler, utils
from app.modules import SchedulerStatus

ns = Namespace('scheduler', description="资产监控任务信息")

base_search_fields = {
    '_id': fields.String(description="监控任务job_id"),
    'domain': fields.String(description="要监控的域名"),
    'scope_id': fields.String(description="资产组范围ID"),
    'interval': fields.String(description="运行间隔，单位S"),
    'next_run_time': fields.String(description="下一次运行时间戳"),
    'next_run_date': fields.Integer(description="下一次运行日期"),
    'last_run_time': fields.Integer(description="上一次运行时间戳"),
    'last_run_date': fields.String(description="上一次运行时间日期"),
    'run_number': fields.String(description="运行次数")
}

base_search_fields.update(base_query_fields)


@ns.route('/')
class ARLScheduler(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        监控任务查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='scheduler')

        return data


add_scheduler_fields = ns.model('addScheduler',  {
    "scope_id": fields.String(description="添加资产范围"),
    "domain": fields.String(description="域名"),
    "interval": fields.Integer(description="间隔，单位是秒"),  # 单位是S
    "name": fields.String(description="监控任务名称"),
})



@ns.route('/add/')
class AddARLScheduler(ARLResource):

    @auth
    @ns.expect(add_scheduler_fields)
    def post(self):
        """
        添加监控周期任务
        """
        args = self.parse_args(add_scheduler_fields)
        scope_id = args.pop("scope_id")
        domain = args.pop("domain")
        interval = args.pop("interval")
        name = args.pop("name")

        if interval < 3600*6:
            return utils.build_ret(ErrorMsg.IntervalLessThan3600, {"interval": interval})

        monitor_domain = utils.arl.get_monitor_domain_by_id(scope_id)
        scope_data = utils.arl.scope_data_by_id(scope_id)

        if not scope_data:
            return utils.build_ret(ErrorMsg.NotFoundScopeID, {"scope_id": scope_id})

        domains = domain.split(",")
        for x in domains:
            curr_domain = x.strip()
            if curr_domain not in scope_data["scope_array"]:
                return utils.build_ret(ErrorMsg.DomainNotFoundViaScope,
                                        {"domain": curr_domain, "scope_id": scope_id})

            if curr_domain in monitor_domain:
                return utils.build_ret(ErrorMsg.DomainViaJob,
                                       {"domain": curr_domain, "scope_id": scope_id})

        ret_data = []
        for x in domains:
            if not name:
                name = "监控-{}-{}".format(scope_data["name"], x)

            job_id = app_scheduler.add_job(domain=x, scope_id=scope_id,
                                           options=None, interval=interval, name=name)
            ret_data.append({"domain": x, "scope_id": scope_id, "job_id": job_id})

        return utils.build_ret(ErrorMsg.Success, ret_data)


delete_scheduler_fields = ns.model('deleteScheduler',  {
    "job_id": fields.List(fields.String(description="监控任务ID列表"))
})


@ns.route('/delete/')
class DeleteARLScheduler(ARLResource):

    @auth
    @ns.expect(delete_scheduler_fields)
    def post(self):
        """
        删除监控周期任务
        """
        args = self.parse_args(delete_scheduler_fields)
        job_id_list = args.get("job_id", [])

        ret_data = {"job_id": job_id_list}

        for job_id in job_id_list:
            item = app_scheduler.find_job(job_id)
            if not item:
                return utils.build_ret(ErrorMsg.JobNotFound, ret_data)

        for job_id in job_id_list:
            app_scheduler.delete_job(job_id)

        return utils.build_ret(ErrorMsg.Success, ret_data)


recover_scheduler_fields = ns.model('recoverScheduler',  {
    "job_id": fields.String(required=True, description="监控任务ID")
})


@ns.route('/recover/')
class RecoverARLScheduler(ARLResource):

    @auth
    @ns.expect(recover_scheduler_fields)
    def post(self):
        """
        恢复监控周期任务
        """
        args = self.parse_args(recover_scheduler_fields)
        job_id = args.get("job_id")

        item = app_scheduler.find_job(job_id)
        if not item:
            return utils.build_ret(ErrorMsg.JobNotFound, {"job_id": job_id})

        status = item.get("status", SchedulerStatus.RUNNING)
        if status != SchedulerStatus.STOP:
            return utils.build_ret(ErrorMsg.SchedulerStatusNotStop, {"job_id": job_id})

        app_scheduler.recover_job(job_id)

        return utils.build_ret(ErrorMsg.Success, {"job_id": job_id})


stop_scheduler_fields = ns.model('stopScheduler',  {
    "job_id": fields.String(required=True, description="监控任务ID")
})


@ns.route('/stop/')
class StopARLScheduler(ARLResource):

    @auth
    @ns.expect(stop_scheduler_fields)
    def post(self):
        """
        停止监控周期任务
        """
        args = self.parse_args(stop_scheduler_fields)
        job_id = args.get("job_id")

        item = app_scheduler.find_job(job_id)
        if not item:
            return utils.build_ret(ErrorMsg.JobNotFound, {"job_id": job_id})

        status = item.get("status", SchedulerStatus.RUNNING)
        if status != SchedulerStatus.RUNNING:
            return utils.build_ret(ErrorMsg.SchedulerStatusNotRunning, {"job_id": job_id})

        app_scheduler.stop_job(job_id)

        return utils.build_ret(ErrorMsg.Success, {"job_id": job_id})