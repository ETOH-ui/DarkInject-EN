# -*- coding: utf-8 -*-
"""Convert string literals to hex -- dodge quote and keyword scanning

    'abc'  ->  0x616263

Benefits:
  * no longer relies on the ' quote (many WAFs ban quotes separately)
  * the literal content (table/column names) is no longer exposed to keyword filtering
Notes:
  * MySQL semantics (0x.. as a binary string); SQLite treats it as an integer, so it is only a candidate strategy
  * only convert literals that are "pure ASCII with no special characters", avoiding messing up expressions like 0x7e
"""
import re

from tamper._util import split_segments

_LIT = re.compile(r"^(['\"])([ -~]*)\1$")


def _hexify(lit):
    m = _LIT.match(lit)
    if not m:
        return lit
    body = m.group(2)
    # Don't convert an empty string / one with quote escapes; leave as-is
    if body == "" or "\\" in body:
        return lit
    return "0x" + body.encode("utf-8", "surrogateescape").hex()


def hex_string(s):
    return "".join(_hexify(seg) if is_q else seg for is_q, seg in split_segments(s))
