#!/usr/bin/env python3
"""Match SAS 2026 420 Nationals (TSC) to events and create the Event URL.

Live calendar row (already in public.events):
  event_name       = 420 Nationals
  start/end        = 2026-09-25 / 2026-09-27
  category         = National Championships
  source_event_id  = 377703
  source_url       = https://www.sailing.org.za/events/377703
  venue            = Theewater Sports Club (TSC)
  regatta_id       = NULL  (needs Event URL)

Creates / links, same pattern as Midmar Cup preload:
  Event URL = https://sailingsa.co.za/regatta/2026-09-25-tsc-420-nationals

Idempotent. Default is apply; use --dry-run to print the plan only.

  export DB_URL=...   # from sailingsa-api.service on live
  python3 sailingsa/deploy/create_tsc_420_nationals_2026_event_url.py
  python3 sailingsa/deploy/create_tsc_420_nationals_2026_event_url.py --dry-run
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

REGATTA_ID = "2026-09-25-tsc-420-nationals"
EVENT_NAME = "420 Nationals"
YEAR = 2026
START_DATE = date(2026, 9, 25)
END_DATE = date(2026, 9, 27)
SAS_EVENT_ID = "377703"
SAS_URL = "https://www.sailing.org.za/events/377703"
EVENT_URL = f"https://sailingsa.co.za/regatta/{REGATTA_ID}"
HOST_ABBREV = "TSC"
BLOCK_ID = f"{REGATTA_ID}:420"
PROVINCE = "WC"


def get_db_url() -> str:
    url = (os.getenv("DATABASE_URL") or os.getenv("DB_URL") or "").strip()
    if not url:
        print("ERROR: DATABASE_URL or DB_URL not set.", file=sys.stderr)
        sys.exit(1)
    return url


def col_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s AND column_name = %s
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def fetch_one(cur, sql: str, args=()):
    cur.execute(sql, args)
    return cur.fetchone()


def resolve_event(cur) -> dict:
    row = fetch_one(
        cur,
        """
        SELECT event_id, event_name, start_date, end_date, source, source_event_id,
               source_url, host_club_id, host_club_name_raw, venue_raw, regatta_id
        FROM events
        WHERE source_event_id = %s
           OR (lower(trim(event_name)) = '420 nationals'
               AND start_date = %s)
        ORDER BY CASE WHEN source_event_id = %s THEN 0 ELSE 1 END, event_id
        LIMIT 1
        """,
        (SAS_EVENT_ID, START_DATE, SAS_EVENT_ID),
    )
    if not row:
        raise SystemExit(
            "ERROR: 420 Nationals 2026-09-25 / SAS 377703 not found in events. "
            "Re-run the SAS events scrape first."
        )
    return dict(row)


def resolve_tsc(cur) -> dict:
    row = fetch_one(
        cur,
        """
        SELECT club_id, club_abbrev, club_fullname
        FROM clubs
        WHERE upper(trim(club_abbrev)) = 'TSC'
           OR lower(trim(club_fullname)) = 'theewater sports club'
        ORDER BY CASE WHEN upper(trim(club_abbrev)) = 'TSC' THEN 0 ELSE 1 END
        LIMIT 1
        """,
    )
    if not row:
        raise SystemExit("ERROR: TSC / Theewater Sports Club not found in clubs.")
    return dict(row)


def resolve_class_420(cur) -> dict:
    row = fetch_one(
        cur,
        """
        SELECT class_id, class_name
        FROM classes
        WHERE trim(class_name) = '420'
        LIMIT 1
        """,
    )
    if not row:
        row = fetch_one(
            cur,
            """
            SELECT class_id, class_name
            FROM classes
            WHERE lower(trim(class_name)) = '420'
            LIMIT 1
            """,
        )
    if not row:
        raise SystemExit("ERROR: class_name '420' not found in classes.")
    return dict(row)


def next_regatta_number(cur) -> int:
    cur.execute(
        "SELECT COALESCE(MAX(regatta_number), 0) + 1 AS next_num FROM regattas WHERE regatta_number IS NOT NULL"
    )
    row = cur.fetchone()
    if isinstance(row, dict):
        return int(row["next_num"])
    return int(row[0])


def ensure_regatta(cur, tsc: dict, class_420: dict, dry_run: bool) -> str:
    existing = fetch_one(
        cur,
        "SELECT regatta_id, event_name FROM regattas WHERE regatta_id = %s",
        (REGATTA_ID,),
    )
    if existing:
        print(f"regattas: already present {existing['regatta_id']} ({existing['event_name']})")
        return existing["regatta_id"]

    number = next_regatta_number(cur)
    cols = [
        "regatta_id",
        "event_name",
        "year",
        "start_date",
        "end_date",
        "result_status",
        "host_club_id",
        "import_status",
    ]
    vals = [
        REGATTA_ID,
        EVENT_NAME,
        YEAR,
        START_DATE,
        END_DATE,
        "Provisional",
        tsc["club_id"],
        "pending",
    ]
    if col_exists(cur, "regattas", "regatta_number"):
        cols.append("regatta_number")
        vals.append(number)
    if col_exists(cur, "regattas", "host_club_code"):
        cols.append("host_club_code")
        vals.append(HOST_ABBREV)
    if col_exists(cur, "regattas", "host_club_name"):
        cols.append("host_club_name")
        vals.append(tsc.get("club_fullname") or "Theewater Sports Club")
    if col_exists(cur, "regattas", "province_name"):
        cols.append("province_name")
        vals.append(PROVINCE)
    if col_exists(cur, "regattas", "source_url"):
        cols.append("source_url")
        vals.append(SAS_URL)

    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO regattas ({', '.join(cols)}) VALUES ({placeholders})"
    print(f"regattas: INSERT {REGATTA_ID} number={number} host=TSC class={class_420['class_name']}")
    if not dry_run:
        cur.execute(sql, tuple(vals))
    return REGATTA_ID


def ensure_block(cur, class_420: dict, dry_run: bool) -> None:
    existing = fetch_one(
        cur,
        "SELECT block_id FROM regatta_blocks WHERE block_id = %s OR (regatta_id = %s AND lower(trim(COALESCE(class_canonical, class_original, ''))) = '420')",
        (BLOCK_ID, REGATTA_ID),
    )
    if existing:
        print(f"regatta_blocks: already present {existing['block_id']}")
        return

    class_name = (class_420.get("class_name") or "420").strip()
    cols = [
        "block_id",
        "regatta_id",
        "class_original",
        "class_canonical",
        "fleet_label",
        "races_sailed",
        "discard_count",
        "to_count",
    ]
    vals = [BLOCK_ID, REGATTA_ID, class_name, class_name, class_name, 0, 0, 0]
    if col_exists(cur, "regatta_blocks", "scoring_system"):
        cols.append("scoring_system")
        vals.append("Appendix A")
    if col_exists(cur, "regatta_blocks", "handicap_system"):
        cols.append("handicap_system")
        vals.append("Appendix A")
    if col_exists(cur, "regatta_blocks", "class_id"):
        cols.append("class_id")
        vals.append(class_420["class_id"])
    if col_exists(cur, "regatta_blocks", "entries_raced"):
        cols.append("entries_raced")
        vals.append(0)
    if col_exists(cur, "regatta_blocks", "block_label_raw"):
        cols.append("block_label_raw")
        vals.append("420")

    placeholders = ", ".join(["%s"] * len(cols))
    print(f"regatta_blocks: INSERT {BLOCK_ID} class={class_name}")
    if not dry_run:
        cur.execute(
            f"INSERT INTO regatta_blocks ({', '.join(cols)}) VALUES ({placeholders})",
            tuple(vals),
        )


def link_event(cur, event: dict, tsc: dict, dry_run: bool) -> None:
    sets = []
    args = []
    if (event.get("regatta_id") or "").strip() != REGATTA_ID:
        sets.append("regatta_id = %s")
        args.append(REGATTA_ID)
    if event.get("host_club_id") != tsc["club_id"]:
        sets.append("host_club_id = %s")
        args.append(tsc["club_id"])
    if col_exists(cur, "events", "host_club_name_raw"):
        raw = (event.get("host_club_name_raw") or "").strip()
        if "theewater" not in raw.lower() and "tsc" not in raw.lower():
            sets.append("host_club_name_raw = %s")
            args.append("Theewater Sports Club")
    if not sets:
        print(f"events: already linked event_id={event['event_id']} -> {REGATTA_ID}")
        return
    print(
        f"events: UPDATE event_id={event['event_id']} "
        f"source_event_id={event.get('source_event_id')} SET {', '.join(sets)}"
    )
    if not dry_run:
        args.append(event["event_id"])
        cur.execute(f"UPDATE events SET {', '.join(sets)} WHERE event_id = %s", tuple(args))


def main() -> int:
    parser = argparse.ArgumentParser(description="Match TSC 420 Nationals 2026 and create Event URL.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan; do not write.")
    args = parser.parse_args()
    if psycopg2 is None or RealDictCursor is None:
        print("ERROR: psycopg2 required. pip install psycopg2-binary", file=sys.stderr)
        return 1

    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        event = resolve_event(cur)
        tsc = resolve_tsc(cur)
        class_420 = resolve_class_420(cur)
        print("Matched events row:")
        print(f"  event_id={event['event_id']} name={event['event_name']!r}")
        print(f"  dates={event.get('start_date')} → {event.get('end_date')}")
        print(f"  source={event.get('source')}/{event.get('source_event_id')} {event.get('source_url')}")
        print(f"  venue={event.get('venue_raw')!r} host_raw={event.get('host_club_name_raw')!r}")
        print(f"  current regatta_id={event.get('regatta_id')!r}")
        print(f"Host: {tsc.get('club_abbrev')} ({tsc.get('club_fullname')}) club_id={tsc['club_id']}")
        print(f"Class: {class_420['class_name']!r} class_id={class_420['class_id']}")
        print(f"SAS: {SAS_URL}")
        print(f"Event URL: {EVENT_URL}")

        ensure_regatta(cur, tsc, class_420, args.dry_run)
        ensure_block(cur, class_420, args.dry_run)
        link_event(cur, event, tsc, args.dry_run)

        if args.dry_run:
            conn.rollback()
            print("DRY RUN — no writes. Re-run without --dry-run to apply.")
        else:
            conn.commit()
            print("Applied. Preload entries onto this Event URL when the list arrives.")
        print(EVENT_URL)
        return 0
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
