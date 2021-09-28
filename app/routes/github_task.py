from bson import ObjectId
from flask_restplus import fields, Namespace
from app.utils import get_logger, auth
from app import utils
from . import base_query_fields, ARLResource, get_arl_parser
from app.modules import TaskStatus, ErrorMsg
from app.utils.github_task import submit_github_task
from app.celerytask import CeleryAction
from app import celerytask

ns = Namespace('github_task', description="Github 任务详情")

logger = get_logger()

base_search_fields = {
    'name': fields.String(required=False, description="任务名"),
    'keyword': fields.String(description="关键字"),
    'status': fields.String(description="任务状态"),
    '_id': fields.String(description="任务ID")
}

base_search_fields.update(base_query_fields)


add_github_task_fields = ns.model('AddGithubTask', {
    'name': fields.String(required=True, description="任务名"),
    'keyword': fields.String(required=True, description="关键字")
})


@ns.route('/')
class ARLGithubTask(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        Github 任务信息查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='github_task')

        return data

    @auth
    @ns.expect(add_github_task_fields)
    def post(self):
        """
        Github 任务添加
        """
        args = self.parse_args(add_github_task_fields)
        name = args.pop('name')
        keyword = args.pop('keyword')
        keyword = keyword.strip()
        if not keyword:
            return utils.build_ret(ErrorMsg.GithubKeywordEmpty, data={})

        task_data = {
            "name": name,
            "keyword": keyword,
            "start_time": "-",
            "end_time": "-",
            "status": TaskStatus.WAITING,
        }

        task_data = submit_github_task(task_data=task_data,
                           action=CeleryAction.GITHUB_TASK_TASK, delay_flag=True)

        if isinstance(task_data, str):
            return utils.build_ret(ErrorMsg.Error, data={"error": task_data})

        return utils.build_ret(ErrorMsg.Success, data=task_data)


delete_github_task_fields = ns.model('DeleteGithubTask',  {
    '_id': fields.List(fields.String(required=True, description="Github 任务ID"))
})


@ns.route('/delete/')
class DeleteARLGithubTask(ARLResource):
    @auth
    @ns.expect(delete_github_task_fields)
    def post(self):
        """
        Github 任务删除
        """
        done_status = [TaskStatus.DONE, TaskStatus.STOP, TaskStatus.ERROR]
        args = self.parse_args(delete_github_task_fields)
        task_id_list = args.pop('_id')

        for task_id in task_id_list:
            task_data = utils.conn_db('github_task').find_one({'_id': ObjectId(task_id)})
            if not task_data:
                return utils.build_ret(ErrorMsg.NotFoundTask, {"_id": task_id})

            if task_data["status"] not in done_status:
                return utils.build_ret(ErrorMsg.TaskIsRunning, {"_id": task_id})

        for task_id in task_id_list:
            utils.conn_db('github_task').delete_one({'_id': ObjectId(task_id)})
            utils.conn_db('github_result').delete_many({'github_task_id': task_id})

        return utils.build_ret(ErrorMsg.Success, {"_id": task_id_list})


stop_github_task_fields = ns.model('StopGithubTask',  {
    '_id': fields.List(fields.String(required=True, description="Github 任务ID"))
})


@ns.route('/stop/')
class StopARLGithubTask(ARLResource):
    @auth
    @ns.expect(stop_github_task_fields)
    def post(self):
        """
        Github 任务停止
        """
        done_status = [TaskStatus.DONE, TaskStatus.STOP, TaskStatus.ERROR]
        args = self.parse_args(stop_github_task_fields)
        task_id_list = args.pop('_id')

        for task_id in task_id_list:
            task_data = utils.conn_db('github_task').find_one({'_id': ObjectId(task_id)})
            if not task_data:
                return utils.build_ret(ErrorMsg.NotFoundTask, {"_id": task_id})

            if task_data["status"] in done_status:
                return utils.build_ret(ErrorMsg.TaskIsDone, {"_id": task_id})

            celery_id = task_data.get("celery_id")
            if not celery_id:
                return utils.build_ret(ErrorMsg.CeleryIdNotFound, {"_id": task_id})

            control = celerytask.celery.control

            control.revoke(celery_id, signal='SIGTERM', terminate=True)

            utils.conn_db('github_task').update_one({'_id': ObjectId(task_id)}, {"$set": {"status": TaskStatus.STOP}})

            utils.conn_db('github_task').update_one({'_id': ObjectId(task_id)}, {"$set": {"end_time": utils.curr_date()}})

        return utils.build_ret(ErrorMsg.Success, {"_id": task_id_list})
