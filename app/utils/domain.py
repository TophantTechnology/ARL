import tld
from app.config import Config

blackdomain_list = None
blackhexie_list = None

def check_domain_black(domain):
    global blackdomain_list
    global blackhexie_list
    if blackdomain_list is None:
        with open(Config.black_domain_path) as f:
            blackdomain_list = f.readlines()

    for item in blackdomain_list:
        item = item.strip()
        if item and domain.endswith(item):
            return True

    if blackhexie_list is None:
        with open(Config.black_heixie_path) as f:
            blackhexie_list = f.readlines()


    for item in blackhexie_list:
        item = item.strip()
        _, _, subdomain = tld.parse_tld(domain, fix_protocol=True, fail_silently=True)
        if subdomain and  item and  item.strip() in subdomain:
            return True

    return False




def is_valid_domain(domain):
    from app.utils import domain_parsed
    if "." not in domain:
        return False
    if ":" in domain:
        return False
    if domain_parsed(domain):
        return True

    return False


def is_in_scope(src_domain, target_domain):
    from app.utils import get_fld

    fld1 = get_fld(src_domain)
    fld2 = get_fld(target_domain)

    if not fld1 or not fld2:
        return False

    if fld1 != fld2:
        return False

    if src_domain == target_domain:
        return True

    return src_domain.endswith("."+target_domain)


def is_in_scopes(domain, scopes):
    for target_scope in scopes:
        if is_in_scope(domain, target_scope):
            return True

    return False


def cut_first_name(domain):
    """将子域名剔除前面一节名称"""
    domain_parts, non_zero_i, _ = tld.utils.process_url(domain, fix_protocol=True, fail_silently=True)
    if not domain_parts:
        return

    if non_zero_i == 1:
        return

    item = ".".join(domain_parts[1:])
    return item
