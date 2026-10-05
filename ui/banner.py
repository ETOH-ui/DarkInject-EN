#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DarkInject signature Banner + legal disclaimer"""
import os
import sys


class C:
    RESET = "\033[0m"
    BOLD  = "\033[1m"
    DIM   = "\033[2m"

    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"


def _enable_ansi():
    if os.name == "nt":
        try:
            os.system("")
        except Exception:
            pass


def _enable_utf8():
    if os.name == "nt":
        try:
            os.system("chcp 65001 >nul 2>&1")
        except Exception:
            pass
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _supports_unicode():
    enc = (getattr(sys.stdout, "encoding", "") or "").lower()
    if "utf" in enc:
        return True
    if os.name == "nt":
        return False
    return True


BANNER_UNICODE = r"""
          ██████╗  █████╗ ██████╗ ██╗  ██╗
          ██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝
          ██║  ██║███████║██████╔╝█████╔╝
          ██║  ██║██╔══██║██╔══██╗██╔═██╗
          ██████╔╝██║  ██║██║  ██║██║  ██╗
          ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
   ██╗███╗   ██╗     ██╗███████╗ ██████╗████████╗
   ██║████╗  ██║     ██║██╔════╝██╔════╝╚══██╔══╝
   ██║██╔██╗ ██║     ██║█████╗  ██║        ██║
   ██║██║╚██╗██║██   ██║██╔══╝  ██║        ██║
   ██║██║ ╚████║╚█████╔╝███████╗╚██████╗   ██║
   ╚═╝╚═╝  ╚═══╝ ╚════╝ ╚══════╝ ╚═════╝   ╚═╝
"""

BANNER_ASCII = r"""
        ____    _    ____  _  __
       |  _ \  / \  |  _ \| |/ /
       | | | |/ _ \ | |_) | ' /
       | |_| / ___ \|  _ <| . \
       |____/_/   \_\_| \_\_|\_\
    ___ _   _     _ _____ ____ _____
   |_ _| \ | |   | | ____/ ___|_   _|
    | ||  \| |_  | |  _|| |     | |
    | || |\  | |_| | |__| |___  | |
   |___|_| \_|\___/|_____\____| |_|
"""


def print_legal_disclaimer():
    """Print a brief legal disclaimer (sqlmap style)"""
    _enable_ansi()
    print(
        f"   {C.RED}[!]{C.RESET} "
        f"{C.DIM}Disclaimer: attacking a target with this tool without prior mutual consent is illegal.{C.RESET}"
    )
    print(
        f"       {C.DIM}Users are responsible for complying with all applicable laws; the developers assume no liability.{C.RESET}"
    )


def print_logo(version="1.2.0", url=None):
    _enable_ansi()
    _enable_utf8()

    use_unicode = _supports_unicode()
    art = BANNER_UNICODE if use_unicode else BANNER_ASCII
    lines = art.strip("\n").split("\n")

    if use_unicode:
        colors = [C.CYAN, C.CYAN, C.GREEN, C.GREEN, C.YELLOW, C.YELLOW]
        art_colored = "\n".join(
            f"{C.BOLD}{colors[i % len(colors)]}{line}{C.RESET}"
            for i, line in enumerate(lines)
        )
    else:
        # Note: use strip("\n") instead of strip(): the latter also eats the first line's indentation, misaligning the whole block
        art_colored = "\n".join(
            f"{C.BOLD}{C.GREEN}{line}{C.RESET}" for line in lines
        )

    subtitle = (f"   {C.DIM}SQL Injection Toolkit{C.RESET}  "
                f"{C.YELLOW}v{version}{C.RESET}")

    meta = (f"   {C.DIM}┃{C.RESET} {C.CYAN}Tech{C.RESET}  "
            f"{C.DIM}┃{C.RESET} {C.CYAN}DBMS{C.RESET}  "
            f"{C.DIM}┃{C.RESET} {C.CYAN}Tamper{C.RESET}  "
            f"{C.DIM}┃{C.RESET} {C.CYAN}Auto Fingerprint{C.RESET}")

    if url:
        meta += f"\n   {C.DIM}→ Target:{C.RESET} {C.MAGENTA}{url}{C.RESET}"

    print()
    print(art_colored)
    print(subtitle)
    print()
    print(f"   {C.DIM}{'─' * 58}{C.RESET}")
    print(meta)
    print(f"   {C.DIM}{'─' * 58}{C.RESET}")
    print()
    print_legal_disclaimer()
    print()


def print_step(step_no, total, title):
    _enable_ansi()
    print(f"\n{C.BOLD}{C.BLUE}[{step_no}/{total}]{C.RESET} "
          f"{C.BOLD}{title}{C.RESET}")