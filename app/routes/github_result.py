from flask_restx import fields, Namespace
from app.utils import get_logger, auth
from . import base_query_fields, ARLResource, get_arl_parser

ns = Namespace('github_result', description="Github 结果详情")

logger = get_logger()

base_search_fields = {
    'path': fields.String(required=False, description="路径名称"),
    'repo_full_name': fields.String(description="仓库名称"),
    'human_content': fields.String(description="内容"),
    'github_task_id': fields.String(description="任务ID")
}

base_search_fields.update(base_query_fields)


@ns.route('/')
class ARLGithubResult(ARLResource):
    parser = get_arl_parser(base_search_fields, location='args')

    @auth
    @ns.expect(parser)
    def get(self):
        """
        Github 结果详情查询
        """
        args = self.parser.parse_args()
        data = self.build_data(args=args, collection='github_result')

        return data


