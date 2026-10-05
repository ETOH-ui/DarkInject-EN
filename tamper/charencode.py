from urllib.parse import quote


def charencode(s):
    return quote(s, safe="")