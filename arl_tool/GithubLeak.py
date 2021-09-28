import base64
import sys
import os
from collections import deque
ARL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "./../"))
sys.path.append(ARL_PATH)
from app.utils import http_req, get_logger, gen_md5, load_file
from app.config import Config
import time

from app.utils.push import send_email

logger = get_logger()


class GithubResult(object):
    def __init__(self, item):
        self.raw_data = item
        self.git_url = item["git_url"]
        self.html_url = item["html_url"]
        self.repo_full_name = item["repository"]["full_name"]
        self.path = item["path"]
        self.hash_md5 = gen_md5(self.repo_full_name + "/" + item["path"])
        self._content = None

    def __str__(self):
        return "{} {}".format(self.repo_full_name, self.path)

    def __hash__(self):
        return self.hash_md5

    def __eq__(self, other):
        return self.hash_md5 == other.hash_md5

    def __repr__(self):
        return "<GithubResult>{} {}".format(self.hash_md5, str(self))

    @property
    def content(self):
        if self._content is None:
            try:
                content_base64 = github_client(self.git_url)["content"]
                decode_bytes = base64.decodebytes(content_base64.encode("utf-8"))
                self._content = decode_bytes.decode("utf-8", errors="replace")
            except Exception as e:
                logger.info("error on {}".format(self.git_url))
                logger.exception(e)
                self._content = ""

            return self._content
        else:
            return self._content

    def human_content(self, keyword):
        lines = self.content.split("\n")
        max_len = 8
        before_lines = deque(maxlen=max_len)
        index = 0
        for line in lines:
            if keyword in line:
                break
            before_lines.append(line)
            index += 1

        after_lines = lines[index:index + max_len]
        return "{}\n{}".format("\n".join(before_lines), "\n".join(after_lines))


def github_search_code(query, order="desc", sort="indexed", per_page=100, page=1):
    url = "https://api.github.com/search/code"
    params = {
        "q": query,
        "order": order,
        "sort": sort,
        "per_page": per_page,
        "page": page
    }

    data = github_client(url, params=params)
    logger.info("search {} count {}".format(query, data["total_count"]))
    ret_list = []
    for item in data["items"]:
        result = GithubResult(item=item)
        ret_list.append(result)

    return ret_list


def github_client(url, params=None):
    headers = {
        "Authorization": "Bearer {}".format(Config.GITHUB_TOKEN),
        "Accept": "application/vnd.github.v3+json"
    }
    time.sleep(1)
    conn = http_req(url, params=params, headers=headers)
    data = conn.json()
    if conn.status_code != 200:
        message = data.get("message", "Github 错误")
        raise Exception(message)

    return data


class GithubSearch(object):
    def __init__(self, query):
        self.results = []
        self.query = query
        language_query = "language:Dockerfile language:INI language:Shell " \
                         "language:\"Java Properties\" language:\"SSH Config\" language:\"Protocol Buffer\" " \
                         "language:Gradle language:\"Maven POM\""

        extension_query = "extension:php extension:java extension:py extension:go extension:js extension:json " \
                          "extension:sql extension:yaml extension:yml extension:conf extension:config extension:jsp"

        self.built_in_rules = [language_query, extension_query]

    def search(self):
        try:
            for build_in in self.built_in_rules:
                query = "{} {}".format(self.query, build_in)
                results = github_search_code(query=query, per_page=100)
                for result in results:
                    if result not in self.results:
                        self.results.append(result)
        except Exception as e:
            logger.info("Error on {} {}".format(self.query, e))
            logger.exception(e)

        logger.info("{} search result {}".format(self.query, len(self.results)))
        return self.results


class HashManager(object):
    def __init__(self):
        self._hash_list = None
        self.hash_file = Config.GITHUB_HASH_FILE

    @property
    def hash_list(self):
        if self._hash_list is None:
            if not os.path.isfile(self.hash_file):
                self._hash_list = []
            else:
                hash_list = list(map(str.strip, load_file(self.hash_file)))
                self._hash_list = hash_list

        return self._hash_list

    def append_hash(self, hash_str):
        if hash_str in self.hash_list:
            return

        self._hash_list.append(hash_str)
        with open(self.hash_file, "a", encoding="utf-8") as f:
            f.write("{}\n".format(hash_str))

    def __contains__(self, value):
        return value in self.hash_list


class GithubLeak(object):
    def __init__(self, query):
        self.hash_manager = HashManager()
        self.new_results = []
        self.query = query
        self.github_search = GithubSearch(self.query)

    def build_html_report(self):
        repo_map = dict()
        for result in self.new_results:
            repo_name = result.repo_full_name
            if repo_map.get(repo_name) is None:
                repo_map[repo_name] = [result]
            else:
                repo_map[repo_name].append(result)

        repo_cnt = 0
        html = "<br/><br/> <div> 搜索: {}  仓库数：{}  结果数： {} </div>".format(self.query,
                                                                        len(repo_map.keys()), len(self.new_results))
        for repo_name in repo_map:
            repo_cnt += 1
            start_div = '<br/><br/><br/><div>#{} <a href="https://github.com/{}"> {} </a> 结果数：{}</div><br/>\n'.format(
                repo_cnt, repo_name, repo_name, len(repo_map[repo_name]))
            table_start = '''<table style="border-collapse: collapse;">
            <thead>
                <tr>
                    <th style="border: 0.5pt solid;">编号</th>
                    <th style="border: 0.5pt solid;">文件名</th>
                    <th style="border: 0.5pt solid;">代码</th>
                </tr>
            </thead>
            <tbody>\n'''
            html += start_div
            html += table_start

            style = 'style="border: 0.5pt solid; font-size: 14px;"'
            tr_cnt = 0
            for item in repo_map[repo_name]:
                tr_cnt += 1
                code_content = item.human_content(self.query).replace('>', "&#x3e;").replace('<', "&#x3c;")
                tr_tag = '<tr><td {}> {} </td><td {}> <a href="{}">{}</a> </td><td {}>' \
                         '<pre>{}</pre></td></tr>\n'.format(
                    style, tr_cnt, style, item.html_url, item.path, style, code_content)

                html += tr_tag
                if tr_cnt > 10:
                    break

            table_end = '</tbody></table>'
            end_div = "</div>"

            html += table_end
            html += end_div

        return html

    def run(self):
        results = self.github_search.search()
        for x in results:
            if x.hash_md5 not in self.hash_manager:
                self.hash_manager.append_hash(x.hash_md5)
            else:
                continue
            if self.filter_result(x):
                continue

            logger.info("found {}".format(x))
            self.new_results.append(x)

        self.new_results = self.new_results

        html = self.build_html_report()
        # with open("report.html", "w") as f:
        #     f.write(html)

        if self.new_results:
            logger.info("found new result {} {}".format(self.query, len(self.new_results)))
            send_email(host=Config.EMAIL_HOST, port=Config.EMAIL_PORT, mail=Config.EMAIL_USERNAME,
                       password=Config.EMAIL_PASSWORD, to=Config.EMAIL_TO,
                       title="[Github-{}] 灯塔消息推送".format(self.query), html=html)

        return self.new_results

    def filter_result(self, result: GithubResult):
        content_keyword_list = ["DOMAIN-SUFFIX", "HOST-SUFFIX"]
        for keyword in content_keyword_list:
            if keyword in result.content:
                return True

        return False


if __name__ == '__main__':
    import sys
    github_leak = GithubLeak(sys.argv[1])
    github_leak.run()
