# -*- coding: utf-8 -*-
"""tamper common utilities

Background: a tamper should only act on the "SQL code" parts, and must not
corrupt string literals (database/table names, data) along with them.

But the quotes in an injection payload are inherently unbalanced, e.g. a closing one:
    -1' UNION SELECT 1,2,3 AND '1'='1
If we split by "on encountering a quote, enter a literal", then
    ' UNION SELECT 1,2,3 AND '
is treated as one literal, so UNION gets no nesting and the bypass fails.

Therefore the rule here is:
  * look forward for the matching quote;
  * if the paired span **contains whitespace**, it looks more like SQL code than a value -> treat that quote as code;
  * otherwise (e.g. 'past_paper') treat it as a real literal and keep it whole.

Values that contain spaces (rare) will be misjudged as code; this is a deliberately accepted trade-off.
"""


def _find_close(s, i, q):
    """From s[i] (the quote q), look forward for the matching quote and return its index; return -1 if not found."""
    n = len(s)
    j = i + 1
    while j < n:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == q:
            if j + 1 < n and s[j + 1] == q:   # '' doubled escape
                j += 2
                continue
            return j
        j += 1
    return -1


def _looks_like_value(span):
    """Whether the paired span looks like a "value": contains no whitespace."""
    return not any(ch.isspace() for ch in span)


def split_segments(s):
    """Split into [(is_literal, text), ...]; literal segments are kept whole."""
    out = []
    buf = []
    i, n = 0, len(s)

    def flush():
        if buf:
            out.append((False, "".join(buf)))
            buf.clear()

    while i < n:
        c = s[i]
        if c in ("'", '"'):
            j = _find_close(s, i, c)
            if j != -1 and _looks_like_value(s[i + 1:j]):
                flush()
                out.append((True, s[i:j + 1]))
                i = j + 1
                continue
            # treat as code: a single quote character
            buf.append(c)
            i += 1
        else:
            buf.append(c)
            i += 1
    flush()
    return out


def transform_outside_quotes(s, fn):
    """Apply fn only to "code" segments."""
    return "".join(t if is_lit else fn(t) for is_lit, t in split_segments(s))


def transform_inside_quotes(s, fn):
    """Apply fn only to literal segments (including the quotes)."""
    return "".join(fn(t) if is_lit else t for is_lit, t in split_segments(s))
