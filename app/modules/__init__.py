from .ipInfo import PortInfo, IPInfo
from .baseInfo import BaseInfo
from .domainInfo import DomainInfo
from .pageInfo import PageInfo
from app.config import Config


class ScanPortType:
    TEST = Config.TOP_10
    TOP100 = Config.TOP_100
    TOP1000 = Config.TOP_1000
    ALL = "0-65535"


class DomainDictType:
    TEST = Config.DOMAIN_DICT_TEST
    BIG = Config.DOMAIN_DICT_2W


class CollectSource:
    DOMAIN_BRUTE = "domain_brute"
    BAIDU = "baidu"
    RISKIQ = "riskIQ"
    ALTDNS = "altdns"
    ARL = "arl"
    SITESPIDER = "site_spider"
    SEARCHENGINE = "search_engine"
    MONITOR = "monitor"
    CRTSH = "crtsh"


class TaskStatus:
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"
    STOP = "stop"


class TaskScheduleStatus:
    DONE = "done"
    SCHEDULED = "scheduled"
    STOP = "stop"
    ERROR = "error"


class TaskTag:
    """任务标签"""

    """带资产发现的任务"""
    TASK = "task"

    """域名监控任务"""
    MONITOR = "monitor"

    """风险巡航任务"""
    RISK_CRUISING = "risk_cruising"


class TaskType:
    """任务目标类别"""

    """IP任务"""
    IP = "ip"

    """域名任务"""
    DOMAIN = "domain"

    """站点， 风险巡航"""
    RISK_CRUISING = "risk_cruising"

    """资产站点更新"""
    ASSET_SITE_UPDATE = "asset_site_update"

    """Fofa 任务"""
    FOFA = "fofa"


class SiteAutoTag:
    ENTRY = "入口"
    INVALID = "无效"


class TaskSyncStatus:
    WAITING = "waiting"
    RUNNING = "running"
    ERROR = "error"
    DEFAULT = "default"


class SchedulerStatus:
    RUNNING = "running"
    STOP = "stop"


class AssetScopeType:
    DOMAIN = "domain"
    IP = "ip"


class PoCCategory:
    POC = "漏洞PoC"
    SNIFFER = "协议识别"
    SYSTEM_BRUTE = "服务弱口令"
    WEBB_RUTE = "应用弱口令"


class CeleryAction:
    """celery任务celery_action字段"""

    """常规IP任务"""
    IP_TASK = "ip_task"

    """常规域名任务"""
    DOMAIN_TASK = "domain_task"

    """域名监测任务"""
    DOMAIN_EXEC_TASK = "domain_exec_task"

    """IP 类型监测任务"""
    IP_EXEC_TASK = "ip_exec_task"

    """同步已有任务"""
    DOMAIN_TASK_SYNC_TASK = "domain_task_sync_task"

    """PoC运行任务"""
    RUN_RISK_CRUISING = "run_risk_cruising"

    """Fofa 查询任务"""
    FOFA_TASK = "fofa_task"

    """Github 泄漏任务"""
    GITHUB_TASK_TASK = "github_task_task"

    """Github 泄漏监控任务"""
    GITHUB_TASK_MONITOR = "github_task_monitor"

    """资产站点更新任务"""
    ASSET_SITE_UPDATE = "asset_site_update"


