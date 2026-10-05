"""HTTP requester (cache + thread lock + stats + throttle + UA rotation + proxy pool)

v1.1: added raw_mode.
  raw_mode=False (default) —— payload is handed to requests for encoding, correct and general.
  raw_mode=True            —— payload is already "pre-encoded text",
                              concatenated directly as a string into query/body, with no second encoding.
                              Used by the charencode / manual %xx style strategies.

v1.2: added json_body.
  json_body=True —— --data passes JSON text; the payload is injected as a string value into
                    the field specified by --param (supports nested paths like 'a.b'), then serialized as a whole.
                    This way a payload containing quotes / spaces / parentheses does not break the JSON.
                    In this mode raw_mode has no effect (the payload must be serialized before sending).
"""
import copy
import json
import random
import threading
import time

import requests

from core.throttle import Throttle
from core.proxy_pool import ProxyPool
from utils.helpers import set_json_path
from utils.ua_pool import UAPool

requests.packages.urllib3.disable_warnings()


class Requester:
    def __init__(self, url, method="POST", position="data", param="id",
                 base_data=None, base_params=None, base_headers=None,
                 base_cookies=None, timeout=10,
                 throttle=None, ua_pool=None, proxy_pool=None,
                 retries=0, retry_delay=1.0,
                 log=None, json_body=False):
        self.url = url
        self.method = method.upper()
        self.position = position
        self.param = param
        self.base_data = base_data or {}
        self.base_params = base_params or {}
        self.base_headers = base_headers or {}
        self.base_cookies = base_cookies or {}
        self.timeout = timeout
        self.log = log

        self.throttle = throttle or Throttle()
        self.ua_pool = ua_pool
        self.proxy_pool = proxy_pool
        self.retries = retries
        self.retry_delay = retry_delay

        # v1.1
        self.raw_mode = False
        # v1.2
        self.json_body = bool(json_body)
        if self.json_body and not isinstance(self.base_data, dict):
            self.base_data = {}

        self.session = requests.Session()
        self._cache = {}
        self._lock = threading.RLock()
        self._stats = {"total": 0, "errors": 0, "time": 0.0}

    # ---------------- Build request ----------------
    def _common_headers(self, headers):
        if self.ua_pool:
            headers["User-Agent"] = self.ua_pool.get()
        if self.throttle.human_mode:
            headers.setdefault("Accept",
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
            headers.setdefault("Accept-Language", random.choice(
                ["zh-CN,zh;q=0.9", "zh-CN,zh;q=0.9,en;q=0.8", "en-US,en;q=0.9"]))
            headers.setdefault("Connection", "keep-alive")
        return headers

    @staticmethod
    def _join_kv(d, override_key, override_val):
        parts = []
        for k, v in d.items():
            if k == override_key:
                continue
            parts.append(f"{k}={v}")
        parts.append(f"{override_key}={override_val}")
        return "&".join(parts)

    def build(self, payload):
        # In JSON mode the payload must be serialized into JSON before any encoding; raw_mode has no effect on it
        if self.raw_mode and not self.json_body:
            return self._build_raw(payload)

        data = dict(self.base_data)
        params = dict(self.base_params)
        headers = dict(self.base_headers)
        cookies = dict(self.base_cookies)

        if self.position == "data":
            if self.json_body:
                obj = copy.deepcopy(self.base_data)
                set_json_path(obj, self.param, payload)
                data = json.dumps(obj, ensure_ascii=False)
                headers.setdefault("Content-Type", "application/json")
            else:
                data[self.param] = payload
        elif self.position == "params":
            params[self.param] = payload
        elif self.position == "headers":
            headers[self.param] = payload
        elif self.position == "cookies":
            cookies[self.param] = payload

        return params, data, self._common_headers(headers), cookies

    def _build_raw(self, payload):
        """payload is treated as already-encoded text, concatenated as-is, with no second encoding."""
        data = dict(self.base_data)
        params = dict(self.base_params)
        headers = dict(self.base_headers)
        cookies = dict(self.base_cookies)

        if self.position == "data":
            data = self._join_kv(data, self.param, payload)
            params = self.base_params or None
        elif self.position == "params":
            params = self._join_kv(params, self.param, payload)
            data = self.base_data or None
        elif self.position == "headers":
            headers[self.param] = payload
            params = params or None
            data = data or None
        elif self.position == "cookies":
            cookies[self.param] = payload
            params = params or None
            data = data or None

        return params, data, self._common_headers(headers), cookies

    # ---------------- Send ----------------
    def send(self, payload, use_cache=True):
        with self._lock:
            if use_cache and payload in self._cache:
                return self._cache[payload]

        params, data, headers, cookies = self.build(payload)
        proxies = self.proxy_pool.get() if self.proxy_pool else None

        result = None
        for attempt in range(self.retries + 1):
            self.throttle.wait()
            t0 = time.time()
            try:
                r = self.session.request(
                    self.method, self.url,
                    params=params, data=data,
                    headers=headers, cookies=cookies,
                    timeout=self.timeout, proxies=proxies, verify=False,
                )
                elapsed = time.time() - t0
                result = {
                    "status": r.status_code,
                    "length": len(r.text),
                    "text": r.text,
                    "time": elapsed,
                    "attempt": attempt + 1,
                }
                break
            except Exception as e:
                elapsed = time.time() - t0
                with self._lock:
                    self._stats["errors"] += 1
                if attempt < self.retries:
                    time.sleep(self.retry_delay)
                    continue
                result = {
                    "status": -1, "length": -1, "text": "",
                    "time": elapsed, "error": str(e),
                }

        with self._lock:
            self._stats["total"] += 1
            self._stats["time"] += result.get("time", 0)
            if use_cache:
                self._cache[payload] = result
        return result

    def stats(self):
        with self._lock:
            return dict(self._stats)

    def clear_cache(self):
        with self._lock:
            self._cache.clear()
