# -*- coding: utf-8 -*-
"""DBMS dialect abstract base class

v1.1: gives multiple spellings (templates) for the same semantics; the technique rotates them at probe time.
Templates use {sql}/{pos}/{len} placeholders so they can be reused with different parameters.
"""
import re  # noqa: F401  (keeps the import habit consistent with older versions)


class BaseDialect:
    name = "base"

    def version_expr(self): raise NotImplementedError
    def database_expr(self): raise NotImplementedError
    def current_user_expr(self): raise NotImplementedError
    def is_dba_expr(self): raise NotImplementedError

    def tables_query(self, db_name, idx): raise NotImplementedError
    def columns_query(self, table_name, db_name, idx): raise NotImplementedError
    def column_types_query(self, table_name, db_name, idx): raise NotImplementedError
    def data_query(self, table_name, column, idx): raise NotImplementedError

    # ---------------- Expression templates (source of variants) ----------------
    # Note that {sql} must be wrapped in parentheses: the extracted expression is often a scalar subquery
    # (e.g. SELECT name FROM ... LIMIT 0,1), and writing LENGTH(SELECT ...) is a syntax error.
    def length_templates(self):
        return ["LENGTH(({sql}))"]

    def substr_templates(self):
        return ["SUBSTR(({sql}),{pos},{len})"]

    def ascii_templates(self):
        return ["ASCII(({sql}))"]

    # ---------------- Ready-made expressions (compatible with old callers) ----------------
    def length_expr(self, sql): return self.length_templates()[0].format(sql=sql)
    def substr_expr(self, sql, pos, length):
        return self.substr_templates()[0].format(sql=sql, pos=pos, len=length)
    def ascii_expr(self, sql): return self.ascii_templates()[0].format(sql=sql)

    def concat_templates(self):
        """String concatenation spellings (used by UNION/error injection reflecting markers)."""
        return ["CONCAT({a},{b},{c})"]

    # ---------------- String equality comparison (for whole-string verification after extraction) ----------------
    def hex_to_str(self, hexstr):
        """Write a hex string as a literal that "can be compared directly against a string".

        Used for the whole-string verification `((expr)=<here>)`.
        Note that `0x..` is treated as a binary string **only by MySQL** --
        in SQLite it is an **integer**, and PG/Oracle do not recognize it,
        so other DBMSes must each override this, otherwise the check is constantly false (a false "verification inconsistent",
        and worse, it triggers a full re-extraction for nothing).
        MySQL's `(varchar) = 0x..` compares as binary, which distinguishes case exactly.
        """
        return f"0x{hexstr}"

    def length_exprs(self, sql):
        return [t.format(sql=sql) for t in self.length_templates()]

    def substr_exprs(self, sql, pos, length):
        return [t.format(sql=sql, pos=pos, len=length) for t in self.substr_templates()]

    def ascii_exprs(self, sql):
        return [t.format(sql=sql) for t in self.ascii_templates()]

    # ---------------- Delay / error ----------------
    def sleep_expr(self, seconds): raise NotImplementedError

    def sleep_expr_variants(self, seconds):
        return [self.sleep_expr(seconds)]

    def error_payloads(self, inner_sql): raise NotImplementedError
    def error_fingerprints(self): return []
    def error_keywords(self): return []
    def boolean_fingerprints(self): return []
    def known_expr(self): return "1"
    def file_read_expr(self, path): return None
    def file_write_expr(self, path, content): return None
