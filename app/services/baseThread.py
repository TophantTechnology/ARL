import threading
import collections
import time
import requests.exceptions
from lxml import etree
from app import utils
from app.modules import DomainInfo
logger = utils.get_logger()



class BaseThread(object):
    def __init__(self, targets, concurrency=6):
        self.concurrency = concurrency
        self.semaphore = threading.Semaphore(concurrency)
        self.targets = targets

    def work(self, site):
        raise NotImplementedError()

    def _work(self, url):
        try:
            self.work(url)
        except requests.exceptions.RequestException as e:
            pass

        except etree.Error as e:
            pass

        except Exception as e:
            logger.warning("error on {}".format(url))
            logger.exception(e)

        self.semaphore.release()

    def _run(self):
        deque = collections.deque(maxlen=2000)
        cnt = 0

        for target in self.targets:
            if isinstance(target, str):
                target = target.strip()

            cnt += 1
            logger.debug("[{}/{}] work on {}".format(cnt, len(self.targets), target))

            if not target:
                continue

            self.semaphore.acquire()
            t1 = threading.Thread(target=self._work, args=(target,))
            t1.start()

            deque.append(t1)

        for t in list(deque):
            while t.is_alive():
                time.sleep(0.2)



