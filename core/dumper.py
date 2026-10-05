"""Unified database traversal API"""
from collections import Counter


class Dumper:
    def __init__(self, engine, votes=2):
        """
        engine: Engine instance
        votes:  number of votes when extracting key fields (database/table/column names); >=2 effectively avoids false positives under concurrency
        """
        self.eng = engine
        self.votes = votes

    # ---------------- Safe extraction of key fields ----------------
    def _safe_extract(self, sql_expr, votes=None):
        """Extract the same field multiple times and take the majority result to avoid false positives under concurrency"""
        n = self.votes if votes is None else votes
        if n <= 1:
            return self.eng.extract(sql_expr)

        results = []
        for _ in range(n):
            v = self.eng.extract(sql_expr)
            if v:
                results.append(v)
        if not results:
            return ""
        # Take the most frequent
        return Counter(results).most_common(1)[0][0]

    # ---------------- Metadata ----------------
    def get_database(self):
        return self._safe_extract(self.eng.dialect.database_expr())

    def get_version(self):
        return self.eng.extract(self.eng.dialect.version_expr())

    def get_current_user(self):
        return self.eng.extract(self.eng.dialect.current_user_expr())

    # ---------------- Structure traversal ----------------
    def get_tables(self, db_name, max_items=500):
        tables, idx = [], 0
        while idx < max_items:
            q = self.eng.dialect.tables_query(db_name, idx)
            v = self._safe_extract(q)
            if not v:
                break
            tables.append(v)
            idx += 1
        return tables

    def get_columns(self, db_name, table_name, max_items=500):
        cols, idx = [], 0
        while idx < max_items:
            q = self.eng.dialect.columns_query(table_name, db_name, idx)
            v = self._safe_extract(q)
            if not v:
                break
            cols.append(v)
            idx += 1
        return cols

    def get_column_types(self, db_name, table_name, max_items=500):
        types, idx = [], 0
        try:
            while idx < max_items:
                q = self.eng.dialect.column_types_query(table_name, db_name, idx)
                v = self.eng.extract(q)
                if not v:
                    break
                types.append(v.upper())
                idx += 1
        except Exception:
            pass
        return types

    # ---------------- Data extraction ----------------
    def get_rows(self, table_name, columns, max_rows=3):
        rows = []
        for i in range(max_rows):
            row = []
            for col in columns:
                q = self.eng.dialect.data_query(table_name, col, i)
                try:
                    row.append(self.eng.extract(q))
                except Exception:
                    row.append("(NULL)")
            if all(v in ("", "(NULL)") for v in row):
                break
            rows.append(tuple(row))
        return rows