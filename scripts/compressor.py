#!/usr/bin/env python3
"""
compressor.py — Compress hosts file to 9 domains per line.

Reads 'lists/hosts', groups domains into lines of 9, and writes the
result to 'lists/compressedhosts'.

Format of each output line:
    0.0.0.0 domain1.com domain2.com ... domain9.com

Usage:
    python3 scripts/compress_hosts.py
"""

import sys
import os
from datetime import datetime


# ── Config ────────────────────────────────────────────────────────────────────

HERE             = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT        = os.path.dirname(HERE)  # scripts/ -> repo root
HOSTS_FILE       = os.path.join(REPO_ROOT, "lists", "hosts")
COMPRESSED_FILE  = os.path.join(REPO_ROOT, "lists", "compressedhosts")

DOMAINS_PER_LINE = 9


# ── Read ──────────────────────────────────────────────────────────────────────

def read_domains(path: str) -> list[str]:
    """Read bare domains from a hosts file, skipping comments and blank lines."""
    if not os.path.exists(path):
        print(f"  ✗  hosts file not found: {path}")
        print("     Run update_hosts.py first to generate it.")
        sys.exit(1)

    domains: list[str] = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.split("#")[0].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                domains.append(parts[1].lower())
            elif len(parts) == 1:
                domains.append(parts[0].lower())

    return domains


# ── Write ─────────────────────────────────────────────────────────────────────

def write_compressed(domains: list[str], path: str, per_line: int) -> tuple[int, int]:
    """
    Write domains to *path*, grouping *per_line* domains per line.
    Each line: 0.0.0.0 domain1 domain2 ... domainN
    Returns (lines_written, domains_written).
    """
    action = "Overwriting" if os.path.exists(path) else "Creating"
    print(f"  {action} {path} …")

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total        = len(domains)
    lines        = 0

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"# compressedhosts — generated {generated_at}\n")
        fh.write(f"# {total:,} domains, {per_line} per line\n")
        fh.write("#\n")

        for i in range(0, total, per_line):
            chunk = domains[i : i + per_line]
            fh.write("0.0.0.0 " + " ".join(chunk) + "\n")
            lines += 1

    return lines, total


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║           COMPRESS HOSTS FILE                              ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\n  Run at : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Input  : {HOSTS_FILE}")
    print(f"  Output : {COMPRESSED_FILE}\n")

    # Read
    print("── Reading hosts ────────────────────────────────────────────")
    domains = read_domains(HOSTS_FILE)
    print(f"  ✓  {len(domains):,} domains read")

    # Write
    print("\n── Writing compressedhosts ──────────────────────────────────")
    lines, total = write_compressed(domains, COMPRESSED_FILE, DOMAINS_PER_LINE)
    size_kb      = os.path.getsize(COMPRESSED_FILE) / 1024
    reduction    = (1 - (size_kb / (os.path.getsize(HOSTS_FILE) / 1024))) * 100
    print(f"  ✓  {total:,} domains written across {lines:,} lines")
    print(f"  ✓  File size : {size_kb:,.1f} KB  ({reduction:.1f}% smaller than hosts)")

    print("\n── Done ─────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    main()
