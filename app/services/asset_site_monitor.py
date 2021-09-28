import threading
from app.helpers import asset_site
from app import utils
from app.helpers.scope import get_scope_by_scope_id
from app.helpers.message_notify import push_email, push_dingding
from .baseThread import BaseThread
from .fetchSite import fetch_site


logger = utils.get_logger()


class AssetSiteCompare(BaseThread):
    def __init__(self, scope_id):
        self._scope_id = scope_id
        sites = asset_site.find_site_by_scope_id(scope_id)
        logger.info("load {}  site from {}".format(len(sites), self._scope_id))
        super(AssetSiteCompare, self).__init__(targets=sites, concurrency=15)
        self.new_site_info_map = {}
        self.mutex = threading.Lock()
        self.site_change_map = {}

    def work(self, site):
        conn = utils.http_req(site)
        item = {
            "title": utils.get_title(conn.content),
            "status": conn.status_code
        }
        with self.mutex:
            self.new_site_info_map[site] = item

    def compare(self):
        site_info_list = asset_site.find_site_info_by_scope_id(scope_id=self._scope_id)
        for site_info in site_info_list:
            curr_site = site_info["site"]
            # 访问不了的站点，跳过
            if curr_site not in self.new_site_info_map:
                continue

            new_site_info = self.new_site_info_map[curr_site]
            if new_site_info["status"] in [404, 502, 504]:
                continue

            if new_site_info["title"] != site_info["title"]:
                # 只关注标题不为空
                if new_site_info["title"]:
                    self.site_change_map[curr_site] = site_info

            elif new_site_info["status"] != site_info["status"]:
                # 只关注变成200的变化
                if new_site_info["status"] == 200:
                    self.site_change_map[curr_site] = site_info

    def run(self):
        self._run()
        self.compare()
        return self.site_change_map


