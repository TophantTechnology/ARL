#!/bin/bash

function start() {
    systemctl start mongod
    systemctl start rabbitmq-server
    systemctl start arl-web
    systemctl start arl-worker
    systemctl start arl-worker-github
    systemctl start arl-scheduler
    systemctl start nginx
}

function stop() {
    systemctl stop arl-web
    systemctl stop arl-worker
    systemctl stop arl-worker-github
    systemctl stop arl-scheduler
    systemctl stop nginx
    systemctl stop mongod
    systemctl stop rabbitmq-server
}


function status() {
    systemctl status arl-web
    systemctl status arl-worker
    systemctl status arl-worker-github
    systemctl status arl-scheduler
    systemctl status nginx
    systemctl status mongod
    systemctl status rabbitmq-server
}

function disable() {
    systemctl disable mongod
    systemctl disable rabbitmq-server
    systemctl disable arl-web
    systemctl disable arl-worker
    systemctl disable arl-worker-github
    systemctl disable arl-scheduler
    systemctl disable nginx
}

function enable() {
    systemctl enable mongod
    systemctl enable rabbitmq-server
    systemctl enable arl-web
    systemctl enable arl-worker
    systemctl enable arl-worker-github
    systemctl enable arl-scheduler
    systemctl enable nginx
}

function showLog() {
    echo "------ nginx server log ------"
    journalctl -n 15 --no-pager -u nginx
    echo "------ mongod server log ------"
    journalctl -n 15 --no-pager -u mongod
    echo "------ rabbitmq-server server log ------"
    journalctl -n 15 --no-pager -u rabbitmq-server
    echo "------ arl-scheduler server log ------"
    journalctl -n 15 --no-pager -u arl-scheduler
    echo "------ arl-web server log ------"
    journalctl -n 15 --no-pager -u arl-web
    echo "------ arl-worker server log ------"
    journalctl -n 15 --no-pager -u arl-worker
    echo "------ arl-worker github server log ------"
    journalctl -n 15 --no-pager -u arl-worker-github
}

function help() {
    echo "ARL 服务管理"
    echo "Usage: manage.sh [ stop | start | status | restart | disable | enable | log ]"
}

function restart() {
    stop
    start
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    disable)
        disable
        ;;
    enable)
        enable
        ;;
    log)
        showLog
        ;;
    help)
        help
        ;;
    *)
        help
        ;;
esac
exit 0