error_map = {
    'CeleryIdNotFound': {
        "message": "没有找到Celery id",
        "code": 102,
    },
    'NotFoundTask': {
        "message": "没有找到任务",
        "code": 103,
    },
    "TaskIsRunning": {
        "message": "任务运行中",
        "code": 104,
    },
    "TaskIsDone": {
        "message": "任务已经完成",
        "code": 105,
    },
    "Success": {
        "message": "success",
        "code": 200,
    },
    "NotLogin": {
        "message": "未登录",
        "code": 401,
    },
    "NotFoundScopeID": {
        "message": "没有找到资产范围ID",
        "code": 601,
    },
    "NotFoundScope": {
        "message": "没有找到对应的资产范围",
        "code": 602,
    },
    "ExistScope": {
        "message": "已存在对应的资产范围",
        "code": 603,
    },
    "IntervalLessThan3600": {
        "message": "监控任务时间间隔不能小于6小时（21600s）",
        "code": 700,
    },
    "DomainNotFoundViaScope": {
        "message": "域名不在给定的资产范围中",
        "code": 701,
    },
    "DomainViaJob": {
        "message": "给定资产范围中的域名已经存在监控任务",
        "code": 699,
    },
    "DomainNotViaJob": {
        "message": "给定资产范围中的域名不存在监控任务",
        "code": 698,
    },
    "JobNotFound": {
        "message": "监控任务未找到",
        "code": 702,
    },
    "DomainInvalid": {
        "message": "域名无效",
        "code": 703,
    },
    "TargetInvalid": {
        "message": "任务目标无效",
        "code": 704,
    },
    "IPInBlackIps": {
        "message": "目标IP不允许下发",
        "code": 705,
    },
    "TaskTargetIsEmpty": {
        "message": "任务目标为空",
        "code": 706,
    },
    "TaskSyncDealing": {
        "message": "任务资产同步处理中",
        "code": 801,
    },
    "TaskTypeIsNotDomain": {
        "message": "不是域名发现任务",
        "code": 802,
    },
    "TaskTargetNotInScope": {
        "message": "任务目标不在资产组中",
        "code": 802,
    },
    "DomainInScope": {
        "message": "域名已经存在指定资产组中",
        "code": 803,
    },
    "URLInvalid": {
        "message": "URL无效",
        "code": 804,
    },
    "SiteURLNotDomain": {
        "message": "非域名类型URL",
        "code": 805,
    },
    "SiteInScope": {
        "message": "站点已在指定资产中",
        "code": 806,
    },
    "DomainNotFoundNotInScope": {
            "message": "没有发现可以添加的域名",
            "code": 807,
    },
    "SchedulerStatusNotRunning": {
        "message": "监控任务非运行状态",
        "code": 901,
    },
    "SchedulerStatusNotStop": {
        "message": "监控任务非停止状态",
        "code": 902,
    },
    "ResultSetIDNotFound": {
        "message": "结果集 ID 没有找到",
        "code": 1001,
    },
    "ResultSetIsEmpty": {
        "message": "结果集中目标为空",
        "code": 1002,
    },
    "PoCTargetIsEmpty": {
        "message": "PoC 任务目标为空",
        "code": 1003,
    },
    "QueryResultIsEmpty": {
        "message": "查询结果为空",
        "code": 1004,
    },
    "PolicyIDNotFound": {
        "message": "策略不存在",
        "code": 1100,
    },
    "RiskCruisingPoCConfigIsEmpty": {
        "message": "风险巡航任务选择的策略PoC配置字段不能为空",
        "code": 1101,
    },
    "BruteTaskBruteConfigIsEmpty": {
        "message": "弱口令任务选择的策略爆破配置字段不能为空",
        "code": 1102,
    },
    "PolicyDataIsEmpty": {
        "message": "策略数据为空",
        "code": 1103,
    },
    "FofaConnectError": {
        "message": "连接Fofa API异常",
        "code": 1201,
    },
    "FofaKeyError": {
        "message": "Fofa 认证信息错误",
        "code": 1202,
    },
    "FofaResultEmpty": {
        "message": "Fofa 查询结果为空",
        "code": 1203,
    },
    "SiteIdNotFound": {
        "message": "站点没有找到",
        "code": 1300,
    },
    "SiteTagIsExist": {
        "message": "站点标签已经存在",
        "code": 1301,
    },
    "SiteTagNotExist": {
        "message": "站点标签没有找到",
        "code": 1302,
    },
    "ScopeTypeIsNotIP": {
        "message": "资产组IP范围无效",
        "code": 1303,
    },
    "IsForbiddenDomain": {
        "message": "包含在禁止域名内",
        "code": 1401,
    },
    "RuleInvalid": {
        "message": "规则无效",
        "code": 1402,
    },
    "GithubKeywordEmpty": {
        "message": "关键字为空",
        "code": 1501,
    },
    "Error": {
        "message": "系统异常",
        "code": 500,
    },
    "CronError": {
        "message": "Cron 表达式错误",
        "code": 1502,
    },
    "IPInvalid": {
        "message": "IP 无效",
        "code": 1503,
    },
    "IPNotFoundViaScope": {
        "message": "不在给定的资产范围中",
        "code": 1504,
    },
    "PortCustomInvalid": {
        "message": "自定义端口信息错误",
        "code": 1506,
    },
    "TaskScheduleTypeInvalid": {
        "message": "计划任务类型错误",
        "code": 1601,
    },
    "DateInvalid": {
        "message": "时间错误",
        "code": 1602,
    },
    "TaskTagInvalid": {
        "message": "任务类型错误",
        "code": 1603,
    },
    "FutureDateInvalid": {
        "message": "时间已经过去了",
        "code": 1604,
    },
    "TaskScheduleNotFound": {
        "message": "计划任务没有找到",
        "code": 1605,
    },
    "DomainSiteViaJob": {
        "message": "资产站点更新任务已存在",
        "code": 1607,
    }
}


