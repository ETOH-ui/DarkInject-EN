"""Request throttle: fixed delay / jitter / QPS limit / human-like mode"""
import random
import threading
import time


class Throttle:
    def __init__(self, delay=0.0, jitter=0.0, qps=0.0, human_mode=False):
        self.delay = float(delay)
        self.jitter = float(jitter)
        self.qps = float(qps)
        self.human_mode = human_mode

        self._lock = threading.RLock()
        self._req_window = []

    def wait(self):
        waited = 0.0

        if self.qps > 0:
            waited += self._enforce_qps()

        if self.human_mode:
            s = random.uniform(0.8, 2.5)
            time.sleep(s)
            waited += s

        if self.delay > 0 or self.jitter > 0:
            d = self.delay
            if self.jitter > 0:
                d += random.uniform(-self.jitter, self.jitter)
            d = max(0.0, d)
            if d > 0:
                time.sleep(d)
                waited += d

        return waited

    def _enforce_qps(self):
        with self._lock:
            now = time.time()
            self._req_window = [t for t in self._req_window if now - t < 1.0]

            sleep_time = 0.0
            if len(self._req_window) >= self.qps:
                wait_until = self._req_window[0] + 1.0
                sleep_time = max(0.0, wait_until - now)
                time.sleep(sleep_time)
                now = time.time()
                self._req_window = [t for t in self._req_window if now - t < 1.0]

            self._req_window.append(now)
            return sleep_time