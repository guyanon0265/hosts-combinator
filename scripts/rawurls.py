#!/usr/bin/env python3
"""
rawurls.py — Strip IP prefixes from hosts and write plain domains to urls.

Reads 'hosts' from the same directory as this script, removes the leading
'0.0.0.0' (or any IP address) from each entry, and writes one bare domain
per line into a file called 'urls' in the same directory.

Usage:
    python3 extract_urls.py
"""

import sys
import os
from datetime import datetime


# ── Config ────────────────────────────────────────────────────────────────────

HERE       = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.dirname(HERE)  # scripts/ -> repo root
HOSTS_FILE = os.path.join(REPO_ROOT, "lists", "hosts")
URLS_FILE  = os.path.join(REPO_ROOT, "lists", "urls")


# ── Core ──────────────────────────────────────────────────────────────────────

def read_domains(path: str) -> list[str]:
    """
    Read *path* and return a list of bare domain strings, in file order.
    Skips blank lines and comment lines (starting with #).
    Strips any leading IP address token (e.g. 0.0.0.0, 127.0.0.1, ::1).
    """
    if not os.path.exists(path):
        print(f"  ✗  hosts file not found: {path}")
        print("     Run update_hosts.py first to generate it.")
        sys.exit(1)

    domains: list[str] = []
    skipped = 0

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            # Strip inline comments and surrounding whitespace
            line = line.split("#")[0].strip()
            if not line:
                continue

            parts = line.split()

            if len(parts) == 1:
                # Bare domain with no leading IP
                domains.append(parts[0].lower())
            elif len(parts) >= 2:
                # "IP domain [extra…]" — drop the IP, keep the domain
                domains.append(parts[1].lower())
            else:
                skipped += 1

    return domains, skipped


def write_urls(domains: list[str], path: str) -> int:
    """
    Write *domains* to *path*, one per line (creating or overwriting).
    Returns the number of domains written.
    """
    action = "Overwriting" if os.path.exists(path) else "Creating"
    print(f"  {action} {path} …")

    with open(path, "w", encoding="utf-8") as fh:
        for domain in domains:
            fh.write(domain + "\n")

    return len(domains)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║              EXTRACT URLs FROM hosts                       ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\n  Run at : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Input  : {HOSTS_FILE}")
    print(f"  Output : {URLS_FILE}\n")

    # Read
    print("── Reading hosts ────────────────────────────────────────────")
    domains, skipped = read_domains(HOSTS_FILE)
    print(f"  ✓  {len(domains):,} domain entries read")
    if skipped:
        print(f"  ⚠  {skipped} line(s) skipped (unrecognised format)")

    # Write
    print("\n── Writing urls ─────────────────────────────────────────────")
    count   = write_urls(domains, URLS_FILE)
    size_kb = os.path.getsize(URLS_FILE) / 1024
    print(f"  ✓  {count:,} domains written  ({size_kb:,.1f} KB)")

    print("\n── Done ─────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
