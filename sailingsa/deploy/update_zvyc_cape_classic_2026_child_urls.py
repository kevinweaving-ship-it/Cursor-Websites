#!/usr/bin/env python3
"""Correct ZVYC Cape Classic 2026 fleet labels and the ILCA 4.7 child URL.

Live child URLs are fluid `{parent}-{block-tail}` while the event is
upcoming/happening. Additional classes (420, Mirror, Open) already have
shells; ILCA 4.7 was still published as `…-ilca-4-fleet` with no class logo.

Usage on live (DB_URL from sailingsa-api.service):
  python3 fix_zvyc_cape_classic_2026_child_urls.py
  python3 fix_zvyc_cape_classic_2026_child_urls.py --apply
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

PARENT = "2026-09-13-zvyc-cape-classic"
OLD_TAIL = "ilca-4-fleet"
NEW_TAIL = "ilca-4.7-fleet"
OLD_BID = f"{PARENT}:{OLD_TAIL}"
NEW_BID = f"{PARENT}:{NEW_TAIL}"
OLD_SLUG = f"{PARENT}-{OLD_TAIL}"
NEW_SLUG = f"{PARENT}-{NEW_TAIL}"

FLEET_LABELS = {
    f"{PARENT}:420-fleet": "420",
    f"{PARENT}:extra-fleet": "Extra",
    f"{PARENT}:ilca-4-fleet": "ILCA 4.7",
    f"{PARENT}:ilca-4.7-fleet": "ILCA 4.7",
    f"{PARENT}:ilca-6-fleet": "ILCA 6",
    f"{PARENT}:ilca-7-fleet": "ILCA 7",
    f"{PARENT}:mirror-fleet": "Mirror",
    f"{PARENT}:open": "Open",
    f"{PARENT}:optimist-a-fleet": "Optimist",
}


def db_url() -> str:
    env = (os.environ.get("DB_URL") or "").strip()
    if env:
        return env
    service = Path("/etc/systemd/system/sailingsa-api.service")
    if service.is_file():
        m = re.search(r"DB_URL=(.+)", service.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1).strip().strip("\"'")
    raise SystemExit("DB_URL not set")


def redirect_paths() -> list[Path]:
    paths = [
        Path("/var/www/sailingsa/static/data/regatta_slug_redirects.json"),
        Path("/var/www/sailingsa/data/regatta_slug_redirects.json"),
    ]
    return [p for p in paths if p.parent.is_dir()]


def upsert_redirect(apply: bool) -> None:
    payload_key = OLD_SLUG
    payload_val = f"/regatta/{NEW_SLUG}"
    for p in redirect_paths():
        data = {}
        if p.is_file():
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    data = raw
            except Exception:
                data = {}
        prev = data.get(payload_key)
        print(f"redirect {p}: {payload_key} -> {payload_val} (was {prev!r})")
        if not apply:
            continue
        data[payload_key] = payload_val
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    apply = bool(args.apply)

    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(db_url())
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT block_id, class_id, class_canonical, fleet_label, block_label_raw
        FROM regatta_blocks
        WHERE regatta_id = %s
        ORDER BY block_id
        """,
        (PARENT,),
    )
    rows = list(cur.fetchall() or [])
    if not rows:
        print("No blocks for", PARENT)
        return 1
    print("CURRENT BLOCKS")
    for r in rows:
        print(dict(r))

    for r in rows:
        bid = str(r["block_id"])
        label = FLEET_LABELS.get(bid)
        if not label:
            continue
        print(f"set labels {bid} => {label}")
        if apply:
            cur.execute(
                """
                UPDATE regatta_blocks
                SET fleet_label = %s,
                    block_label_raw = COALESCE(NULLIF(TRIM(block_label_raw), ''), %s)
                WHERE block_id = %s
                """,
                (label, label, bid),
            )

    # Rename ILCA 4.7 block / child URL if still on the old tail.
    cur.execute("SELECT 1 FROM regatta_blocks WHERE block_id = %s", (OLD_BID,))
    has_old = bool(cur.fetchone())
    cur.execute("SELECT 1 FROM regatta_blocks WHERE block_id = %s", (NEW_BID,))
    has_new = bool(cur.fetchone())
    print(f"rename {OLD_BID} -> {NEW_BID} has_old={has_old} has_new={has_new}")
    if has_old and not has_new:
        tables = ("results", "entries", "races")
        if apply:
            cur.execute(
                """
                UPDATE regatta_blocks
                SET block_id = %s,
                    fleet_label = 'ILCA 4.7',
                    block_label_raw = 'ILCA 4.7',
                    class_canonical = 'Ilca 4.7',
                    class_original = COALESCE(NULLIF(TRIM(class_original), ''), 'Ilca 4.7')
                WHERE block_id = %s
                """,
                (NEW_BID, OLD_BID),
            )
            for tbl in tables:
                cur.execute(
                    f"SELECT COUNT(*) AS n FROM {tbl} WHERE block_id = %s",
                    (OLD_BID,),
                )
                n = int((cur.fetchone() or {}).get("n") or 0)
                print(f"  {tbl} rows on old block: {n}")
                if n:
                    cur.execute(
                        f"UPDATE {tbl} SET block_id = %s WHERE block_id = %s",
                        (NEW_BID, OLD_BID),
                    )
        else:
            for tbl in tables:
                try:
                    cur.execute(
                        f"SELECT COUNT(*) AS n FROM {tbl} WHERE block_id = %s",
                        (OLD_BID,),
                    )
                    print(f"  {tbl} rows on old block: {(cur.fetchone() or {}).get('n')}")
                except Exception as e:
                    conn.rollback()
                    print(f"  {tbl}: skip ({e})")

    upsert_redirect(apply)

    if apply:
        conn.commit()
        print("APPLIED")
    else:
        conn.rollback()
        print("DRY RUN (pass --apply to write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
