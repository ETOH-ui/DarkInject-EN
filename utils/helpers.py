"""Common utility functions"""


def parse_kv(s):
    """Parse a string of the form 'a=1&b=2' into a dict"""
    d = {}
    for pair in (s or "").split("&"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            d[k] = v
    return d


def parse_cookies(s):
    """Parse a Cookie string of the form 'a=1; b=2' into a dict"""
    d = {}
    for pair in (s or "").split(";"):
        pair = pair.strip()
        if "=" in pair:
            k, v = pair.split("=", 1)
            d[k] = v
    return d


def parse_headers(items):
    """Parse ['Header: value', ...] into a dict"""
    h = {}
    for item in items or []:
        if ":" in item:
            k, v = item.split(":", 1)
            h[k.strip()] = v.strip()
    return h


def set_json_path(obj, path, value):
    """Write value into a nested dict following an 'a.b.c' path (missing intermediate layers are auto-filled as dicts).

    For JSON body injection: writing --param 'user.id' injects into {"user": {"id": ...}}.
    """
    keys = [k for k in (path or "").split(".") if k]
    if not keys:
        return obj
    cur = obj
    for k in keys[:-1]:
        nxt = cur.get(k)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[k] = nxt
        cur = nxt
    cur[keys[-1]] = value
    return obj


def normalize_space(s):
    """Normalize notations like %0a / \\t into actual characters"""
    if s is None:
        return " "
    mapping = {
        "%0a": "\n", "%0A": "\n",
        "%09": "\t",
        "%0b": "\v", "%0B": "\v",
        "%0c": "\f", "%0C": "\f",
        "%0d": "\r", "%0D": "\r",
        "%20": " ",
        "\\n": "\n", "\\t": "\t", "\\r": "\r",
    }
    return mapping.get(s, s)


def format_value(v):
    """Format a single value for SQL-style display"""
    if v is None:
        return "NULL"
    s = str(v)
    if s.isdigit():
        return s
    return f"'{s}'"


def format_row(row):
    """Format a row of data into an SQL-style string"""
    return "(" + ", ".join(format_value(v) for v in row) + ")"