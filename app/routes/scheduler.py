from bson import ObjectId
from flask_restplus import Resource, Api, reqparse, fields, Namespace
from app.utils import get_logger, auth
from app.modules import ErrorMsg
from . import base_query_fields, ARLResource, get_arl_parser
from app import scheduler as app_scheduler, utils
from app.modules import SchedulerStatus, AssetScopeType, TaskTag
from app.helpers import get_options_by_policy_id
from app.helpers.scheduler import have_same_site_update_monitor

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
    'run_number': fields.String(description="运行次数"),
    "name": fields.String(description="名称")
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
    "scope_id": fields.String(required=True, description="添加资产范围"),
    "domain": fields.String(required=True, description="域名"),  # 多个域名可以用,隔开
    "interval": fields.Integer(description="间隔，单位是秒"),  # 单位是S
    "name": fields.String(description="监控任务名称"),  # 名称为空即自动生成
    "policy_id": fields.String(description="策略ID")
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
        policy_id = args.pop("policy_id", "")

        if interval < 3600*6:
            return utils.build_ret(ErrorMsg.IntervalLessThan3600, {"interval": interval})

        monitor_domain = utils.arl.get_monitor_domain_by_id(scope_id)
        scope_data = utils.arl.scope_data_by_id(scope_id)

        if not scope_data:
            return utils.build_ret(ErrorMsg.NotFoundScopeID, {"scope_id": scope_id})

        task_options = None
        if policy_id and len(policy_id) == 24:
            task_options = get_options_by_policy_id(policy_id, TaskTag.TASK)
            if task_options is None:
                return utils.build_ret(ErrorMsg.PolicyIDNotFound, {"policy_id": policy_id})

        # 资产范围类型（域名或者是IP）
        scope_type = scope_data.get("scope_type")
        if not scope_type:
            scope_type = AssetScopeType.DOMAIN

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
        # 下发 域名类型监控任务
        if scope_type == AssetScopeType.DOMAIN:
            for x in domains:
                curr_name = name
                if not name:
                    curr_name = "监控-{}-{}".format(scope_data["name"], x)

                job_id = app_scheduler.add_job(domain=x, scope_id=scope_id,
                                               options=task_options, interval=interval,
                                               name=curr_name, scope_type=scope_type)
                ret_data.append({"domain": x, "scope_id": scope_id, "job_id": job_id})

        # 下发IP 类型监控任务
        if scope_type == AssetScopeType.IP:
            curr_name = name
            ip_target = " ".join(domains)
            if not name:
                curr_name = "监控-{}-{}".format(scope_data["name"], ip_target)

            job_id = app_scheduler.add_job(domain=ip_target, scope_id=scope_id,
                                           options=task_options, interval=interval,
                                           name=curr_name, scope_type=scope_type)
            ret_data.append({"domain": ip_target, "scope_id": scope_id, "job_id": job_id})

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


# 下面有个批量恢复的，这个接口后面再删除
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


batch_recover_scheduler_fields = ns.model('batchRecoverScheduler',  {
    "job_id": fields.List(fields.String(required=True, description="监控任务ID列表"))
})


@ns.route('/recover/batch')
class BatchRecoverARLScheduler(ARLResource):

    @auth
    @ns.expect(batch_recover_scheduler_fields)
    def post(self):
        """
        批量恢复监控周期任务
        """
        args = self.parse_args(batch_recover_scheduler_fields)
        job_id_list = args.get("job_id", [])
        for job_id in job_id_list:
            item = app_scheduler.find_job(job_id)
            if not item:
                return utils.build_ret(ErrorMsg.JobNotFound, {"job_id": job_id})

            status = item.get("status", SchedulerStatus.RUNNING)
            if status != SchedulerStatus.STOP:
                return utils.build_ret(ErrorMsg.SchedulerStatusNotStop, {"job_id": job_id})

            app_scheduler.recover_job(job_id)

        return utils.build_ret(ErrorMsg.Success, {"job_id": job_id_list})


stop_scheduler_fields = ns.model('stopScheduler',  {
    "job_id": fields.String(required=True, description="监控任务ID")
})


# 下面有个批量停止的，这个接口后面再删除
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


batch_stop_scheduler_fields = ns.model('batchStopScheduler',  {
    "job_id": fields.List(fields.String(required=True, description="监控任务ID列表"))
})


@ns.route('/stop/batch')
class BatchStopARLScheduler(ARLResource):

    @auth
    @ns.expect(batch_stop_scheduler_fields)
    def post(self):
        """
        停止监控周期任务
        """
        args = self.parse_args(batch_stop_scheduler_fields)
        job_id_list = args.get("job_id", [])
        for job_id in job_id_list:
            item = app_scheduler.find_job(job_id)
            if not item:
                return utils.build_ret(ErrorMsg.JobNotFound, {"job_id": job_id})

            status = item.get("status", SchedulerStatus.RUNNING)
            if status != SchedulerStatus.RUNNING:
                return utils.build_ret(ErrorMsg.SchedulerStatusNotRunning, {"job_id": job_id})

            app_scheduler.stop_job(job_id)

        return utils.build_ret(ErrorMsg.Success, {"job_id": job_id_list})


add_scheduler_site_fields = ns.model('addSchedulerSite',  {
    "scope_id": fields.String(required=True, description="资产范围 id"),
    "interval": fields.Integer(description="间隔，单位是秒"),  # 单位是S
    "name": fields.String(description="监控任务名称"),  # 名称为空即自动生成
})


@ns.route('/add/site_monitor/')
class AddSiteScheduler(ARLResource):

    @auth
    @ns.expect(add_scheduler_site_fields)
    def post(self):
        """
        添加站点更新监控周期任务
        """
        args = self.parse_args(add_scheduler_site_fields)
        scope_id = args.pop("scope_id")
        interval = args.pop("interval")
        name = args.pop("name")

        if interval < 3600*6:
            return utils.build_ret(ErrorMsg.IntervalLessThan3600, {"interval": interval})

        scope_data = utils.arl.scope_data_by_id(scope_id)

        if not scope_data:
            return utils.build_ret(ErrorMsg.NotFoundScopeID, {"scope_id": scope_id})

        if have_same_site_update_monitor(scope_id=scope_id):
            return utils.build_ret(ErrorMsg.DomainSiteViaJob, {"scope_id": scope_id,
                                                               "scope_name": scope_data['name']})

        if not name:
            name = "站点监控-{}".format(scope_data["name"])

        _id = app_scheduler.add_asset_site_monitor_job(scope_id=scope_id,
                                                       name=name,
                                                       interval=interval)

        return utils.build_ret(ErrorMsg.Success, {"schedule_id": _id})
