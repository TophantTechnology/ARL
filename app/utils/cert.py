import json
import ssl
import OpenSSL
import socket
from datetime import datetime

socket.setdefaulttimeout(6)

def parse_certs(certs):
    result = {}
    ospj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, certs)

    subject = ospj.get_subject()
    subject_dn = "C={C}, CN={CN}".format(C=subject.C,CN=subject.CN)
    if subject.O:
        subject_dn += " ,O={O}".format(O = subject.O)

    issuer = ospj.get_issuer()
    issuser_obj = {}
    issuser_obj['country'] = issuer.C
    issuser_obj['province'] = issuer.ST
    issuser_obj['locality'] = issuer.L
    issuser_obj['organizational'] = issuer.O
    issuser_obj['organizational_unit'] = issuer.OU
    issuser_obj['common_name'] = issuer.CN
    issuser_obj['email'] = issuer.emailAddress

    issuer_dn = "C={C}, O={O}, OU={OU}, CN={CN}".format(C=issuer.CN, O=issuer.O, OU=issuer.OU, CN=issuer.CN)

    signature_algorithm = bytes.decode(ospj.get_signature_algorithm()) # 返回证书使用的签名算法
    serial_number = ospj.get_serial_number() # 证书序列号
    validity_obj = {}
    start_date = str(datetime.strptime(ospj.get_notBefore().decode("UTF-8"), '%Y%m%d%H%M%SZ'))
    end_date = str(datetime.strptime(ospj.get_notAfter().decode("UTF-8"), '%Y%m%d%H%M%SZ'))

    validity_obj['start'] = start_date
    validity_obj['end'] = end_date
    validity_obj['expired'] = ospj.has_expired()

    version = ospj.get_version() + 1


    subject_key_info = {}
    subject_key_info['key_algorithm'] = signature_algorithm
    subject_key_info['public_key'] = {}
    subject_key_info['public_key']['length'] = ospj.get_pubkey().bits()
    subject_key_info['public_key']['key'] = OpenSSL.crypto.dump_publickey(OpenSSL.crypto.FILETYPE_PEM, ospj.get_pubkey()).decode("utf-8")

    subject_obj = {}
    subject_obj['country'] =  subject.C
    subject_obj['province'] = subject.ST
    subject_obj['locality'] = subject.L
    subject_obj['organizational'] = subject.O
    subject_obj['organizational_unit'] = subject.OU
    subject_obj['common_name'] = subject.CN
    subject_obj['email'] = subject.emailAddress

    fingerprint_obj = {}
    fingerprint_obj['sha1'] = bytes.decode(ospj.digest('sha1')).replace(":", "").lower()
    fingerprint_obj['sha256'] = bytes.decode(ospj.digest('sha256')).replace(":", "").lower()
    fingerprint_obj['md5'] = bytes.decode(ospj.digest('md5')).replace(":", "").lower()

    extensions = {}
    exn_num = 0
    while exn_num < ospj.get_extension_count():
        ext_name = bytes.decode(ospj.get_extension(exn_num).get_short_name())
        ext_val = str(ospj.get_extension(exn_num))
        extensions[ext_name] = ext_val
        exn_num += 1

    result['subject_dn'] = subject_dn
    result['issuer'] = issuser_obj
    result['signature_algorithm'] = signature_algorithm
    result['serial_number'] = str(serial_number) # 转换为 str模式 MongoDB can only handle up to 8-byte ints
    result['validity'] = validity_obj
    result['issuer_dn'] = issuer_dn
    result['version'] = version
    result['extensions'] = extensions
    #这个太长了，省点
    #result['subject_key_info'] = subject_key_info
    result['subject'] = subject_obj
    result['fingerprint'] = fingerprint_obj

    return result



def get_cert(host, port):
    from . import get_logger
    logger = get_logger()
    try:

        certs = ssl.get_server_certificate((host, port))
        return parse_certs(certs)
    except Exception as e:
        logger.debug("get cert error {}:{} {}".format(host,port, e))












