import json
from app.config import Config
from app.utils import get_logger, conn_db, load_file
logger = get_logger()

# 解析规则，只有或，且条件不能出现=

'''
html
title
headers
favicon_hash
'''


def parse_human_rule(rule):
    rule_map = {
        "html": [],
        "title": [],
        "headers": [],
        "favicon_hash": []
    }
    key_map = {
        "body": "html",
        "title": "title",
        "header": "headers",
        "icon_hash": "favicon_hash"
    }
    split_result = rule.split("||")
    empty_flag = True

    for item in split_result:
        key_value = item.split("=")
        key = key_value[0]
        key = key.strip()
        if len(key_value) == 2:
            if key not in key_map:
                logger.info("{} 不在指定关键字中".format(key))
                continue

            value = key_value[1]
            value = value.strip()
            if len(value) <= 6:
                logger.info("{} 长度少于7".format(value))
                continue

            if value[0] != '"' or value[-1] != '"':
                logger.info("{} 没有在双引号内".format(value))
                continue

            empty_flag = False

            # 防御性转换成gbk
            value.encode("gbk")

            value = value[1:-1]
            if key == "icon_hash":
                value = int(value)

            rule_map[key_map[key]].append(value)

    if empty_flag:
        return None

    return rule_map


def transform_rule_map(rule):
    key_map = {
        "html": "body",
        "title": "title",
        "headers": "header",
        "favicon_hash": "icon_hash"
    }
    human_rule_list = []
    for key in rule:
        if key not in key_map:
            logger.info("{} 不在指定关键字中".format(key))
            continue

        for rule_item in rule[key]:
            human_rule_list.append('{}="{}"'.format(key_map[key], rule_item))

    return " || ".join(human_rule_list)


web_app_rules = json.loads("\n".join(load_file(Config.web_app_rule)))


def load_fingerprint():
    items = list(conn_db('fingerprint').find())
    for rule in web_app_rules:
        new_rule = dict()
        new_rule["name"] = rule
        new_rule["rule"] = web_app_rules[rule]
        items.append(new_rule)
    return items


# 根据规则列表来获取应用名，单个规则字段是或的关系
def fetch_fingerprint(content, headers, title, favicon_hash, finger_list):
    finger_name_list = []

    for finger in finger_list:
        rule = finger["rule"]
        rule_name = finger["name"]
        match_flag = False
        for html in rule["html"]:
            if html.encode("utf-8") in content:
                finger_name_list.append(rule_name)
                match_flag = True
                break

            try:
                if html.encode("gbk") in content:
                    finger_name_list.append(rule_name)
                    match_flag = True
                    break
            except Exception as e:
                logger.debug("error on fetch_fingerprint {} to gbk".format(html))

        if match_flag:
            continue
        for header in rule["headers"]:
            if header in headers:
                finger_name_list.append(rule_name)
                match_flag = True
                break

        if match_flag:
            continue
        for rule_title in rule["title"]:
            if rule_title in title:
                finger_name_list.append(rule_name)
                match_flag = True
                break

        if match_flag:
            continue
        if isinstance(rule.get("favicon_hash"), list):
            for rule_hash in rule["favicon_hash"]:
                if rule_hash == favicon_hash:
                    finger_name_list.append(rule_name)
                    break

    return finger_name_list
