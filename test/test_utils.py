import unittest
from app.utils.fingerprint import parse_human_rule, transform_rule_map, \
    fetch_fingerprint, load_fingerprint
from app import utils


class TestCDNName(unittest.TestCase):
    def test_parse_human_rule(self):
        human_rule = 'header="test.php" || body="test.gif" || title="test title" || body="test22.gif"'
        rule_map = parse_human_rule(human_rule)

        self.assertTrue(rule_map["html"][0] == "test.gif")
        self.assertTrue(rule_map["headers"][0] == "test.php")
        self.assertTrue(rule_map["title"][0] == "test title")

        human_rule = "xx=fdf || fdf=xxx"
        rule_map = parse_human_rule(human_rule)
        self.assertTrue(rule_map is None)

    def test_utils_get_fld(self):
        fld = utils.get_fld("www.baidu.com")
        self.assertTrue(fld == "baidu.com")

        fld = utils.get_fld("baidu.com")
        self.assertTrue(fld == "baidu.com")

    def test_transform_rule_map(self):
        human_rule = 'header="test.php" || body="test.gif" || title="test title" || body="test22.gif"'
        rule_map = parse_human_rule(human_rule)
        human_rule = transform_rule_map(rule_map)
        self.assertTrue('title="test title"' in human_rule)

    def test_fetch_fingerprint(self):
        site = "https://www.baidu.com/"
        conn = utils.http_req(site)
        headers = utils.get_headers(conn)
        title = utils.get_title(conn.content)
        finger_list = [
            {
                "name": "百度测试",
                "rule": {
                    "html": [
                        "百度"
                    ],
                    "title": [],
                    "headers": [],
                    "favicon_hash": []
                }
            },
            {
                "name": "百度测试2",
                "rule": {
                    "html": [],
                    "title": ["百度222222", "百度"],
                    "headers": [],
                    "favicon_hash": []
                }
            },
            {
                "name": "百度测试3",
                "rule": {
                    "html": [],
                    "title": [],
                    "headers": ["TTTBAIDUIDTTT", "BAIDUID"],
                    "favicon_hash": []
                }
            },
            {
                "name": "百度测试4",
                "rule": {
                    "html": [],
                    "title": [],
                    "headers": [],
                    "favicon_hash": [789, 123456]
                }
            }
        ]
        finger_list.extend(load_fingerprint())
        result = fetch_fingerprint(content=conn.content, headers=headers,
                                   title=title, favicon_hash=789, finger_list=finger_list)
        self.assertTrue(len(result) >= 4)
        self.assertTrue(result[0] == finger_list[0]["name"])
        self.assertTrue(result[3] == finger_list[3]["name"])


if __name__ == '__main__':
    unittest.main()
