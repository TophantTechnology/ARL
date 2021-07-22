from bson import ObjectId
from app import utils


# 任务类中一些相关公共类
class CommonTask(object):
    def __init__(self, task_id):
        self.task_id = task_id

    def insert_task_stat(self):
        query = {
            "_id": ObjectId(self.task_id)
        }

        stat = utils.arl.task_statistic(self.task_id)

        update = {"$set": {"statistic": stat}}

        utils.conn_db('task').update_one(query, update)

    def insert_cip_stat(self):
        cip_map = utils.arl.gen_cip_map(self.task_id)
        for cidr_ip in cip_map:
            item = cip_map[cidr_ip]
            ip_list = list(item["ip_set"])
            domain_list = list(item["domain_set"])

            data = {
                "cidr_ip": cidr_ip,
                "ip_count": len(ip_list),
                "ip_list": ip_list,
                "domain_count": len(domain_list),
                "domain_list": domain_list,
                "task_id": self.task_id
            }

            utils.conn_db('cip').insert_one(data)
