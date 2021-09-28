import time
import base64
import hmac
import urllib.parse
import hashlib
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.utils import http_req, get_logger
from app.config import Config
logger = get_logger()


class Push(object):
    """docstring for ClassName"""

    def __init__(self, asset_map, asset_counter):
        super(Push, self).__init__()
        self.asset_map = asset_map
        self.asset_counter = asset_counter
        self._domain_info_list = None
        self._site_info_list = None
        self._ip_info_list = None
        self.domain_len = self.asset_counter.get("domain", 0)
        self.ip_len = self.asset_counter.get("ip", 0)
        self.site_len = self.asset_counter.get("site", 0)
        self.task_name = self.asset_map.get("task_name", "")

    @property
    def domain_info_list(self):
        if self._domain_info_list is None:
            self._domain_info_list = self.build_domain_info_list()

        return self._domain_info_list

    @property
    def site_info_list(self):
        if self._site_info_list is None:
            self._site_info_list = self.build_site_info_list()

        return self._site_info_list

    @property
    def ip_info_list(self):
        if self._ip_info_list is None:
            self._ip_info_list = self.build_ip_info_list()

        return self._ip_info_list

    def build_domain_info_list(self):
        if "domain" not in self.asset_map:
            return []
        domain_info_list = []
        for old in self.asset_map["domain"]:
            domain_dict = dict()
            domain_dict["域名"] = old["domain"]
            domain_dict["解析类型"] = old["type"]
            domain_dict["记录值"] = old["record"][0]
            domain_info_list.append(domain_dict)

        return domain_info_list

    def build_ip_info_list(self):
        if "ip" not in self.asset_map:
            return []
        ip_info_list = []
        for old in self.asset_map["ip"]:
            ip_dict = dict()
            port_list = []
            for port_info in old["port_info"]:
                port_list.append(str(port_info["port_id"]))

            ip_dict["IP"] = old["ip"]
            ip_dict["端口数目"] = len(port_list)
            ip_dict["开放端口"] = ",".join(port_list[:10])
            ip_dict["组织"] = old["geo_asn"].get("organization")
            ip_info_list.append(ip_dict)

        return ip_info_list

    def build_site_info_list(self):
        if "site" not in self.asset_map:
            return []
        site_info_list = []
        for old in self.asset_map["site"]:
            site_dict = dict()
            site_dict["站点"] = old["site"]
            site_dict["标题"] = old["title"]
            site_dict["状态码"] = old["status"]
            site_dict["favicon"] = old["favicon"].get("hash", "")
            site_info_list.append(site_dict)
        return site_info_list

    def _push_dingding(self):
        tpl = ""
        if self.domain_len > 0:
            tpl = "[{}]新发现域名 `{}` , 站点 `{}`\n***\n".format(self.task_name, self.domain_len, self.site_len)
            tpl = "{}\n{}".format(tpl, dict2dingding_mark(self.domain_info_list))

        if self.ip_len > 0:
            tpl = "[{}]新发现 IP `{}` , 站点 `{}`\n***\n".format(self.task_name, self.ip_len, self.site_len)
            tpl = "{}\n{}".format(tpl, dict2dingding_mark(self.ip_info_list))

        tpl += "\n***\n"
        tpl = "{}\n{}".format(tpl, dict2dingding_mark(self.site_info_list))
        ding_out = dingding_send(msg=tpl, access_token=Config.DINGDING_ACCESS_TOKEN,
                                 secret=Config.DINGDING_SECRET, msgtype="markdown")
        if ding_out["errcode"] != 0:
            logger.warning("发送失败 \n{}\n {}".format(tpl, ding_out))
            return False
        return True

    def _push_email(self):
        html = ""
        if self.domain_len > 0:
            tpl = "<div> 新发现域名 {}, 站点 {}\n</div>".format(self.domain_len, self.site_len)
            html = tpl
            html += "<br/>"
            html += dict2table(self.domain_info_list)

        if self.ip_len > 0:
            tpl = "<div> 新发现 IP {}, 站点 {}\n</div>".format(self.ip_len, self.site_len)
            html = tpl
            html += "<br/>"
            html += dict2table(self.ip_info_list)

        html += "<br/><br/>"
        html += dict2table(self.site_info_list)

        title = "[{}] 灯塔消息推送".format(self.task_name[:50])
        send_email(host=Config.EMAIL_HOST, port=Config.EMAIL_PORT, mail=Config.EMAIL_USERNAME,
                   password=Config.EMAIL_PASSWORD, to=Config.EMAIL_TO, title=title, html=html)

        return True

    def push_dingding(self):
        try:
            if Config.DINGDING_ACCESS_TOKEN and Config.DINGDING_SECRET:
                if self._push_dingding():
                    logger.info("push dingding succ")
                    return True

        except Exception as e:
            logger.warning(self.task_name, e)

    def push_email(self):
        try:
            if Config.EMAIL_HOST and Config.EMAIL_USERNAME and Config.EMAIL_PASSWORD:
                self._push_email()
                logger.info("send email succ")
                return True
        except Exception as e:
            logger.warning(self.task_name, e)


