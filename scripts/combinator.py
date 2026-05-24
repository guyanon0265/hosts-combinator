#!/usr/bin/env python3
"""
combinator.py — Fetch, diff, deduplicate, and write a combined hosts file.

Sources:
  1. StevenBlack porn-only
     https://raw.githubusercontent.com/StevenBlack/hosts/refs/heads/master/alternates/porn-only/hosts
  2. 4skinSkywalker Anti-Porn
     https://raw.githubusercontent.com/4skinSkywalker/Anti-Porn-HOSTS-File/refs/heads/master/HOSTS.txt
  3. guyanon0265 hosts-combinator example
     https://raw.githubusercontent.com/guyanon0265/hosts-combinator/refs/heads/main/example

Behaviour:
  - Downloads all three lists fresh every run.
  - Compares each against a locally cached copy (stored in .cache/).
  - If nothing has changed across all three, exits early.
  - If anything changed, deduplicates the union and writes 'hosts' in this
    script's directory (creating it if it doesn't exist, overwriting if it does).

Usage:
    python3 update_hosts.py
"""

import urllib.request
import subprocess
import hashlib
import json
import sys
import re
import os
from datetime import datetime


# ── Config ────────────────────────────────────────────────────────────────────

SOURCES: dict[str, str] = {
    "StevenBlack-porn-only": (
        "https://raw.githubusercontent.com/StevenBlack/hosts/"
        "refs/heads/master/alternates/porn-only/hosts"
    ),
    "4skinSkywalker": (
        "https://raw.githubusercontent.com/4skinSkywalker/Anti-Porn-HOSTS-File/"
        "refs/heads/master/HOSTS.txt"
    ),
    "guyanon0265-example": (
        "https://raw.githubusercontent.com/guyanon0265/hosts-combinator/"
        "refs/heads/main/example"
    ),
}

HERE        = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.dirname(HERE)  # scripts/ -> repo root
HOSTS_FILE  = os.path.join(REPO_ROOT, "lists", "hosts")
HASHES_FILE = os.path.join(REPO_ROOT, "source_hashes.json")


# ── Fetch ─────────────────────────────────────────────────────────────────────

