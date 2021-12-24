import base64
from collections import deque
from app.utils import http_req, get_logger, gen_md5
from app.config import Config
from app.utils.time import parse_datetime
import time


logger = get_logger()


class GithubResult(object):
    def __init__(self, item):
        self.raw_data = item
        self.git_url = item["git_url"]
        self.html_url = item["html_url"]
        self.repo_full_name = item["repository"]["full_name"]
        self.path = item["path"]
        self.hash_md5 = gen_md5(self.repo_full_name + "/" + item["path"])
        self._commit_date = None  # 记录文件最后一次 Commit 时间
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

    @property
    def commit_date(self):
        if self._commit_date is None:
            commit_url = "https://api.github.com/repos/{}/commits".format(
                    self.repo_full_name)
            params = {
                "per_page": 1,
                "path": self.path
            }
            try:

                commit_info = github_client(commit_url, params=params)
                assert commit_info

                # 先保存为字符串吧
                self._commit_date = str(parse_datetime(commit_info[0]["commit"]["author"]["date"]))
            except Exception as e:
                logger.info("error on {}, {}".format(commit_url, self.path))
                logger.exception(e)
                self._commit_date = ""

        return self._commit_date

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

    def to_dict(self):
        item = {
            "git_url": self.git_url,
            "html_url": self.html_url,
            "repo_full_name":  self.repo_full_name,
            "path": self.path,
            "hash_md5": self.hash_md5,
            "commit_date": self.commit_date
        }
        return item


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

    total_count = data["total_count"]
    if data["total_count"] > 0 and len(ret_list) == 0 and page == 1:
        logger.warning("Query items empty {},  {}".format(total_count, query))

    return ret_list, total_count


def github_client(url, params=None, cnt=0):
    headers = {
        "Authorization": "Bearer {}".format(Config.GITHUB_TOKEN),
        "Accept": "application/vnd.github.v3+json"
    }
    time.sleep(2.5)
    conn = http_req(url, params=params, headers=headers)
    data = conn.json()
    if conn.status_code != 200:
        message = data.get("message", "Github 错误")
        if cnt < 3:
            cnt += 1
            if "You have triggered an abuse detection mechanism" in message \
                    or "API rate limit exceeded for user ID" in message\
                    or "You have exceeded a secondary rate limit" in message:
                sleep_time = 20 + 15*cnt
                logger.info("rate-limit retry {} {}, time sleep {}".format(cnt, params, sleep_time))
                time.sleep(sleep_time)
                return github_client(url, params=params, cnt=cnt)

        raise Exception(message)

    return data


class GithubSearch(object):
    def __init__(self, query):
        self.results = []
        self.query = query
        language_query = "language:Dockerfile " \
                         "language:\"Java Properties\" language:\"Protocol Buffer\" " \
                         "language:Gradle language:\"Maven POM\""

        language_query_2 = "language:Python language:\"Git Config\" " \
                           "language:INI language:Shell  language:\"SSH Config\""

        extension_query = "extension:java extension:js extension:json " \
                          "extension:sql extension:yaml extension:yml extension:conf extension:config " \
                          "extension:jsp"

        extension_query_2 = "extension:php extension:py extension:go extension:bat extension:cfg " \
                            "extension:env extension:exs extension:ini " \
                            "extension:pem extension:ppk extension:cs"

        self.built_in_rules = [language_query, language_query_2, extension_query, extension_query_2]

        self.max_page = 3  # 最大翻页数目
        self.per_page = 100  # 每页数目
        self.total_count = 0  # 保存搜索结果总数

    def search(self):
        try:
            search_cnt = 0
            total_search_cnt = len(self.built_in_rules)
            for build_in in self.built_in_rules:
                search_cnt += 1
                build_in = build_in.strip()
                if not build_in:
                    continue

                curr_page = 1
                query = "{} {}".format(self.query, build_in)
                results, total_count = github_search_code(query=query, per_page=self.per_page, page=curr_page)
                logger.info("[{}/{}] page:1 keyword:{} total:{}".format(search_cnt,
                                                                        total_search_cnt,  self.query, total_count))

                self.total_count += total_count

                # 对于根据文件来查的，应该只跑一页
                if "filename:" not in build_in:
                    while (total_count / 100) > curr_page and curr_page < self.max_page:
                        curr_page += 1
                        next_results, total_count = github_search_code(query=query, per_page=self.per_page, page=curr_page)
                        logger.info("page:{} keyword:{} total:{}".format(curr_page, self.query, total_count))
                        results.extend(next_results)

                for result in results:
                    if result not in self.results:
                        self.results.append(result)
        except Exception as e:
            logger.info("Error on {} {}".format(self.query, e))
            logger.exception(e)

        logger.info("{} search result {}".format(self.query, len(self.results)))
        return self.results


def github_search(keyword):
    search = GithubSearch(keyword)
    return search.search()
