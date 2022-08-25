import logging
import time

from app import utils
from app.config import Config


class DNSQueryBase(object):
    def __init__(self):
        self.source_name = None
        self.logger = utils.get_logger()

    def init_key(self, **kwargs):
        """
        用来初始化各种key
        :param kwargs:
        :return:
        """
        raise NotImplementedError()

    def sub_domains(self, target):
        """
        根据子域名查询
        :param target:
        :return:
        """
        raise NotImplementedError()

    def query(self, target):
        t1 = time.time()
        self.logger.info("start query {} on {}".format(target, self.source_name))
        try:
            domains = self.sub_domains(target)
        except Exception as e:
            self.logger.error(e)
            return []

        if not isinstance(domains, list):
            self.logger.warning("{} is not list".format(domains))
            return []

        """下面是过滤掉不合法的数据"""
        subdomains = []

        for domain in domains:
            domain = domain.strip("*.")
            domain = domain.lower()
            if not domain:
                continue

            if not domain.endswith(".{}".format(target)):
                continue

            # 删除掉过长的域名
            if len(domain) - len(target) >= Config.DOMAIN_MAX_LEN:
                continue

            if not utils.is_valid_domain(domain):
                continue

            # 屏蔽和谐域名和黑名单域名
            if utils.check_domain_black(domain):
                continue

            if utils.domain_parsed(domain):
                subdomains.append(domain)

        subdomains = list(set(subdomains))

        t2 = time.time()
        self.logger.info("end query {} on {}, source result:{}, real result:{} ({:.2f}s)".format(
            target, self.source_name, len(domains), len(subdomains), t2 - t1))

        return subdomains


# *****  执行域名查询插件
"""
返回: [{
    "domain": "www.baidu.com",
    "source": "crtsh"
}]
"""
# *********


def run_query_plugin(target, sources=None):
    """
    批量运行子域名查询插件
    :param sources:
    :param target:
    :return:
    """
    if sources is None:
        sources = []

    plugins = utils.load_query_plugins(Config.dns_query_plugin_path)
    query_key = Config.QUERY_PLUGIN_CONFIG
    logger = utils.get_logger()
    ret = []
    subdomains = set()
    t1 = time.time()
    for p in plugins:
        try:
            source_name = p.source_name
            if sources and source_name not in sources:
                continue

            # ***　查看是否有配置
            if query_key.get(source_name):
                source_kwargs = query_key[source_name]
                if not isinstance(source_kwargs, dict):
                    logger.warning("{} config {} is not dict".format(source_name, source_kwargs))
                    continue

                # 判断是否为空，为空就跳过 init_key 调用
                if all(source_kwargs.values()):
                    p.init_key(**source_kwargs)
                else:
                    logger.debug("skip {}, config is not set".format(source_name))
                    continue

            results = p.query(target)
            for result in results:
                if result in subdomains:
                    continue
                item = {
                    "domain": result,
                    "source": source_name
                }
                ret.append(item)
                subdomains.add(result)

        except Exception as e:
            error_str = str(e)
            if "please set fofa key" in error_str:
                logger.debug(error_str)
            else:
                logger.error(str(e))

    t2 = time.time()
    logger.info("{} subdomains result {} ({:.2f}s)".format(target, len(subdomains), t2 - t1))
    return ret
