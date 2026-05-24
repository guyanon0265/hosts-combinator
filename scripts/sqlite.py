#!/usr/bin/env python3
"""
sqlite.py — Load domains from 'urls' into an SQLite database 'blockedurls'.

Behaviour:
  - Reads bare domains from 'urls' (one per line).
  - Wipes and repopulates the 'domains' table in 'blockedurls.db' each run
    (no previous versions are kept).
  - After a successful update, increments the version in 'dbversion.txt'
    by 0.1. If 'dbversion.txt' does not exist, it is created at Version 0.1.

Files (all in the same directory as this script):
  urls          — input: one domain per line
  blockedurls   — SQLite database
  dbversion.txt — plain-text version tracker

Usage:
    python3 urls_to_db.py
"""

import sqlite3
import sys
import os
import re
from datetime import datetime  # used in main() for run timestamp


# ── Config ────────────────────────────────────────────────────────────────────

HERE         = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT    = os.path.dirname(HERE)  # scripts/ -> repo root
URLS_FILE    = os.path.join(REPO_ROOT, "lists",   "urls")
DB_FILE      = os.path.join(REPO_ROOT, "sqlite",  "blockedurls.sqlite3")
VERSION_FILE = os.path.join(REPO_ROOT, "sqlite",  "dbversion.txt")


# ── Version helpers ───────────────────────────────────────────────────────────

def read_version() -> float:
    """
    Read the current version from dbversion.txt.
    Returns 0.0 if the file doesn't exist or can't be parsed.
    """
    if not os.path.exists(VERSION_FILE):
        return 0.0

    with open(VERSION_FILE, "r", encoding="utf-8") as fh:
        line = fh.read().strip()

    match = re.search(r"Version\s*-\s*([0-9]+\.[0-9]+)", line, re.IGNORECASE)
    if match:
        return float(match.group(1))

    print(f"  ⚠  Could not parse version from '{line}' — resetting to 0.0")
    return 0.0


def write_version(version: float) -> None:
    """Write the version to dbversion.txt in the required format."""
    # Round to 1 decimal to avoid floating-point drift (0.1 + 0.2 != 0.3)
    version = round(version, 1)
    with open(VERSION_FILE, "w", encoding="utf-8") as fh:
        fh.write(f"Version - {version:.1f}\n")


def increment_version(current: float) -> float:
    """Increment version by 0.1, avoiding floating-point imprecision."""
    return round(current + 0.1, 1)


# ── URL reader ────────────────────────────────────────────────────────────────

def read_urls(path: str) -> list[str]:
    """
    Read domains from *path*, one per line.
    Skips blank lines and comment lines.
    """
    if not os.path.exists(path):
        print(f"  ✗  urls file not found: {path}")
        print("     Run extract_urls.py first to generate it.")
        sys.exit(1)

    domains: list[str] = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.split("#")[0].strip()
            if line:
                domains.append(line.lower())

    return domains


# ── Database ──────────────────────────────────────────────────────────────────

def update_database(domains: list[str], db_path: str) -> int:
    """
    Open (or create) the SQLite database at *db_path*, wipe the domains table,
    and repopulate it. Returns the number of rows inserted.
    """
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Create table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS domains (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            domain  TEXT    NOT NULL UNIQUE
        )
    """)

    # Wipe all existing rows (no version history needed)
    cur.execute("DELETE FROM domains")

    # Bulk insert
    cur.executemany(
        "INSERT INTO domains (domain) VALUES (?)",
        [(domain,) for domain in domains]
    )

    con.commit()
    count = cur.execute("SELECT COUNT(*) FROM domains").fetchone()[0]
    con.close()

    return count


# ── Helpers ───────────────────────────────────────────────────────────────────

def banner(text: str) -> None:
    print(f"\n{'─' * 62}")
    print(f"  {text}")
    print(f"{'─' * 62}")


def ok(msg: str)   -> None: print(f"  ✓  {msg}")
def warn(msg: str) -> None: print(f"  ⚠  {msg}")
def fail(msg: str) -> None: print(f"  ✗  {msg}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║           URLs → SQLite DATABASE                          ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\n  Run at  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Input   : {URLS_FILE}")
    print(f"  Database: {DB_FILE}")
    print(f"  Version : {VERSION_FILE}\n")

    # ── Step 1: Read urls ─────────────────────────────────────────────────────
    banner("1 · Reading urls")
    domains = read_urls(URLS_FILE)
    ok(f"{len(domains):,} domains read")

    # ── Step 2: Update database ───────────────────────────────────────────────
    banner("2 · Updating database")
    action = "Overwriting" if os.path.exists(DB_FILE) else "Creating"
    print(f"  {action} {DB_FILE} …")

    try:
        inserted = update_database(domains, DB_FILE)
        ok(f"{inserted:,} rows in database")
        size_kb = os.path.getsize(DB_FILE) / 1024
        ok(f"Database size: {size_kb:,.1f} KB")
    except sqlite3.Error as exc:
        fail(f"Database error: {exc}")
        sys.exit(1)

    # ── Step 3: Increment version ─────────────────────────────────────────────
    banner("3 · Updating version")

    current_version = read_version()
    if not os.path.exists(VERSION_FILE):
        print("  dbversion.txt not found — creating it.")

    new_version = increment_version(current_version)
    write_version(new_version)
    ok(f"Version {current_version:.1f}  →  {new_version:.1f}  ({VERSION_FILE})")

    # ── Done ──────────────────────────────────────────────────────────────────
    banner("Done")
    print(f"  blockedurls is up to date — {inserted:,} domains, version {new_version:.1f}\n")


if __name__ == "__main__":
    main()
