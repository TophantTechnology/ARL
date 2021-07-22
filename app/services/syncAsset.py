import copy
from app.utils import conn_db as conn
from app import utils
logger = utils.get_logger()


class SyncAsset():
    def __init__(self, task_id, scope_id, update_flag=False,  category=None, task_name=""):
        self.available_category = ["site", "domain", "ip"]

        if category is None:
            self.category_list = self.available_category
        else:
            self.category_list = category

        self.task_id = task_id
        self.scope_id = scope_id
        self.task_name = task_name
        self.update_flag = update_flag

        self.new_asset_map = {
            "site": [],
            "domain": [],
            "ip": [],
            "task_name": task_name
        }

        self.new_asset_counter = {
            "site": 0,
            "domain": 0,
            "ip": 0
        }
        self.max_record_asset_count = 10

    def sync_by_category(self, category):
        dist_collection = 'asset_{}'.format(category)
        for data in conn(category).find({"task_id": self.task_id}):
            query = {"scope_id": self.scope_id, category: data[category]}
            del data["_id"]
            data["scope_id"] = self.scope_id

            old = conn(dist_collection).find_one(query)
            if old is None:
                data["save_date"] = utils.curr_date_obj()
                data["update_date"] = data["save_date"]
                logger.info("sync {}, insert {}  {} -> {}".format(
                    category, data[category], self.task_id, self.scope_id))

                #记录新插入的资产
                if category in self.new_asset_map:
                    if self.new_asset_counter[category] < self.max_record_asset_count:
                        self.new_asset_map[category].append(copy.deepcopy(data))
                    self.new_asset_counter[category] += 1

                conn(dist_collection).insert_one(data)

            if old and self.update_flag:
                curr_date = utils.curr_date_obj()
                data["save_date"] = old.get("save_date", curr_date)
                data["update_date"] = curr_date
                if category == 'ip':
                    if data.get("domain") and old.get("domain"):
                        old["domain"].extend(data["domain"])
                        data["domain"] = list(set(old["domain"]))

                logger.info("sync {}, replace {}  {} -> {}".format(
                    category, data[category], self.task_id, self.scope_id))
                conn(dist_collection).find_one_and_replace(query, data)

    def run(self):
        logger.info("start sync {} -> {}".format(self.task_id, self.scope_id))
        for category in self.category_list:
            if category not in self.available_category:
                logger.warning("not found {} category in {}".format(category, self.available_category))
                continue

            self.sync_by_category(category)

        logger.info("end sync {} -> {}".format(self.task_id, self.scope_id))

        return self.new_asset_map, self.new_asset_counter


def sync_asset(task_id, scope_id, update_flag=False,  category=None, push_flag=False, task_name=""):
    sync = SyncAsset(task_id=task_id, scope_id=scope_id,
                     update_flag=update_flag, category=category, task_name=task_name)
    new_asset_map, new_asset_counter = sync.run()
    if 'ip' in new_asset_map:
        new_asset_map.pop('ip')

    if 'ip' in new_asset_counter:
        new_asset_counter.pop('ip')

    if push_flag:
        utils.message_push(asset_map=new_asset_map, asset_counter=new_asset_counter)
