import os
import re
import tld
import subprocess
import shlex
from collections import Counter
from app.config import Config
from app import utils
logger = utils.get_logger()
NUM_COUNT = 4

class DnsGen():
    def __init__(self, subdomains, words, base_domain = None):
        self.subdomains = subdomains
        self.base_domain = base_domain
        self.words = words

    def partiate_domain(self, domain):
        '''
        Split domain base on subdomain levels.
        TLD is taken as one part, regardless of its levels (.co.uk, .com, ...)
        '''

        # test.1.foo.example.com -> [test, 1, foo, example.com]
        # test.2.foo.example.com.cn -> [test, 2, foo, example.com.cn]
        # test.example.co.uk -> [test, example.co.uk]
        if self.base_domain:
            subdomain = re.sub(re.escape("." + self.base_domain) + "$", '', domain)
            return subdomain.split(".") + [self.base_domain]

        ext = tld.get_tld(domain.lower(), fail_silently=True, as_object=True, fix_protocol=True)
        base_domain = "{}.{}".format(ext.domain, ext.suffix)

        parts = (ext.subdomain.split('.') + [base_domain])

        return [p for p in parts if p]

    def insert_word_every_index(self, parts):
        '''
        Create new subdomain levels by inserting the words between existing levels
        '''

        # test.1.foo.example.com -> WORD.test.1.foo.example.com, test.WORD.1.foo.example.com,
        #                           test.1.WORD.foo.example.com, test.1.foo.WORD.example.com, ...

        domains = []

        for w in self.words:
            for i in range(len(parts)):
                tmp_parts = parts[:-1]
                tmp_parts.insert(i, w)
                domains.append('{}.{}'.format('.'.join(tmp_parts), parts[-1]))

        return domains

    def insert_num_every_index(self, parts):
        '''
        Create new subdomain levels by inserting the numbers between existing levels
        '''

        # foo.test.example.com ->   foo1.test.example.com, foo.test1.example.com,
        #                            ...

        domains = []

        for num in range(NUM_COUNT):
            for i in range(len(parts[:-1])):
                if num == 0:
                    continue
                # single digit
                tmp_parts = parts[:-1]
                tmp_parts[i] = '{}{}'.format(tmp_parts[i], num)
                domains.append('{}.{}'.format('.'.join(tmp_parts), '.'.join(parts[-1:])))

        return domains


    def prepend_word_every_index(self, parts):
        '''
        On every subdomain level, prepend existing content with `WORD` and `WORD-`
        '''

        # test.1.foo.example.com -> WORDtest.1.foo.example.com, test.WORD1.foo.example.com,
        #                           test.1.WORDfoo.example.com, WORD-test.1.foo.example.com,
        #                           test.WORD-1.foo.example.com, test.1.WORD-foo.example.com, ...

        domains = []

        for w in self.words:
            for i in range(len(parts[:-1])):
                # prepend normal
                tmp_parts = parts[:-1]
                tmp_parts[i] = '{}{}'.format(w, tmp_parts[i])
                domains.append('{}.{}'.format('.'.join(tmp_parts), parts[-1]))

                # prepend with dash
                tmp_parts = parts[:-1]
                tmp_parts[i] = '{}-{}'.format(w, tmp_parts[i])
                domains.append('{}.{}'.format('.'.join(tmp_parts), parts[-1]))

        return domains


    def append_word_every_index(self, parts):
        '''
        On every subdomain level, append existing content with `WORD` and `WORD-`
        '''

        # test.1.foo.example.com -> testWORD.1.foo.example.com, test.1WORD.foo.example.com,
        #                           test.1.fooWORD.example.com, test-WORD.1.foo.example.com,
        #                           test.1-WORD.foo.example.com, test.1.foo-WORD.example.com, ...

        domains = []

        for w in self.words:
            for i in range(len(parts[:-1])):
                # append normal
                tmp_parts = parts[:-1]
                tmp_parts[i] = '{}{}'.format(tmp_parts[i], w)
                domains.append('{}.{}'.format('.'.join(tmp_parts), '.'.join(parts[-1:])))

                # append with dash
                tmp_parts = parts[:-1]
                tmp_parts[i] = '{}-{}'.format(tmp_parts[i], w)
                domains.append('{}.{}'.format('.'.join(tmp_parts), '.'.join(parts[-1:])))

        return domains

    def replace_word_with_word(self, parts):
        '''
        If word longer than 3 is found in existing subdomain, replace it with other words from the dictionary
        '''

        # WORD1.1.foo.example.com -> WORD2.1.foo.example.com, WORD3.1.foo.example.com,
        #                            WORD4.1.foo.example.com, ...

        domains = []

        for w in self.words:
            if len(w) <= 3:
                continue

            if w in '.'.join(parts[:-1]):
                for w_alt in self.words:
                    if w == w_alt:
                        continue

                    domains.append('{}.{}'.format('.'.join(parts[:-1]).replace(w, w_alt), '.'.join(parts[-1:])))

        return domains

    def run(self):
        for domain in set(self.subdomains):
            parts = self.partiate_domain(domain)
            permutations = []
            permutations += self.insert_word_every_index(parts)
            permutations += self.insert_num_every_index(parts)
            permutations += self.prepend_word_every_index(parts)
            permutations += self.append_word_every_index(parts)
            permutations += self.replace_word_with_word(parts)

            for perm in permutations:
                yield perm


