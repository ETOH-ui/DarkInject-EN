#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local SQLite vulnerable lab range (for end-to-end verification of the tool's blacklist bypass capability)

Deliberately written as a "typical CTF-style" injection point:

    $id = $_GET['id'];
    // filtering
    $sql = "SELECT id, title, body FROM articles WHERE id = $id";
    $res = mysql_query($sql);   // on error, spew both the SQL and the error back out

Implemented with SQLite, requiring no external database dependency.

Usage:
    python lab/vuln_app.py --filter strip_single_i --port 8899
    python lab/vuln_app.py --filter presence_i   --port 8899

--filter choices:
    none / presence_i / presence_cs / strip_single_i / strip_single_cs / strip_recursive_i
The blacklist comes from lab/blacklist_ctf.txt (identical to the one given in the challenge).

⚠️ For local learning and tool self-testing only.
"""
import argparse
import html
import json
import os
import re
import sqlite3
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.blacklist import load_blacklist  # noqa: E402


BL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blacklist_ctf.txt")
TOKENS = load_blacklist(BL_FILE)


def ireplace(s, old, new):
    if not old:
        return s
    return re.sub(re.escape(old), new, s, flags=re.IGNORECASE)


def apply_filter(value, mode):
    """Return (filtered value, whether blocked)"""
    if mode == "none":
        return value, False
    if mode == "presence_i":
        if any(t.lower() in value.lower() for t in TOKENS):
            return "", True
        return value, False
    if mode == "presence_cs":
        if any(t in value for t in TOKENS):
            return "", True
        return value, False
    if mode in ("strip_single_i", "strip_single_cs", "strip_recursive_i"):
        case_i = mode != "strip_single_cs"
        if mode == "strip_recursive_i":
            prev = None
            while prev != value:
                prev = value
                for t in TOKENS:
                    value = ireplace(value, t, "") if case_i else value.replace(t, "")
            return value, False
        for t in TOKENS:
            value = ireplace(value, t, "") if case_i else value.replace(t, "")
        return value, False
    return value, False


def build_db():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.executescript("""
        CREATE TABLE articles (id INTEGER PRIMARY KEY, title TEXT, body TEXT);
        INSERT INTO articles VALUES (1, 'hello', 'first post');
        INSERT INTO articles VALUES (2, 'world', 'second post');
        INSERT INTO articles VALUES (3, 'sqlite', 'third post');
        CREATE TABLE secret (id INTEGER PRIMARY KEY, flag TEXT);
        INSERT INTO secret VALUES (1, 'flag{un10n_n3st1ng_w0rk5}');
    """)
    return conn


DB = build_db()
FILTER_MODE = "none"

# ---- Fault injection (only for verifying tool robustness) ----
# --flaky N: every N-th request returns a 500, and the error page is **longer than a normal page**.
# Used to reproduce the real-world case where "a sporadically anomalous backend page pollutes the baseline length of differential decisions",
# whose typical symptom is a whole run of characters in the blind injection result being read as smaller characters.
FLAKY = 0
_REQ_N = 0
_REQ_LOCK = threading.Lock()

# ---- Flat-length mode (only for verifying the tool's "content differencing" capability) ----
# --flat-len N: pads all response bodies to a fixed N bytes, so true/false lengths are **exactly identical**,
# rendering length differencing completely useless — the tool must rely on response body content differences to keep deciding.
# Used to reproduce real targets such as "uniform templates / forced 200 same-length frameworks".
FLAT_LEN = 0

FAULT_BODY = (
    "Internal Server Error\n"
    "Traceback (most recent call last):\n"
    "  File \"query.py\", line 88, in handle\n"
    "    rows = db.execute(sql)\n"
    "sqlite3.OperationalError: database table is locked\n"
) * 6

PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>CTF Lab</title></head>
<body><h3>Article Viewer</h3><pre>{body}</pre></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # silence

    def _send(self, code, body):
        data = PAGE.format(body=html.escape(str(body))).encode("utf-8")
        if FLAT_LEN:
            # pad to a fixed length: the length signal fails, leaving only content differences usable
            filler = b" " * max(0, FLAT_LEN - len(data) - 7)
            data += b"<!--" + filler + b"-->"
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        global _REQ_N
        if FLAKY:
            with _REQ_LOCK:
                _REQ_N += 1
                n = _REQ_N
            if n % FLAKY == 0:
                self._send(500, FAULT_BODY)
                return

        qs = parse_qs(urlparse(self.path).query)
        raw = (qs.get("id", ["1"])[0]) or "1"
        self._run(raw)

    def do_POST(self):
        global _REQ_N
        if FLAKY:
            with _REQ_LOCK:
                _REQ_N += 1
                n = _REQ_N
            if n % FLAKY == 0:
                self._send(500, FAULT_BODY)
                return

        length = int(self.headers.get("Content-Length") or 0)
        raw_body = self.rfile.read(length).decode("utf-8", "replace")
        ctype = (self.headers.get("Content-Type") or "").lower()

        # JSON body: {"id": ...} — for self-testing the tool's --json mode
        if "application/json" in ctype:
            try:
                obj = json.loads(raw_body)
            except Exception as e:
                self._send(400, f"bad json: {e}")
                return
            ident = obj.get("id", "1") if isinstance(obj, dict) else "1"
            if isinstance(ident, (dict, list)):
                ident = "1"
            self._run(str(ident))
            return

        # form-urlencoded body: id=...
        self._run(parse_qs(raw_body).get("id", ["1"])[0] or "1")

    # ---------------- shared query logic ----------------
    def _run(self, raw):
        """Execute the injection query and echo the result (shared by GET / POST, form / JSON)."""
        value, blocked = apply_filter(raw, FILTER_MODE)
        if blocked:
            self._send(403, "HACKER DETECTED\nblocked by blacklist")
            return

        sql = f"SELECT id, title, body FROM articles WHERE id = {value}"
        try:
            cur = DB.execute(sql)
            rows = cur.fetchall()
        except Exception as e:
            # typical "debug leakage": echo the SQL together with the error
            self._send(200, f"SQL: {sql}\nERROR: {e}")
            return

        lines = [f"SQL: {sql}"]
        for r in rows:
            lines.append(" | ".join("" if v is None else str(v) for v in r))
        self._send(200, "\n".join(lines))


def main():
    global FILTER_MODE, FLAKY, FLAT_LEN
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8899)
    ap.add_argument("--filter", default="none",
                    choices=["none", "presence_i", "presence_cs",
                             "strip_single_i", "strip_single_cs", "strip_recursive_i"])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--flaky", type=int, default=0,
                    help="Inject a 500 long error page once every N requests (0=off), for verifying tool robustness")
    ap.add_argument("--flat-len", type=int, default=0,
                    help="Pad all response bodies to a fixed N bytes (length signal fails; for verifying content differencing; 0=off)")
    args = ap.parse_args()
    FILTER_MODE = args.filter
    FLAKY = args.flaky
    FLAT_LEN = args.flat_len

    print(f"[lab] http://{args.host}:{args.port}/  filter={FILTER_MODE}"
          + (f"  flaky=500 once every {FLAKY} requests" if FLAKY else "")
          + (f"  flat-len={FLAT_LEN}B (all lengths identical)" if FLAT_LEN else ""))
    print(f"[lab] blacklist tokens: {len(TOKENS)}")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
