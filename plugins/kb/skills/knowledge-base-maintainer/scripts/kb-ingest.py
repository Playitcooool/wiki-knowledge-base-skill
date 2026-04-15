#!/usr/bin/env python3
"""
Incremental ingest command for ongoing knowledge-base updates.

Behavior:
- Default: dry-run safety preview.
- With --apply: write updates to pages/, pages/index.md, and log.md.
- In a greenfield directory, --apply bootstraps required folders/files first.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest new or changed sources into the knowledge base."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Knowledge base root directory (default: current directory).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (default is dry-run).",
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve().parent / "sync_kb.py"
    cmd = [sys.executable, str(script_path), "--root", args.root]
    if args.apply:
        cmd.append("--apply")

    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