class AltDNS:
    def __init__(self, subdomains, base_domain = None, words = None, massdns_bin = None,
                 dnsserver = None, tmp_dir = None):
        self.subdomains = subdomains
        self.base_domain = base_domain
        self.words = words
        self.tmp_dir = tmp_dir
        self.dnsserver = dnsserver
        self.dnsgen_output_path = os.path.join(tmp_dir,
                                               "dnsgen_{}".format(utils.random_choices()))

        self.massdns_output_path = os.path.join(tmp_dir,
                                               "massdns_{}".format(utils.random_choices()))
        self.massdns_bin = massdns_bin

    def dnsgen(self):
        genresult = DnsGen(set(self.subdomains), self.words,
                           base_domain=self.base_domain).run()

        with open(self.dnsgen_output_path, "w") as f:
            for domain in genresult:
                f.write(domain + "\n")

        return self.dnsgen_output_path

    def massdns(self):
        command = [self.massdns_bin, "-q",
                   "-r {}".format(self.dnsserver),
                   "-o S",
                   "-w {}".format(self.massdns_output_path),
                   "-s {}".format(Config.ALT_DNS_CONCURRENT),
                   self.dnsgen_output_path,
                   "--root"
                   ]

        logger.info(" ".join(command))
        utils.exec_system(command)

        return self.massdns_output_path

    def parse_massdns_output(self):
        output = []
        lines = utils.load_file(self.massdns_output_path)
        for line in lines:
            data = line.split(" ")
            if len(data) != 3:
                continue
            domain, type, record = data
            item = {
                "domain": domain.strip("."),
                "type": type,
                "record": record.strip()
            }
            output.append(item)

        return output

    def run(self):
        output = []
        try:
            self.dnsgen()
            self.massdns()
            output =  self.parse_massdns_output()
            self._delete_file()
        except Exception as e:
            logger.exception(e)

        return output

    def _delete_file(self):
        try:
            os.unlink(self.dnsgen_output_path)
            os.unlink(self.massdns_output_path)
        except Exception as e:
            logger.warning(e)


'''
[{
	'domain': 'account.tophant.com',
	'type': 'A',
	'record': '182.254.150.199'
}]
'''
def altdns(subdomains, base_domain = None, words = None):
    if len(subdomains) == 0:
        return []

    a = AltDNS(subdomains, base_domain,
               words = words, massdns_bin= Config.MASSDNS_BIN,
               dnsserver=Config.DNS_SERVER, tmp_dir=Config.TMP_PATH)
    raw_domains_info = a.run()

    '''解决泛解析的问题'''
    domains_info = []
    records = [x['record'] for x in raw_domains_info]
    records_count = Counter(records)
    for info in raw_domains_info:
        if records_count[info['record']] >= 15:
            continue
        domains_info.append(info)

    return domains_info




