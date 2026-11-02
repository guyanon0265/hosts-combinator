#!/usr/bin/env python3
"""
checksum.py — Write SHA-256 checksums for the published artifacts.

Behaviour:
  - Hashes the raw bytes of the combined hosts file, the compressed hosts
    file and the SQLite database.
  - Writes the results to 'checksum.json' in the repo root.
  - The output is deterministic (no timestamps, sorted keys), so re-running
    it on unchanged files produces a byte-identical checksum.json and
    therefore no spurious git commits.
  - Exits non-zero if any input file is missing, so the workflow fails
    instead of publishing an incomplete checksum.json.

Files:
  lists/hosts                  — combined hosts file
  lists/compressedhosts        — compressed hosts file
  sqlite/blockedurls.sqlite3   — SQLite database of blocked domains
  sqlite/dbversion.txt         — (optional) database version, recorded as metadata
  checksum.json                — output

Usage:
    python3 scripts/checksum.py
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime  # used in main() for run timestamp (console only)


# ── Config ────────────────────────────────────────────────────────────────────

HERE          = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT     = os.path.dirname(HERE)  # scripts/ -> repo root
CHECKSUM_FILE = os.path.join(REPO_ROOT, "checksum.json")
VERSION_FILE  = os.path.join(REPO_ROOT, "sqlite", "dbversion.txt")

# key in checksum.json -> path relative to repo root (always forward slashes)
TARGETS: dict[str, str] = {
    "hosts":           "lists/hosts",
    "compressedhosts": "lists/compressedhosts",
    "sqlite":          "sqlite/blockedurls.sqlite3",
}

CHUNK_SIZE = 1024 * 1024  # 1 MiB


# ── Helpers ───────────────────────────────────────────────────────────────────

def banner(text: str) -> None:
    print(f"\n{'─' * 62}")
    print(f"  {text}")
    print(f"{'─' * 62}")


def ok(msg: str)   -> None: print(f"  ✓  {msg}")
def warn(msg: str) -> None: print(f"  ⚠  {msg}")
def fail(msg: str) -> None: print(f"  ✗  {msg}")


def sha256_file(path: str) -> str:
    """Return the SHA-256 hex digest of the file's raw bytes (streamed)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def read_db_version() -> str | None:
    """
    Return the database version string (e.g. '4.6') from dbversion.txt,
    or None if the file is missing or can't be parsed.
    """
    if not os.path.exists(VERSION_FILE):
        return None
    with open(VERSION_FILE, "r", encoding="utf-8") as fh:
        line = fh.read().strip()
    match = re.search(r"Version\s*-\s*([0-9]+\.[0-9]+)", line, re.IGNORECASE)
    return match.group(1) if match else None


def build_checksums() -> dict:
    """Hash every target file and return the checksum.json structure."""
    result: dict = {"algorithm": "sha256", "files": {}}

    for key, rel_path in TARGETS.items():
        abs_path = os.path.join(REPO_ROOT, *rel_path.split("/"))
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(abs_path)

        entry = {
            "path":   rel_path,
            "sha256": sha256_file(abs_path),
            "size":   os.path.getsize(abs_path),
        }
        if key == "sqlite":
            version = read_db_version()
            if version is None:
                warn("Could not read database version — omitting it")
            else:
                entry["version"] = version

        result["files"][key] = entry
        ok(f"{rel_path}")
        print(f"       sha256 : {entry['sha256']}")
        print(f"       size   : {entry['size']:,} bytes")

    return result


def write_checksums(data: dict, path: str) -> None:
    """Write *data* to *path* atomically (temp file + rename)."""
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp_path, path)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║                  CHECKSUM GENERATOR                       ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"\n  Run at : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Output : {CHECKSUM_FILE}\n")

    banner("1 · Hashing files")
    try:
        data = build_checksums()
    except FileNotFoundError as exc:
        fail(f"File not found: {exc}")
        sys.exit(1)
    except OSError as exc:
        fail(f"Could not read file: {exc}")
        sys.exit(1)

    banner("2 · Writing checksum.json")
    action = "Overwriting" if os.path.exists(CHECKSUM_FILE) else "Creating"
    print(f"  {action} {CHECKSUM_FILE} …")
    try:
        write_checksums(data, CHECKSUM_FILE)
    except OSError as exc:
        fail(f"Could not write checksum.json: {exc}")
        sys.exit(1)
    ok(f"{len(data['files'])} checksums written")

    banner("Done")
    print("  checksum.json is up to date\n")


if __name__ == "__main__":
    main()