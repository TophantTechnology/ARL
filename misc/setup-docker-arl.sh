echo "install dependencies ..."
yum install epel-release -y
yum install python36 git htop vim yum-utils -y

if [ ! -f /usr/local/bin/pip3.6 ]; then
  echo "install  pip3.6"
  python3.6 -m ensurepip --default-pip
  pip3.6 install --upgrade pip
fi

pip3.6 install docker-compose

echo "remove docker ..."
yum remove docker \
                  docker-client \
                  docker-client-latest \
                  docker-common \
                  docker-latest \
                  docker-latest-logrotate \
                  docker-logrotate \
                  docker-engine

if [ ! -f /etc/yum.repos.d/docker-ce.repo ]; then
  echo "add docker repo ..."
  yum-config-manager \
      --add-repo \
      https://download.docker.com/linux/centos/docker-ce.repo
fi

echo "install docker-ce ..."
yum install docker-ce docker-ce-cli containerd.io -y

echo "start docker service ..."
systemctl enable docker
systemctl start docker


cd /opt/
if [ ! -d ARL ]; then
  echo "git clone ARL proj"
  git clone https://github.com/TophantTechnology/ARL
fi
cd ARL/docker

echo "pull images ..."
docker-compose pull
echo "start arl ..."
docker volume create arl_db
docker-compose up -d
echo "done ."