# syntax=docker/dockerfile:1
FROM ubuntu:20.04 AS builder
ENV DEBIAN_FRONTEND noninteractive
WORKDIR /opt/
RUN set -x;\
    apt-get update \
    && apt-get install -y g++ make wget  libssl-dev zlib1g-dev git \
    && git clone https://github.com/blechschmidt/massdns.git \
    && cd /opt/massdns \
    && make \
    && /opt/massdns/bin/massdns --version \
    && cd /opt/ \
    && wget https://nmap.org/ncrack/dist/ncrack-0.7.tar.gz --no-check-certificate \
    && tar -xzf ncrack-0.7.tar.gz \
    && cd ncrack-0.7 \
    && ./configure \
    && make \
    && /opt/ncrack-0.7/ncrack -V



FROM ubuntu:20.04
ENV DEBIAN_FRONTEND noninteractive
ENV LANG en_US.UTF-8

WORKDIR /code

RUN set -x;\
    apt-get update \
    && apt-get install -y python3.8 python3-pip curl nginx nmap wget unzip \
    && ln -s /usr/bin/python3.8 /usr/bin/python3.6 \
    && useradd -s /bin/false nginx \
    && nmap -v

COPY app/ app/
COPY test/ test/
COPY --from=builder /opt/ncrack-0.7/ncrack /usr/local/bin/ncrack
COPY --from=builder /opt/ncrack-0.7/ncrack-services /usr/local/share/ncrack/ncrack-services
COPY --from=builder /opt/massdns/bin/massdns app/tools/massdns
COPY docker/frontend/ frontend/
COPY docker/nginx.conf  /etc/nginx/nginx.conf

## 复制生成ssl证书文件
COPY docker/worker/gen_crt.sh /usr/bin/gen_crt.sh
## 复制 wait-for-it
COPY docker/worker/wait-for-it.sh /usr/bin/wait-for-it.sh

## 复制npoc 并安装
COPY docker/ARL-NPoC/ /opt/ARL-NPoC/
WORKDIR /opt/ARL-NPoC/
RUN pip3 install -e .

WORKDIR /code
RUN curl https://ssl-config.mozilla.org/ffdhe2048.txt -o /etc/ssl/certs/dhparam.pem
COPY requirements.txt requirements.txt
COPY docker/GeoLite2/ /data/GeoLite2/
RUN pip3 install -r requirements.txt


## 安装 NPoC 的依赖
WORKDIR /opt/ARL-NPoC/
RUN pip3 install -r requirements.txt

## 安装nuclei
RUN wget https://github.com/projectdiscovery/nuclei/releases/download/v2.9.4/nuclei_2.9.4_linux_arm64.zip
RUN unzip nuclei_2.9.4_linux_arm64.zip && mv nuclei /usr/bin/ && rm -f nuclei_2.9.4_linux_arm64.zip
RUN nuclei

## 切换工作目录
WORKDIR /code

## 自测一下
RUN cp app/config.yaml.example app/config.yaml
RUN env FLASK_APP=app.main:arl_app python3.6 -m flask routes
RUN python3 -m app.celerytask