class AssetSiteMonitor(object):
    def __init__(self, scope_id):
        self.scope_id = scope_id
        self.status_change_list = []
        self.title_change_list = []
        scope_data = get_scope_by_scope_id(self.scope_id)
        if not scope_data:
            raise Exception("没有找到资产组 {}".format(self.scope_id))

        self.scope_name = scope_data["name"]

    def compare_status(self, site_info, old_site_info):
        curr_status = site_info["status"]
        old_status = old_site_info["status"]
        curr_site = site_info["site"]

        asset_site_id = old_site_info["_id"]

        if curr_status != old_status:
            item = {
                "site": curr_site,
                "status": curr_status,
                "old_status": old_status
            }
            logger.info("{} status {} => {}".format(curr_site, old_status, curr_status))

            self.update_asset_site(asset_site_id, site_info)
            self.status_change_list.append(item)
            return True

    def compare_title(self, site_info, old_site_info):
        curr_title = site_info["title"]
        old_title = old_site_info["title"]
        curr_site = site_info["site"]

        asset_site_id = old_site_info["_id"]

        if curr_title != old_title:
            item = {
                "site": curr_site,
                "title": curr_title,
                "old_title": old_title
            }

            logger.info("{} title {} => {}".format(curr_site, old_title, curr_title))

            self.update_asset_site(asset_site_id, site_info)

            self.title_change_list.append(item)
            return True

    def build_change_list(self):
        compare = AssetSiteCompare(scope_id=self.scope_id)
        site_change_map = compare.run()
        sites = list(site_change_map.keys())

        if not sites:
            logger.info("not found change ok site, scope_id: {}".format(self.scope_id))
            return

        site_info_list = fetch_site(sites)

        for site_info in site_info_list:
            curr_site = site_info["site"]
            if curr_site not in site_change_map:
                continue

            if "入口" not in site_info["tag"]:
                continue

            old_site_info = site_change_map[curr_site]

            if self.compare_title(site_info, old_site_info):
                continue

            if self.compare_status(site_info, old_site_info):
                continue

    def update_asset_site(self, asset_id, site_info):
        query = {
            "_id": asset_id
        }
        copy_site_info = site_info.copy()
        if "favicon" in copy_site_info:
            favicon = copy_site_info.pop("favicon")
            if "data" in favicon:
                copy_site_info["favicon.data"] = favicon["data"]
                copy_site_info["favicon.url"] = favicon["url"]
                copy_site_info["favicon.hash"] = favicon["hash"]

        copy_site_info["update_date"] = utils.curr_date_obj()

        utils.conn_db('asset_site').update(query, {"$set": copy_site_info})

    def build_status_html_report(self):
        html = ""
        style = 'style="border: 0.5pt solid; font-size: 14px;"'

        table_start = '''<table style="border-collapse: collapse;">
                    <thead>
                        <tr>
                            <th style="border: 0.5pt solid;">编号</th>
                            <th style="border: 0.5pt solid;">站点</th>
                            <th style="border: 0.5pt solid;">变化前状态码</th>
                            <th style="border: 0.5pt solid;">当前状态码</th>
                        </tr>
                    </thead>
                    <tbody>\n'''
        html += table_start

        tr_cnt = 0
        for item in self.status_change_list:
            tr_cnt += 1
            tr_tag = '<tr><td {}> {} </td><td {}> {} </td><td {}>' \
                     '{}</td> <td {}> {} </td></tr>\n'.format(
                style, tr_cnt, style, item["site"], style, item["old_status"], style, item["status"])

            html += tr_tag
            if tr_cnt > 10:
                break

        html += '</tbody></table>'
        return html

    def build_title_html_report(self):
        html = ""
        style = 'style="border: 0.5pt solid; font-size: 14px;"'

        table_start = '''<table style="border-collapse: collapse;">
                    <thead>
                        <tr>
                            <th style="border: 0.5pt solid;">编号</th>
                            <th style="border: 0.5pt solid;">站点</th>
                            <th style="border: 0.5pt solid;">变化前标题</th>
                            <th style="border: 0.5pt solid;">当前标题</th>
                        </tr>
                    </thead>
                    <tbody>\n'''
        html += table_start

        tr_cnt = 0
        for item in self.title_change_list:
            tr_cnt += 1
            title = item["title"].replace('>', "&#x3e;").replace('<', "&#x3c;")
            old_title = item["old_title"].replace('>', "&#x3e;").replace('<', "&#x3c;")
            tr_tag = '<tr><td {}> {} </td><td {}> {} </td><td {}>' \
                     '{}</td> <td {}> {} </td></tr>\n'.format(
                style, tr_cnt, style, item["site"], style, old_title, style, title)

            html += tr_tag
            if tr_cnt > 10:
                break

        html += '</tbody></table>'
        return html

    def build_html_report(self):
        html = " <br/><br/> 新发现标题变化 {}， 状态码变化 {}<br/><br/><br/>".format(
            len(self.title_change_list), len(self.status_change_list))

        if self.title_change_list:
            title_html = self.build_title_html_report()
            html += title_html

            html += "\n<br/><br/>\n"

        if self.status_change_list:
            status_html = self.build_status_html_report()
            html += status_html

        return html

    def build_status_markdown_report(self):
        tr_cnt = 0
        markdown = "状态码变化\n\n"

        for item in self.status_change_list:
            tr_cnt += 1
            markdown += "{}. [{}]({})  {} => {} \n".format(tr_cnt,
                                                           item["site"],
                                                           item["site"],
                                                           item["old_status"],
                                                           item["status"]
                                                           )
            if tr_cnt > 5:
                break

        return markdown

    def build_title_markdown_report(self):
        tr_cnt = 0
        markdown = "标题变化\n\n"

        for item in self.title_change_list:
            tr_cnt += 1
            markdown += "{}. [{}]({})  {} => {} \n".format(tr_cnt,
                                                           item["site"],
                                                           item["site"],
                                                           item["old_title"],
                                                           item["title"]
                                                           )
            if tr_cnt > 5:
                break

        return markdown

    def build_markdown_report(self):
        markdown = "\n站点监控-{} 灯塔消息推送\n\n".format(self.scope_name)

        markdown += "\n 新发现标题变化 {}， 状态码变化 {} \n\n".format(
            len(self.title_change_list), len(self.status_change_list))

        if self.title_change_list:
            markdown += self.build_title_markdown_report()
            markdown += "\n"

        if self.status_change_list:
            markdown += self.build_status_markdown_report()

        return markdown

    def run(self):
        self.build_change_list()
        if not self.status_change_list and not self.title_change_list:
            logger.info("not found change by {}".format(self.scope_id))
            return

        html_report = self.build_html_report()
        html_title = "[站点监控-{}] 灯塔消息推送".format(self.scope_name)
        push_email(title=html_title, html_report=html_report)

        markdown_report = self.build_markdown_report()
        push_dingding(markdown_report=markdown_report)


def asset_site_monitor(scope_id):
    monitor = AssetSiteMonitor(scope_id=scope_id)
    monitor.run()

