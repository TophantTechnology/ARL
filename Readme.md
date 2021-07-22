## ARL(Asset Reconnaissance Lighthouse)资产侦察灯塔系统
[![Python 3.6](https://img.shields.io/badge/python-3.6-yellow.svg)](https://www.python.org/)
[![Docker Images](https://img.shields.io/docker/pulls/tophant/arl.svg)](https://hub.docker.com/r/tophant/arl)
[![Github Issues](https://img.shields.io/github/issues/TophantTechnology/ARL.svg)](https://github.com/TophantTechnology/ARL/issues)
[![Github Stars](https://img.shields.io/github/stars/TophantTechnology/ARL.svg)](https://github.com/TophantTechnology/ARL/stargazers)

资产灯塔，不仅仅是域名收集

### 简介

旨在快速侦察与目标关联的互联网资产，构建基础资产信息库。
协助甲方安全团队或者渗透测试人员有效侦察和检索资产，发现存在的薄弱点和攻击面。

在开始使用之前，请务必阅读并同意[免责声明](Disclaimer.md)中的条款，否则请勿下载安装使用本系统。

### 系统要求

目前暂不支持Windows。Linux和MAC建议采用Docker运行，系统配置最低2核4G。  
由于自动资产发现过程中会有大量的的发包，建议采用云服务器可以带来更好的体验。  

### Docker 启动
拉取镜像

```
docker pull tophant/arl
```

docker-compose 启动
```
git clone https://github.com/TophantTechnology/ARL
cd ARL/docker/
docker-compose up -d 
```
详细说明可以参考: [Docker 环境安装 ARL](https://github.com/TophantTechnology/ARL/wiki/Docker-%E7%8E%AF%E5%A2%83%E5%AE%89%E8%A3%85-ARL)

### 截图
登录页面，默认端口5003 (https), 默认用户名密码admin/arlpass  
![登录页面](./image/login.png)

任务页面
![任务页面](./image/task.png)

子域名页面
![子域名页面](./image/domain.png)

站点页面
![站点页面](./image/site.png)

资产监控页面
![资产监控页面](./image/monitor.png)
详细说明可以参考：[资产分组和监控功能使用说明](https://github.com/TophantTechnology/ARL/wiki/%E8%B5%84%E4%BA%A7%E5%88%86%E7%BB%84%E5%92%8C%E7%9B%91%E6%8E%A7%E5%8A%9F%E8%83%BD%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E)

策略页面
![策略配置页面](./image/policy.png)

筛选站点进行任务下发
![筛选站点进行任务下发](./image/scan.png)
详细说明可以参考： [2.3-新添加功能详细说明](https://github.com/TophantTechnology/ARL/wiki/ARL-2.3-%E6%96%B0%E6%B7%BB%E5%8A%A0%E5%8A%9F%E8%83%BD%E8%AF%A6%E7%BB%86%E8%AF%B4%E6%98%8E)

### 任务选项说明
| 编号 |      选项      |                                       说明                                        |
| --- | -------------- | -------------------------------------------------------------------------------- |
| 1    | 任务名称        | 任务名称                                                                          |
| 2    | 任务目标        | 任务目标，支持IP，IP段和域名。可一次性下发多个目标                                      |
| 3    | 域名爆破类型    | 对域名爆破字典大小, 大字典：常用2万字典大小。测试：少数几个字典，常用于测试功能是否正常        |
| 4    | 端口扫描类型    | ALL：全部端口，TOP1000：常用top 1000端口，TOP100：常用top 100端口，测试：少数几个端口 |
| 5    | 域名爆破        | 是否开启域名爆破                                                                   |
| 6    | DNS字典智能生成 | 根据已有的域名生成字典进行爆破                                                      |
| 7    | Riskiq 调用    | 利用[RiskIQ](https://community.riskiq.com/)  API进行查询域名                       |
| 8    | ARL 历史查询    | 对arl历史任务结果进行查询用于本次任务                                                |
| 9    | crt.sh 调用    | 利用 crt.sh 网站 API 进行子域名发现                                                 |
| 10    | 端口扫描        | 是否开启端口扫描，不开启站点会默认探测80,443                                         |
| 11   | 服务识别        | 是否进行服务识别，有可能会被防火墙拦截导致结果为空                                     |
| 12   | 操作系统识别    | 是否进行操作系统识别，有可能会被防火墙拦截导致结果为空                                 |
| 13   | Fofa IP查询    | 利用[Fofa](https://fofa.so/)  API进行查询域名                                      |
| 14   | SSL 证书获取    | 对端口进行SSL 证书获取                                                             |
| 15   | 站点识别        | 对站点进行指纹识别                                                                 |
| 16   | 搜索引擎调用    | 利用搜索引擎结果爬取对应的URL                                                       |
| 17   | 站点爬虫        | 利用静态爬虫对站点进行爬取对应的URL                                                  |
| 18   | 站点截图        | 对站点首页进行截图                                                                 |
| 19   | 文件泄露        | 对站点进行文件泄露检测，会被WAF拦截                                                  |


### 配置参数说明

Docker环境配置文件路径 `docker/config-docker.yaml`

|       配置        |                 说明                 |
| ----------------- | ------------------------------------ |
| CELERY.BROKER_URL | rabbitmq连接信息                      |
| MONGO             | mongo 连接信息                        |
| RISKIQ            | riskiq API 配置信息                   |
| GEOIP             | GEOIP 数据库路径信息                  |
| FOFA              | FOFA API 配置信息                     |
| ARL.AUTH          | 是否开启认证，不开启有安全风险          |
| ARL.API_KEY       | arl后端API调用key，如果设置了请注意保密 |
| ARL.BLACK_IPS     | 为了防止SSRF，屏蔽的IP地址或者IP段      |
| ARL.PORT_TOP_10     | 自定义端口，对应前端端口测试选项      |
| ARL.DOMAIN_DICT     | 域名爆破字典，对应前端大字典选项      |
| ARL.FILE_LEAK_DICT     | 文件泄漏字典      |



### 忘记密码重置

当忘记了登录密码，可以执行下面的命令，然后使用 `admin/admin123` 就可以登录了。
```
docker exec -ti arl_mongodb mongo -u admin -p admin
use arl
db.user.drop()
db.user.insert({ username: 'admin',  password: hex_md5('arlsalt!@#'+'admin123') })
```


### 源码安装

仅仅适配了 centos 7 ，且灯塔安装目录为/opt/ARL
如果在其他目录可以创建软连接，且安装了三个服务分别为`arl-web`, `arl-worker`, `arl-scheduler`

```
wget https://raw.githubusercontent.com/TophantTechnology/ARL/master/misc/setup-arl.sh
chmod +x setup-arl.sh
./setup-arl.sh
```


### Docker 环境安装

仅仅适配了 centos 7 ，且灯塔安装目录为/opt/ARL
```
wget https://raw.githubusercontent.com/TophantTechnology/ARL/master/misc/setup-docker-arl.sh
chmod +x setup-docker-arl.sh
./setup-docker-arl.sh
```

### FAQ

请访问如下链接[FAQ](https://github.com/TophantTechnology/ARL/wiki/Docker-%E7%8E%AF%E5%A2%83%E5%AE%89%E8%A3%85-ARL#faq)

### 写在最后

目前ARL仅仅只是完成了对资产的部分维度的发现和收集，自动发现过程中难免出现覆盖度不全、不精准、不合理等缺陷的地方还请反馈至我们。  

