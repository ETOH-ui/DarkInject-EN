"""Proxy pool: load from file / command line, support round-robin / random"""
import itertools
import random
import threading


class ProxyPool:
    def __init__(self, proxies=None, rotate="round-robin"):
        self.proxies = list(proxies or [])
        self.rotate = rotate
        self._lock = threading.RLock()
        self._cycle = itertools.cycle(self.proxies) if self.proxies else None

    @classmethod
    def from_file(cls, path, rotate="round-robin"):
        proxies = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    proxies.append(line)
        return cls(proxies, rotate)

    def get(self):
        if not self.proxies:
            return None
        with self._lock:
            if self.rotate == "random":
                p = random.choice(self.proxies)
            elif self.rotate == "single":
                p = self.proxies[0]
            else:
                p = next(self._cycle)
        return {"http": p, "https": p}

    def size(self):
        return len(self.proxies)