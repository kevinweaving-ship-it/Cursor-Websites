#!/usr/bin/env python3
"""Create the 2026 ILCA KZN Regional Championships stub so results can be passed.

URL: https://sailingsa.co.za/regatta/2026-08-10-ilca-kzn-regional-championships
Header: generic ILCA logo left, PYC logo right.
Status: Results are Provisional as at 10 August 2026 at 17:25
No fleets / results until the sheet is passed.

Results pass — validated race classes only (never family Ilca/Laser):
  Sheet ILCA 4 / Ilca 4 → class_canonical Ilca 4.7
  Sheet ILCA 6 → Ilca 6; sheet ILCA 7 → Ilca 7
  fleet_label = class as sailed (same validated name as class_canonical).

Requires DATABASE_URL or DB_URL. Merges header icons into data/wc_regatta_header_icons.json
(do not replace that file with a one-key fragment).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import psycopg2

ROOT = Path(__file__).resolve().parents[2]
REGATTA_ID = "2026-08-10-ilca-kzn-regional-championships"
EVENT_NAME = "ILCA KZN Regional Championships"
SOURCE_URL = "https://www.laser.org.za/events/364968"
FRAGMENT = Path(__file__).resolve().parent / "header_icons_2026_08_10_ilca_kzn_regional_championships.json"
HEADER_ICONS = {
    "left": "/artwork/Class Logo/ILCA-Class-Logo.png",
    "right": "/api/club-logo/PYC",
}


def _db_url() -> str:
    url = (os.environ.get("DATABASE_URL") or os.environ.get("DB_URL") or "").strip()
    if not url:
        raise SystemExit("Set DATABASE_URL or DB_URL")
    return url


def _regatta_columns(cur) -> set[str]:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'regattas'
        """
    )
    return {r[0] for r in cur.fetchall() or []}


def upsert_regatta(cur) -> None:
    cols = _regatta_columns(cur)
    cur.execute(
        """
        SELECT club_id, club_abbrev, club_fullname
        FROM clubs
        WHERE UPPER(TRIM(club_abbrev)) = 'PYC'
        LIMIT 1
        """
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit("clubs.club_abbrev PYC not found")
    club_id, club_abbrev, club_fullname = row[0], row[1], row[2]

    wanted = {
        "regatta_id": REGATTA_ID,
        "event_name": EVENT_NAME,
        "year": 2026,
        "start_date": "2026-08-08",
        "end_date": "2026-08-10",
        "as_at_time": "2026-08-10 17:25:00+02",
        "result_status": "Provisional",
        "host_club_id": club_id,
        "host_club_code": (club_abbrev or "PYC"),
        "host_club_name": club_fullname,
        "province_name": "KZN",
        "province_code": "KZN",
        "regatta_type": "Regional Championships",
        "source_url": SOURCE_URL,
        "import_status": "pending",
    }
    insert_cols = [c for c in wanted if c in cols]
    placeholders = ", ".join(["%s"] * len(insert_cols))
    col_sql = ", ".join(insert_cols)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in insert_cols if c != "regatta_id")
    cur.execute(
        f"""
        INSERT INTO public.regattas ({col_sql})
        VALUES ({placeholders})
        ON CONFLICT (regatta_id) DO UPDATE SET {updates}
        """,
        tuple(wanted[c] for c in insert_cols),
    )


def link_event(cur) -> int:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'events' AND column_name = 'regatta_id'
        """
    )
    if not cur.fetchone():
        return 0
    cur.execute(
        """
        UPDATE public.events
        SET regatta_id = %s
        WHERE TRIM(event_name) = '2026 ILCA KZN Regional Championships'
          AND start_date = DATE '2026-08-08'
        """,
        (REGATTA_ID,),
    )
    return cur.rowcount or 0


def _icon_targets() -> list[Path]:
    paths = [ROOT / "data" / "wc_regatta_header_icons.json"]
    live = Path("/var/www/sailingsa/data/wc_regatta_header_icons.json")
    if live.parent.is_dir() and live not in paths:
        paths.append(live)
    return paths


def patch_header_icons() -> list[Path]:
    icons = dict(HEADER_ICONS)
    if FRAGMENT.is_file():
        try:
            loaded = json.loads(FRAGMENT.read_text(encoding="utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get(REGATTA_ID), dict):
                icons = dict(loaded[REGATTA_ID])
        except Exception:
            pass
    written: list[Path] = []
    for path in _icon_targets():
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if path.is_file():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    data = loaded
            except Exception:
                data = {}
        data[REGATTA_ID] = dict(icons)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def main() -> None:
    icons = patch_header_icons()
    conn = psycopg2.connect(_db_url())
    try:
        with conn.cursor() as cur:
            upsert_regatta(cur)
            n = link_event(cur)
        conn.commit()
    finally:
        conn.close()
    print(f"regatta_id={REGATTA_ID}")
    print(f"events_linked={n}")
    print("header_icons=" + ",".join(str(p) for p in icons))
    print("url=https://sailingsa.co.za/regatta/2026-08-10-ilca-kzn-regional-championships")
    print("status_line=Results are Provisional as at 10 August 2026 at 17:25")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
