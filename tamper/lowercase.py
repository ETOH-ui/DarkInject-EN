# -*- coding: utf-8 -*-
"""All lowercase -- bypass implementations that "only block uppercase keywords"

Some targets have a blacklist entry 'UNION' (uppercase), while SQL keywords are case-insensitive,
so lowercasing the payload passes. Only convert outside quotes, protecting database/table name case.
"""
from tamper._util import transform_outside_quotes


def lowercase(s):
    return transform_outside_quotes(s, lambda seg: seg.lower())
