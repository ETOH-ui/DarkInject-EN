# -*- coding: utf-8 -*-
"""Whitespace replacement -- replace spaces with real control characters

Key point: this must output **real characters** (\\t / \\n / \\r / \\f), not "%09".
Because requests URL-encodes the parameter value once more, if you stuff "%09"
in directly, the server receives "%2509", and MySQL sees the literal "%09" rather
than whitespace -> syntax error. (The original space2mysqlblank fell into this trap.)

Only replace outside quotes, to avoid corrupting the spaces inside string literals.
"""
import random

from tamper._util import transform_outside_quotes

# Whitespace characters recognized by MySQL
BLANKS = ["\t", "\n", "\r", "\f", "\t\t", " \t", "\n\n"]


def space_alt(s):
    def f(seg):
        return "".join(random.choice(BLANKS) if c == " " else c for c in seg)
    return transform_outside_quotes(s, f)