class ErrorMsg:
    CeleryIdNotFound = error_map["CeleryIdNotFound"]
    NotFoundTask = error_map["NotFoundTask"]
    TaskIsRunning = error_map["TaskIsRunning"]
    TaskIsDone = error_map["TaskIsDone"]
    Success = error_map["Success"]
    NotLogin = error_map["NotLogin"]
    NotFoundScopeID = error_map["NotFoundScopeID"]
    NotFoundScope = error_map["NotFoundScope"]
    ExistScope = error_map["ExistScope"]
    IntervalLessThan3600 = error_map["IntervalLessThan3600"]
    DomainNotFoundViaScope = error_map["DomainNotFoundViaScope"]
    DomainViaJob = error_map["DomainViaJob"]
    DomainNotViaJob = error_map["DomainNotViaJob"]
    JobNotFound = error_map["JobNotFound"]
    DomainInvalid = error_map["DomainInvalid"]
    TargetInvalid = error_map["TargetInvalid"]
    IPInBlackIps = error_map["IPInBlackIps"]
    TaskSyncDealing = error_map["TaskSyncDealing"]
    TaskTypeIsNotDomain = error_map["TaskTypeIsNotDomain"]
    TaskTargetNotInScope = error_map["TaskTargetNotInScope"]
    DomainInScope = error_map["DomainInScope"]
    SiteInScope = error_map["SiteInScope"]
    URLInvalid = error_map["URLInvalid"]
    SiteURLNotDomain = error_map["SiteURLNotDomain"]
    SchedulerStatusNotRunning = error_map["SchedulerStatusNotRunning"]
    SchedulerStatusNotStop = error_map["SchedulerStatusNotStop"]
    DomainNotFoundNotInScope = error_map["DomainNotFoundNotInScope"]
    ResultSetIDNotFound = error_map["ResultSetIDNotFound"]
    ResultSetIsEmpty = error_map["ResultSetIsEmpty"]
    PoCTargetIsEmpty = error_map["PoCTargetIsEmpty"]
    QueryResultIsEmpty = error_map["QueryResultIsEmpty"]
    TaskTargetIsEmpty = error_map["TaskTargetIsEmpty"]
    PolicyIDNotFound = error_map["PolicyIDNotFound"]
    PolicyDataIsEmpty = error_map["PolicyDataIsEmpty"]
    RiskCruisingPoCConfigIsEmpty = error_map["RiskCruisingPoCConfigIsEmpty"]
    BruteTaskBruteConfigIsEmpty = error_map["BruteTaskBruteConfigIsEmpty"]
    FofaConnectError = error_map["FofaConnectError"]
    FofaKeyError = error_map["FofaKeyError"]
    FofaResultEmpty = error_map["FofaResultEmpty"]
    SiteIdNotFound = error_map["SiteIdNotFound"]
    SiteTagIsExist = error_map["SiteTagIsExist"]
    SiteTagNotExist = error_map["SiteTagNotExist"]
    ScopeTypeIsNotIP = error_map["ScopeTypeIsNotIP"]
    IsForbiddenDomain = error_map["IsForbiddenDomain"]
    RuleInvalid = error_map["RuleInvalid"]
    GithubKeywordEmpty = error_map["GithubKeywordEmpty"]
    Error = error_map["Error"]
    CronError = error_map["CronError"]
    IPInvalid = error_map["IPInvalid"]
    IPNotFoundViaScope = error_map["IPNotFoundViaScope"]
    PortCustomInvalid = error_map["PortCustomInvalid"]
    TaskScheduleTypeInvalid = error_map["TaskScheduleTypeInvalid"]
    DateInvalid = error_map["DateInvalid"]
    TaskTagInvalid = error_map["TaskTagInvalid"]
    FutureDateInvalid = error_map["FutureDateInvalid"]
    TaskScheduleNotFound = error_map["TaskScheduleNotFound"]
    DomainSiteViaJob = error_map["DomainSiteViaJob"]