def message_push(asset_map, asset_counter):
    logger.info("ARL push run")
    p = Push(asset_map=asset_map, asset_counter=asset_counter)
    p.push_dingding()
    p.push_email()


def dict2dingding_mark(info_list):
    if not info_list:
        return ""

    title_tpl = '  \t\t  '.join(map(str, info_list[0].keys()))
    items_tpl = ""
    cnt = 0
    for row in info_list:
        cnt += 1
        row = ' \t '.join(map(str, row.values()))
        items_tpl += "{}. {}\n".format(cnt, row)

    return "{}\n{}".format(title_tpl, items_tpl)


def dingding_send(msg, access_token, secret, msgtype="text", title="灯塔消息推送"):
    ding_url = "https://oapi.dingtalk.com/robot/send?access_token={}".format(access_token)
    timestamp = str(round(time.time() * 1000))
    secret_enc = secret.encode('utf-8')
    string_to_sign = '{}\n{}'.format(timestamp, secret)
    string_to_sign_enc = string_to_sign.encode('utf-8')
    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    param = "&timestamp={}&sign={}".format(timestamp, sign)
    ding_url = ding_url + param
    send_json = {
        "msgtype": msgtype,
        "text": {
            "content": msg
        },
        "markdown": {
            "title": title,
            "text": msg
        }
    }
    conn = http_req(ding_url, method='post', json=send_json)
    return conn.json()


def send_email(host, port, mail, password, to, title, html, smtp_timeout=10):
    context = ssl.create_default_context()
    if port == 465:
        server = smtplib.SMTP_SSL(host, port, context=context, timeout=smtp_timeout)
    else:
        server = smtplib.SMTP(host, port, timeout=smtp_timeout)

    msg = MIMEMultipart()
    msg['Subject'] = title
    msg['From'] = mail
    msg['To'] = to
    part1 = MIMEText(html, "html", "utf-8")
    msg.attach(part1)
    server.login(mail, password)
    server.send_message(msg)
    server.close()


def dict2table(info_list):
    if not info_list:
        return ""
    html = ""
    table_style = 'style="border-collapse: collapse;"'
    table_start = '<table {}>\n'.format(table_style)
    table_end = '</table>\n'
    style = 'style="border: 0.5pt solid windowtext;"'
    thead_start = '<thead><tr><th {}>序号</th><th {}>\n'.format(style, style)
    thead_end = '\n</th></tr></thead>'
    th_join_tpl = '</th>\n<th {}>'.format(style)
    thead_tpl = th_join_tpl.join(map(str, info_list[0].keys()))
    html += table_start
    html += thead_start
    html += thead_tpl
    html += thead_end

    tbody = "<tbody>\n"
    cnt = 0
    for row in info_list:
        cnt += 1
        td_join_tpl = '</td>\n<td {}>'.format(style)
        row_start = '<tr><td {}>{}</td>\n<td {}>'.format(style, cnt, style)
        items = [str(x).replace('>', "&#x3e;").replace('<', "&#x3c;") for x in row.values()]
        row = td_join_tpl.join(items)
        row_end = '</td>\n</tr>'
        row_tpl = row_start + row + row_end
        tbody = tbody + row_tpl + "\n"

    html = html + tbody + "</tbody>" + table_end

    return html

