# -*- coding: utf-8 -*-
"""Whitespace replacement (historical name kept)

The old implementation output percent-strings like "%09", which requests re-encodes into %2509 and is useless.
Here it reuses space_alt (which outputs real control characters): correct behavior, compatible name.
"""
from tamper.space_alt import space_alt


def space2mysqlblank(s):
    return space_alt(s)
