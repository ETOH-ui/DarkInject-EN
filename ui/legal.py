#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legal disclaimer — mandatory confirmation on every run; cannot be bypassed or cached.

Deliberately **do not provide** `--no-legal` / `--cache-legal`:
    legal confirmation must be made by the user themselves every time. Any "skip switch" or "consent cache"
    would turn this step into a mere formality — once written into a script or CI, confirmation is permanently abandoned.
    So not even a parameter entry point is left here.

Calling convention:
    main() must call legal_disclaimer() **before any network request**.
    Refusal / interruption / mismatched input → sys.exit(1), no return.
"""
import sys

from ui.banner import C


# Content that must be entered exactly (case-insensitive, leading/trailing whitespace ignored)
AGREE_PHRASE = "I AGREE"


def legal_disclaimer():
    """Display the full terms and require typing I AGREE.

    There is no bypass path: no command-line switch is accepted, no cache file is read, no previous result is remembered.
    Returning True only means this confirmation passed.
    """
    print()
    print(f"{C.RED}{C.BOLD}" + "=" * 60 + f"{C.RESET}")
    print(f"{C.RED}{C.BOLD}⚠️  Legal Disclaimer{C.RESET}")
    print(f"{C.RED}{C.BOLD}" + "=" * 60 + f"{C.RESET}")
    print(f"{C.YELLOW}This tool is for authorized security testing only.{C.RESET}")
    print(f"{C.YELLOW}By using this tool you confirm:{C.RESET}")
    print(f"  {C.YELLOW}1. You have obtained explicit written authorization to test the target system{C.RESET}")
    print(f"  {C.YELLOW}2. You will comply with all applicable laws and regulations{C.RESET}")
    print(f"  {C.YELLOW}3. You bear sole responsibility for all legal consequences arising from your use of this tool{C.RESET}")
    print(f"{C.RED}{C.BOLD}" + "=" * 60 + f"{C.RESET}")

    try:
        confirm = input(
            f"{C.CYAN}Type '{AGREE_PHRASE}' to confirm that you have read and agree to the above terms: {C.RESET}"
        )
    except (EOFError, KeyboardInterrupt):
        print(f"\n{C.RED}[-] Not confirmed, exiting.{C.RESET}")
        sys.exit(1)

    if confirm.strip().upper() != AGREE_PHRASE:
        print(f"{C.RED}[-] You did not agree to the terms, exiting.{C.RESET}")
        sys.exit(1)

    print(f"{C.GREEN}[+] Confirmed, continuing...{C.RESET}\n")
    return True
