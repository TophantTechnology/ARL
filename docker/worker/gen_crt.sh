cd /etc/ssl/certs/

if [ ! -f arl_web.csr ]; then
  openssl req -new -newkey rsa:2048 -sha256 -nodes -out arl_web.csr -keyout \
arl_web.key -subj "/C=CN/ST=Shanghai/L=Shanghai/O=Example Inc./OU=Web Security/CN=127.0.0.1"
fi

if [ ! -f arl_web.crt ]; then
  openssl x509 -req -days 3650 -in arl_web.csr -signkey arl_web.key -out arl_web.crt
fi
