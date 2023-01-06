import time
from bson import ObjectId
from flask_restx import fields, Namespace
from app.utils import get_logger, auth, github_task
from app import utils
from . import base_query_fields, ARLResource, get_arl_parser
from app.modules import SchedulerStatus, ErrorMsg

ns = Namespace('github_scheduler', description="Github 监控任务详情")

logger = get_logger()

base_search_fields = {
    'name': fields.String(required=False, description="任务名"),
    'keyword': fields.String(description="关键字"),
    'status': fields.String(description="状态")
}

base_search_fields.update(base_query_fields)


add_github_scheduler_fields = ns.model('AddGithubScheduler', {
    'name': fields.String(required=True, description="任务名"),
    'keyword': fields.String(required=True, description="关键字"),
    "cron": fields.String(required=True, description="Cron 表达式")
})


@ns.route('/')
class ARLGithubScheduler(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        Github 监控任务信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='github_scheduler')

        return data

    @auth
    @ns.expect(add_github_scheduler_fields)
    def post(self):
        """
        Github 监控任务添加
        """
        args = self.parse_args(add_github_scheduler_fields)
        name = args.pop('name')
        keyword = args.pop('keyword')
        keyword = keyword.strip()
        cron = args.pop('cron')

        if not keyword:
            return utils.build_ret(ErrorMsg.GithubKeywordEmpty, data={})

        check_flag, msg = utils.check_cron_interval(cron)
        if not check_flag:
            return msg

        previous, next_sec, _ = utils.check_cron(cron)

        scheduler_data = {
            "name": name,
            "keyword": keyword,
            "cron": cron,
            "run_number": 0,
            "last_run_date": "-",
            "last_run_time": 0,
            "next_run_date": utils.time2date(time.time() + next_sec),
            "status": SchedulerStatus.RUNNING
        }

        utils.conn_db('github_scheduler').insert_one(scheduler_data)

        scheduler_data["_id"] = str(scheduler_data["_id"])

        return utils.build_ret(ErrorMsg.Success, data=scheduler_data)


delete_github_scheduler_fields = ns.model('deleteGithubScheduler',  {
    "_id": fields.List(fields.String(description="Github 监控任务ID列表"))
})


# Github 监控任务删除
@ns.route('/delete/')
class DeleteGithubScheduler(ARLResource):

    @auth
    @ns.expect(delete_github_scheduler_fields)
    def post(self):
        """
        删除Github 监控任务
        """
        args = self.parse_args(delete_github_scheduler_fields)
        job_id_list = args.get("_id", [])

        ret_data = {"_id": job_id_list}

        for job_id in job_id_list:
            item = github_task.find_github_scheduler(job_id)
            if not item:
                return utils.build_ret(ErrorMsg.JobNotFound, ret_data)

        for job_id in job_id_list:
            github_task.delete_github_scheduler(job_id)

        return utils.build_ret(ErrorMsg.Success, ret_data)


update_github_scheduler_fields = ns.model('updateGithubScheduler',  {
    "_id": fields.String(required=True, description="Github 监控任务ID"),
    'name': fields.String(required=False, description="任务名"),
    'keyword': fields.String(required=False, description="关键字"),
    "cron": fields.String(required=False, description="Cron 表达式")
})


# Github 监控任务修改
@ns.route('/update/')
class UpdateGithubScheduler(ARLResource):

    @auth
    @ns.expect(update_github_scheduler_fields)
    def post(self):
        """
        修改 Github 监控任务
        """
        args = self.parse_args(update_github_scheduler_fields)
        job_id = args.get("_id")
        name = args.pop('name')
        keyword = args.pop('keyword')
        cron = args.pop('cron')

        item = github_task.find_github_scheduler(job_id)
        if not item:
            return utils.build_ret(ErrorMsg.JobNotFound, {"_id": job_id})

        if name:
            item["name"] = name

        if keyword:
            keyword = keyword.strip()
            item["keyword"] = keyword

        if cron:
            check_flag, msg = utils.check_cron_interval(cron)
            if not check_flag:
                return msg

            previous, next_sec, _ = utils.check_cron(cron)

            item["next_run_date"] = utils.time2date(time.time() + next_sec)
            item["cron"] = cron

        query = {
            "_id": ObjectId(job_id)
        }
        utils.conn_db('github_scheduler').find_one_and_replace(query, item)

        item["_id"] = str(item["_id"])

        return utils.build_ret(ErrorMsg.Success, data=item)


recover_github_scheduler_fields = ns.model('recoverGithubScheduler',  {
    "_id": fields.List(fields.String(required=True, description="Github 监控任务ID"))
})


# Github 监控任务恢复
@ns.route('/recover/')
class RecoverGithubScheduler(ARLResource):

    @auth
    @ns.expect(recover_github_scheduler_fields)
    def post(self):
        """
        恢复 Github 监控周期任务
        """
        args = self.parse_args(recover_github_scheduler_fields)
        job_id_list = args.get("_id")

        for job_id in job_id_list:
            item = github_task.find_github_scheduler(job_id)
            if not item:
                return utils.build_ret(ErrorMsg.JobNotFound, {"_id": job_id})

            status = item.get("status", SchedulerStatus.RUNNING)
            if status != SchedulerStatus.STOP:
                return utils.build_ret(ErrorMsg.SchedulerStatusNotStop, {"_id": job_id})

            github_task.recover_task(_id=job_id)

        return utils.build_ret(ErrorMsg.Success, {"job_id_list": job_id_list})


stop_github_scheduler_fields = ns.model('stopGithubScheduler',  {
    "_id": fields.List(fields.String(required=True, description="Github 监控任务ID"))
})


# Github 监控任务停止
@ns.route('/stop/')
class StopGithubScheduler(ARLResource):

    @auth
    @ns.expect(stop_github_scheduler_fields)
    def post(self):
        """
        停止 Github 监控周期任务
        """
        args = self.parse_args(stop_github_scheduler_fields)
        job_id_list = args.get("_id")

        for job_id in job_id_list:
            item = github_task.find_github_scheduler(job_id)
            if not item:
                return utils.build_ret(ErrorMsg.JobNotFound, {"_id": job_id})

            status = item.get("status", SchedulerStatus.RUNNING)
            if status != SchedulerStatus.RUNNING:
                return utils.build_ret(ErrorMsg.SchedulerStatusNotRunning, {"_id": job_id})

            github_task.stop_task(_id=job_id)

        return utils.build_ret(ErrorMsg.Success, {"job_id_list": job_id_list})