def fetch_raw(name: str, url: str) -> str:
    """Download *url* and return its text. Tries urllib then curl."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/plain,text/html,*/*",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e1:
        print(f"    urllib failed ({e1}), trying curl …")

    try:
        result = subprocess.run(
            ["curl", "-fsSL", "--max-time", "30", "-A",
             "Mozilla/5.0 (compatible; update-hosts/1.0)", url],
            capture_output=True, text=True, check=True,
        )
        return result.stdout
    except FileNotFoundError:
        raise RuntimeError(f"[{name}] curl not found and urllib failed.")
    except subprocess.CalledProcessError as e2:
        raise RuntimeError(
            f"[{name}] curl failed (exit {e2.returncode}): {e2.stderr.strip()}"
        )


# ── Change detection ──────────────────────────────────────────────────────────

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_saved_hashes() -> dict[str, str]:
    """Load previously saved source hashes from source_hashes.json.
    Returns an empty dict if the file doesn't exist yet."""
    if not os.path.exists(HASHES_FILE):
        return {}
    with open(HASHES_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_hashes(hashes: dict[str, str]) -> None:
    """Write current source hashes to source_hashes.json."""
    with open(HASHES_FILE, "w", encoding="utf-8") as fh:
        json.dump(hashes, fh, indent=2)
        fh.write("\n")


# ── Parse ─────────────────────────────────────────────────────────────────────

_SKIP = {
    "localhost", "localhost.localdomain", "local", "broadcasthost",
    "ip6-localhost", "ip6-loopback", "ip6-localnet", "ip6-mcastprefix",
    "ip6-allnodes", "ip6-allrouters", "ip6-allhosts", "0.0.0.0",
}
_VALID_IP = {"0.0.0.0", "127.0.0.1", "::1", "::"}
_DOMAIN_RE = re.compile(r"^[a-z0-9.\-]+\.[a-z]{2,}$")


def parse_hosts(text: str) -> set[str]:
    """Extract blocked domains from a hosts-file string."""
    domains: set[str] = set()
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            ip, domain = parts[0], parts[1].lower()
            if ip not in _VALID_IP:
                continue
        elif len(parts) == 1:
            # bare domain line (some lists omit the IP)
            domain = parts[0].lower()
        else:
            continue
        if domain in _SKIP or domain.startswith("0.0.0.0"):
            continue
        if _DOMAIN_RE.match(domain):
            domains.add(domain)
    return domains


# ── Write hosts ───────────────────────────────────────────────────────────────

def write_hosts(domains: set[str], source_names: list[str]) -> int:
    """Write (or overwrite) the hosts file. Returns domain count."""
    sorted_domains = sorted(domains)
    generated_at   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(HOSTS_FILE, "w", encoding="utf-8") as fh:
        fh.write(f"# hosts — generated {generated_at}\n")
        fh.write(f"# Sources: {', '.join(source_names)}\n")
        fh.write(f"# Total unique domains: {len(sorted_domains):,}\n")
        fh.write("#\n")
        for domain in sorted_domains:
            fh.write(f"0.0.0.0 {domain}\n")

    return len(sorted_domains)


# ── Helpers ───────────────────────────────────────────────────────────────────

def banner(text: str) -> None:
    width = 62
    print(f"\n{'─' * width}")
    print(f"  {text}")
    print(f"{'─' * width}")


def ok(msg: str)   -> None: print(f"  ✓  {msg}")
def warn(msg: str) -> None: print(f"  ⚠  {msg}")
def fail(msg: str) -> None: print(f"  ✗  {msg}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║              HOSTS UPDATE TOOL                             ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\n  Run at : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Output : {HOSTS_FILE}")
    print(f"  Hashes : {HASHES_FILE}\n")

    # ── Step 1: Fetch ─────────────────────────────────────────────────────────
    banner("1 · Fetching lists")
    raw:     dict[str, str] = {}
    hashes:  dict[str, str] = {}
    changed: dict[str, bool] = {}
    failed:  list[str] = []

    for name, url in SOURCES.items():
        print(f"\n  [{name}]")
        print(f"    {url}")
        try:
            text       = fetch_raw(name, url)
            h          = sha256(text)
            raw[name]  = text
            hashes[name] = h
            kb = len(text) / 1024
            ok(f"{kb:,.1f} KB fetched  (sha256: {h[:12]}…)")
        except Exception as exc:
            fail(f"Download failed — {exc}")
            failed.append(name)

    if len(failed) == len(SOURCES):
        fail("All downloads failed. Aborting.")
        sys.exit(1)
    if failed:
        warn(f"Could not fetch: {', '.join(failed)}. Continuing with the rest.")

    # ── Step 2: Change detection ──────────────────────────────────────────────
    banner("2 · Checking for changes")

    saved = load_saved_hashes()
    for name in list(raw.keys()):
        if hashes[name] != saved.get(name):
            changed[name] = True
            ok(f"{name}  →  CHANGED")
        else:
            changed[name] = False
            print(f"  –  {name}  →  no change")

    if not any(changed.values()):
        print("\n  ✓ All lists are unchanged since last run. Nothing to do.")
        sys.exit(0)

    num_changed = sum(changed.values())
    print(f"\n  {num_changed} of {len(raw)} list(s) changed — proceeding.")

    # ── Step 3: Parse & deduplicate ───────────────────────────────────────────
    banner("3 · Parsing & deduplicating")

    per_source: dict[str, set[str]] = {}
    for name, text in raw.items():
        per_source[name] = parse_hosts(text)
        ok(f"{name}: {len(per_source[name]):,} domains parsed")

    # Cross-source duplicate stats
    names = list(per_source.keys())
    union: set[str] = set()
    for ds in per_source.values():
        union |= ds

    raw_total = sum(len(ds) for ds in per_source.values())
    dupes     = raw_total - len(union)

    print(f"\n  Raw total (with dupes) : {raw_total:>10,}")
    print(f"  Duplicates removed     : {dupes:>10,}")
    print(f"  Unique domains         : {len(union):>10,}")

    # Per-pair overlap
    if len(names) > 1:
        print("\n  Pairwise overlap:")
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b   = names[i], names[j]
                shared = len(per_source[a] & per_source[b])
                print(f"    {a}  ∩  {b}  =  {shared:,} shared domains")

    # ── Step 4 & 5: Write hosts ───────────────────────────────────────────────
    banner("4 · Writing hosts file")

    action = "Overwriting" if os.path.exists(HOSTS_FILE) else "Creating"
    print(f"  {action} {HOSTS_FILE} …")

    count   = write_hosts(union, list(per_source.keys()))
    size_kb = os.path.getsize(HOSTS_FILE) / 1024
    ok(f"{count:,} unique domains written  ({size_kb:,.1f} KB)")

    # Persist hashes only after a successful write
    save_hashes(hashes)

    # ── Done ──────────────────────────────────────────────────────────────────
    banner("Done")
    print(f"  hosts file is up to date with {count:,} unique blocked domains.\n")


if __name__ == "__main__":
    main()
