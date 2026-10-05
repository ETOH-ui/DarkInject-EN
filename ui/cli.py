"""Command-line argument parsing"""
import argparse

from ui import banner


def parse_args():
    p = argparse.ArgumentParser(
        description=(
            "DarkInject v1.2.0 - universal SQL injection toolkit\n"
            "\n"
            "[!] Disclaimer: attacking a target with this tool without prior mutual consent is illegal.\n"
            "    Users are responsible for complying with all applicable laws; the developers assume no liability."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  Quick start:
    python main.py -u URL --data "id=1" --param id
  Known database name (skip blind injection):
    python main.py -u URL --data "id=1" --db past_paper --workers 4
  Boolean blind injection + charset optimization:
    python main.py -u URL --data "id=1" --technique B --charset flag --workers 4
  UNION injection (specify column count manually):
    python main.py -u URL --data "id=1" --technique U --cols 2 --visible-col 2
  Stealth mode (a must-read for SRC bug hunting):
    python main.py -u URL --data "id=1" --stealth --proxy-file proxies.txt

[!] Disclaimer: attacking a target with this tool without prior mutual consent is illegal.
    Users are responsible for complying with all applicable laws; the developers assume no liability.
        """,
    )

    # ---- Basic requests ----
    p.add_argument("-u", "--url", required=True, help="Target URL")
    p.add_argument("--method", default="POST", help="Request method GET/POST, default POST")
    p.add_argument("--position", default="data",
                   choices=["data", "params", "headers", "cookies"],
                   help="Injection position: data / params / headers / cookies")
    p.add_argument("--param", default=None, action="append",
                   help="Injection parameter name, default id; may be passed multiple times or comma-separated (multiple parameters probed in turn)")
    p.add_argument("--data", default="",
                   help="Base POST data, e.g. 'id=1&name=x'; pass JSON text when using --json")
    p.add_argument("--json", dest="json_body", action="store_true",
                   help="Send the body as JSON: the payload is injected into the --param field (supports a.b nested paths)")
    p.add_argument("--params", default="", help="Base URL parameters, e.g. 'page=1'")
    p.add_argument("--header", action="append", default=[],
                   help="Custom Header, may be used multiple times")
    p.add_argument("--cookie", default="", help="Cookie string")
    p.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds")
    p.add_argument("--space", default=" ", help="Space substitution notation, e.g. %%0a / %%09")
    p.add_argument("--max-rows", type=int, default=3, help="Maximum rows to fetch per table")
    p.add_argument("--verbose", type=int, default=1, choices=[0, 1, 2])

    # ---- Injection ----
    p.add_argument("--technique", default="auto",
                   choices=["auto", "B", "T", "E", "U"],
                   help="Injection technique: B=boolean T=time E=error U=union")
    p.add_argument("--dbms", default="auto",
                   choices=["auto", "mysql", "mssql", "oracle",
                            "postgresql", "sqlite"])
    p.add_argument("--db", default=None,
                   help="Specify the database name directly (skip blind injection; recommended when the database name is known)")
    p.add_argument("--cols", type=int, default=None,
                   help="Manually specify the column count for the UNION query (skip detection)")
    p.add_argument("--visible-col", type=int, default=None,
                   help="Manually specify the reflected-output column number for UNION (1-based)")
    p.add_argument("--charset", default="full",
                   help="Blind injection charset: full/flag/hex/hexu/alnum/digit/lower/sql, or a custom string")
    p.add_argument("--tamper", default="", help="Tamper chain, comma-separated")
    p.add_argument("--blacklist", default=None,
                   help="WAF blacklist file (Python list or line-based text); enables automatic bypass strategies")
    p.add_argument("--waf-mode", default="auto",
                   choices=["auto", "presence", "strip", "strip-recursive"],
                   help="Filter semantics hint: presence=reject on match strip=single removal strip-recursive=recursive removal")
    p.add_argument("--fast", action="store_true",
                   help="Fast mode: blind injection decisions cast only 1 vote (halves request volume; may err under sporadic jitter)")
    p.add_argument("--fingerprint", action="store_true", help="Only perform fingerprinting")
    p.add_argument("--file-read", default=None, help="Read a remote file")
    p.add_argument("--file-write", default=None,
                   help="Write a remote file, format: local_path::remote_path")
    p.add_argument("--no-banner", action="store_true", help="Do not display the Banner")

    # ---- Legal disclaimer ----
    # Deliberately **do not provide** switches like --no-legal / --cache-legal:
    # every run requires the user themselves to type I AGREE; no skipping or caching is accepted.
    # This step runs in main() before any network request (see ui/legal.py).

    # ---- Stealth / anti-WAF ----
    g = p.add_argument_group("Stealth mode (anti-WAF)")
    g.add_argument("--workers", type=int, default=4,
                   help="Number of concurrent threads; 1-2 recommended for stealth, 2-4 for a local lab range")
    g.add_argument("--delay", type=float, default=0.0, help="Fixed wait of N seconds after each request")
    g.add_argument("--jitter", type=float, default=0.0, help="Jitter of ± N seconds to the delay")
    g.add_argument("--qps", type=float, default=0.0, help="Global QPS cap")
    g.add_argument("--human", action="store_true", help="Human-like mode")
    g.add_argument("--stealth", action="store_true",
                   help="Stealth preset: workers=1 delay=3 jitter=1 qps=1 random-agent human")
    g.add_argument("--random-agent", action="store_true", help="Random UA per request")
    g.add_argument("--user-agent", default=None, help="Custom User-Agent")
    g.add_argument("--proxy", default=None, help="Single proxy")
    g.add_argument("--proxy-file", default=None, help="Proxy pool file")
    g.add_argument("--proxy-rotate", default="round-robin",
                   choices=["round-robin", "random", "single"])
    g.add_argument("--retries", type=int, default=0, help="Number of retries on request failure")
    g.add_argument("--retry-delay", type=float, default=1.0, help="Retry interval in seconds")

    args = p.parse_args()

    # ---- Parameter names: multi-value support (multiple --param, or one comma-separated value) ----
    param_list = []
    for item in (args.param or ["id"]):
        for name in item.split(","):
            name = name.strip()
            if name and name not in param_list:
                param_list.append(name)
    if not param_list:
        param_list = ["id"]
    args.param_list = param_list
    args.param = param_list[0]          # backward compatibility: take the first in single-value scenarios

    # ---- JSON mode validation ----
    if args.json_body and args.position != "data":
        p.error("--json only supports --position data")

    # stealth preset
    if args.stealth:
        args.workers = 1
        args.delay = max(args.delay, 3.0)
        args.jitter = max(args.jitter, 1.0)
        args.qps = max(args.qps, 1.0)
        args.random_agent = True
        args.human = True
        args.retries = max(args.retries, 2)

    return args


def print_banner(url, args, base_data, base_params, base_cookies):
    if not getattr(args, "no_banner", False):
        banner.print_logo(version="1.2.0", url=url)

    from ui.banner import C
    print(f"{C.DIM}{'─' * 62}{C.RESET}")
    print(f"  {C.CYAN}Method   {C.RESET}: {args.method}")
    print(f"  {C.CYAN}Position {C.RESET}: {args.position}"
          + ("  (JSON body)" if getattr(args, "json_body", False) else ""))
    print(f"  {C.CYAN}Param    {C.RESET}: "
          f"{', '.join(getattr(args, 'param_list', [args.param]))}")
    print(f"  {C.CYAN}Technique{C.RESET}: {args.technique}")
    print(f"  {C.CYAN}DBMS     {C.RESET}: {args.dbms}")
    if args.db:
        print(f"  {C.CYAN}DB       {C.RESET}: {args.db} (manually specified)")
    if args.cols is not None:
        print(f"  {C.CYAN}Cols     {C.RESET}: {args.cols} (manually specified)")
    if args.visible_col is not None:
        print(f"  {C.CYAN}Visible  {C.RESET}: column {args.visible_col} (manually specified)")
    if args.charset != "full":
        print(f"  {C.CYAN}Charset  {C.RESET}: {args.charset}")
    if args.tamper:
        print(f"  {C.CYAN}Tamper   {C.RESET}: {args.tamper}")
    if args.blacklist:
        print(f"  {C.CYAN}Blacklist{C.RESET}: {args.blacklist} (waf-mode={args.waf_mode})")

    stealth_info = []
    if args.stealth:      stealth_info.append("STEALTH")
    if args.human:        stealth_info.append("HUMAN")
    if args.random_agent: stealth_info.append("RANDOM-UA")
    if args.proxy_file:   stealth_info.append(f"PROXY({args.proxy_rotate})")
    elif args.proxy:      stealth_info.append("PROXY")
    if stealth_info:
        print(f"  {C.YELLOW}Mode     {C.RESET}: {', '.join(stealth_info)}")
    print(f"  {C.CYAN}Workers  {C.RESET}: {args.workers}")
    print(f"  {C.CYAN}Delay    {C.RESET}: {args.delay}s (±{args.jitter}s)")
    if args.qps > 0:
        print(f"  {C.CYAN}QPS      {C.RESET}: {args.qps}")

    if base_data:
        print(f"  {C.CYAN}Data     {C.RESET}: {base_data}")
    if base_params:
        print(f"  {C.CYAN}Params   {C.RESET}: {base_params}")
    if base_cookies:
        print(f"  {C.CYAN}Cookies  {C.RESET}: {list(base_cookies.keys())}")
    print(f"{C.DIM}{'─' * 62}{C.RESET}\n")