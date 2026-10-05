# -*- coding: utf-8 -*-
"""Logic/function respelling -- shrink the keyword footprint

Replace common spellings with equivalent forms that use fewer keywords:
    AND   -> &&
    OR    -> ||
    =     -> LIKE
    >     -> NOT BETWEEN 0 AND
    SUBSTR( -> MID(
    ASCII(  -> ORD(
    SUBSTRING( -> MID(
    CHAR_LENGTH( -> LENGTH(

Note: && / || are MySQL syntax; SQLite/PG do not necessarily support them.
As a "candidate strategy" they are tested live by engine, and a failure moves
on to the next. Only replace outside quotes.
"""
import re

from tamper._util import transform_outside_quotes

_RULES = [
    (re.compile(r"(?<![A-Za-z0-9_])AND(?![A-Za-z0-9_])", re.IGNORECASE), "&&"),
    (re.compile(r"(?<![A-Za-z0-9_])OR(?![A-Za-z0-9_])", re.IGNORECASE), "||"),
    (re.compile(r"(?<![<>=!])>(?!=)", re.IGNORECASE), " NOT BETWEEN 0 AND "),
    (re.compile(r"SUBSTR\(", re.IGNORECASE), "MID("),
    (re.compile(r"SUBSTRING\(", re.IGNORECASE), "MID("),
    (re.compile(r"ASCII\(", re.IGNORECASE), "ORD("),
    (re.compile(r"CHAR_LENGTH\(", re.IGNORECASE), "LENGTH("),
]


def logic_alt(s):
    def f(seg):
        for pat, rep in _RULES:
            seg = pat.sub(rep, seg)
        return seg
    return transform_outside_quotes(s, f)
