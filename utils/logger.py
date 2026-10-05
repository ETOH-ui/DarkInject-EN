"""Simple logging"""


class Logger:
    def __init__(self, level=1):
        self.level = level

    def info(self, msg):
        if self.level >= 1:
            print(f"[*] {msg}")

    def ok(self, msg):
        if self.level >= 1:
            print(f"[+] {msg}")

    def warn(self, msg):
        if self.level >= 1:
            print(f"[!] {msg}")

    def error(self, msg):
        print(f"[-] {msg}")

    def debug(self, msg):
        if self.level >= 2:
            print(f"[D] {msg}")