#!/usr/bin/env python3
"""Patch live blank.html for Event Interest (Stage 3 landing integration).

Adds data-event-id on Upcoming cards and CSS/JS tags. Does not invent class data.
Default map must be verified against public.events before --write on production.

Usage:
  python3 sailingsa/deploy/patch_blank_event_interest.py --file blank.html --dry-run
  python3 sailingsa/deploy/patch_blank_event_interest.py --file blank.html --write
  python3 sailingsa/deploy/patch_blank_event_interest.py --file blank.html --revert
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Verified against Stage 3 preview / calendar mapping. Confirm on prod before write.
SLOT_EVENT_IDS = {
    "1": "168679",
    "2": "246456",
    "3": "248485",
    "4": "45",
}

CSS_TAG = '<link rel="stylesheet" href="/css/event-interest.css?v=eci1">'
JS_TAG = '<script src="/js/event-interest.js?v=eci1"></script>'


def _backup(path: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bak = path.with_name(path.name + f".bak_eci_{ts}")
    shutil.copy2(path, bak)
    return bak


def patch(html: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    out = html

    for slot, event_id in SLOT_EVENT_IDS.items():
        # Add data-event-id when missing on matching slot card
        pattern = re.compile(
            rf'(<article\b[^>]*\blanding-event-card\b[^>]*\bdata-landing-event-slot="{slot}"[^>]*)(>)',
            re.I,
        )

        def repl(m: re.Match, eid: str = event_id) -> str:
            tag = m.group(1)
            if re.search(r'\bdata-event-id="', tag):
                return m.group(0)
            return f'{tag} data-event-id="{eid}"{m.group(2)}'

        new_out, n = pattern.subn(repl, out, count=1)
        if n:
            notes.append(f"slot {slot} → data-event-id={event_id}")
            out = new_out
        else:
            notes.append(f"WARN: slot {slot} article not found")

    if "event-interest.css" not in out:
        if re.search(r'href="/css/main\.css"', out):
            out = out.replace(
                '<link rel="stylesheet" href="/css/main.css">',
                '<link rel="stylesheet" href="/css/main.css">\n    ' + CSS_TAG,
                1,
            )
            notes.append("inserted event-interest.css after main.css")
        else:
            out = out.replace("</head>", f"    {CSS_TAG}\n</head>", 1)
            notes.append("inserted event-interest.css before </head>")
    else:
        notes.append("css already present")

    if "event-interest.js" not in out:
        # Prefer just before </body>
        if "</body>" in out:
            out = out.replace("</body>", f"    {JS_TAG}\n</body>", 1)
            notes.append("inserted event-interest.js before </body>")
        else:
            out += "\n" + JS_TAG + "\n"
            notes.append("appended event-interest.js")
    else:
        notes.append("js already present")

    return out, notes


def revert(html: str) -> tuple[str, list[str]]:
    notes: list[str] = []
    out = html
    out2, n = re.subn(r"\s*data-event-id=\"\d+\"", "", out)
    if n:
        notes.append(f"removed data-event-id from {n} tag(s)")
        out = out2
    out2, n = re.subn(r"\s*<link rel=\"stylesheet\" href=\"/css/event-interest\.css[^>]*>\s*", "\n", out)
    if n:
        notes.append("removed event-interest.css link")
        out = out2
    out2, n = re.subn(r"\s*<script src=\"/js/event-interest\.js[^>]*></script>\s*", "\n", out)
    if n:
        notes.append("removed event-interest.js script")
        out = out2
    return out, notes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, type=Path)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--write", action="store_true")
    g.add_argument("--revert", action="store_true")
    args = ap.parse_args()

    path: Path = args.file
    if not path.is_file():
        print(f"FAIL: file not found: {path}", file=sys.stderr)
        return 2

    original = path.read_text(encoding="utf-8", errors="replace")
    if args.revert:
        updated, notes = revert(original)
    else:
        updated, notes = patch(original)

    for line in notes:
        print(line)

    if original == updated:
        print("No changes needed.")
        return 0

    if args.dry_run:
        print(f"DRY-RUN: would change {path} ({len(updated) - len(original):+d} bytes)")
        return 0

    bak = _backup(path)
    path.write_text(updated, encoding="utf-8")
    print(f"WROTE {path} (backup {bak})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
