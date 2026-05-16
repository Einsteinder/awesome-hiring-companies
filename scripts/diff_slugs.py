#!/usr/bin/env python3
"""Print slugs that changed in data/companies.yml relative to a base ref.

Used by the PR workflow to scope verify_live.py to only entries touched in
the diff. Compares the full set of slugs before vs. after the change; an
edit to an existing entry surfaces its slug; an addition surfaces the new
slug. Output is newline-delimited on stdout.
"""
from __future__ import annotations

import argparse
import subprocess
import sys

import yaml

DATA_PATH = "data/companies.yml"


def load_from_ref(ref: str | None) -> list[dict]:
    if ref is None:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or []
    try:
        blob = subprocess.check_output(
            ["git", "show", f"{ref}:{DATA_PATH}"], stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        return []
    return yaml.safe_load(blob) or []


def entries_by_slug(entries: list[dict]) -> dict[str, dict]:
    return {e["slug"]: e for e in entries if "slug" in e}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Base git ref (e.g. origin/main).")
    args = parser.parse_args()

    base = entries_by_slug(load_from_ref(args.base))
    head = entries_by_slug(load_from_ref(None))

    changed: set[str] = set()
    for slug, entry in head.items():
        if base.get(slug) != entry:
            changed.add(slug)

    for slug in sorted(changed):
        print(slug)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
