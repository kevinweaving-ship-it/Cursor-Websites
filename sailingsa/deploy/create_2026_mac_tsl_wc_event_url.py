#!/usr/bin/env python3
"""Create the MAC TSL WC Team Sailing Event URL (17–18 Oct 2026).

Gold slug (docs/CLUB_EVENT_LIVE_CARDS.md / docs/MAC_TSL_WC_2026_EVENT_URL.md):
  YYYY-MM-DD-{club}-{slug}
  https://sailingsa.co.za/regatta/2026-10-17-mac-tsl-wc-team-sailing

SAS: https://www.sailing.org.za/events/380433
Do not reuse March 328007 or July GLYC 370796.

Header (std gold): TSL event logo left · name/host/data centre · MAC club logo right.
Fleet: TSL logo + TSL Fleet + sailed line. Empty results until Saturday.
Do not change this slug after create. Entries/results update the fleet only.

  export DB_URL=...   # from sailingsa-api.service on live
  python3 sailingsa/deploy/create_2026_mac_tsl_wc_event_url.py --dry-run
  python3 sailingsa/deploy/create_2026_mac_tsl_wc_event_url.py
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

REGATTA_ID = "2026-10-17-mac-tsl-wc-team-sailing"
EVENT_NAME = "SA Sailing WC Team Sailing Event"
YEAR = 2026
START_DATE = date(2026, 10, 17)
END_DATE = date(2026, 10, 18)
SAS_EVENT_ID = "380433"
SAS_URL = "https://www.sailing.org.za/events/380433"
EVENT_URL = f"https://sailingsa.co.za/regatta/{REGATTA_ID}"
HOST_ABBREV = "MAC"
HOST_FULLNAME = "Milnerton Aquatic Club"
BLOCK_ID = f"{REGATTA_ID}:tsl"
PROVINCE = "WC"
CLASS_NAME = "TSL"
SCORING = "Team Racing"


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


def resolve_event(cur) -> dict | None:
    row = fetch_one(
        cur,
        """
        SELECT event_id, event_name, start_date, end_date, source, source_event_id,
               source_url, host_club_id, host_club_name_raw, venue_raw, regatta_id
        FROM events
        WHERE source_event_id = %s
           OR (lower(event_name) LIKE '%%team sailing%%'
               AND start_date = %s
               AND lower(COALESCE(venue_raw, host_club_name_raw, '')) LIKE '%%milnerton%%')
        ORDER BY CASE WHEN source_event_id = %s THEN 0 ELSE 1 END, event_id
        LIMIT 1
        """,
        (SAS_EVENT_ID, START_DATE, SAS_EVENT_ID),
    )
    return dict(row) if row else None


def ensure_event(cur, mac: dict, dry_run: bool) -> dict:
    existing = resolve_event(cur)
    if existing:
        return existing
    cols = ["event_name", "start_date", "end_date"]
    vals = [EVENT_NAME, START_DATE, END_DATE]
    if col_exists(cur, "events", "source"):
        cols.append("source")
        vals.append("sas")
    if col_exists(cur, "events", "source_event_id"):
        cols.append("source_event_id")
        vals.append(SAS_EVENT_ID)
    if col_exists(cur, "events", "source_url"):
        cols.append("source_url")
        vals.append(SAS_URL)
    if col_exists(cur, "events", "details_url"):
        cols.append("details_url")
        vals.append(SAS_URL)
    if col_exists(cur, "events", "venue_raw"):
        cols.append("venue_raw")
        vals.append("Milnerton Aquatic Club, 1 Grey Ave Bloubergstrand Cape Town")
    if col_exists(cur, "events", "host_club_id"):
        cols.append("host_club_id")
        vals.append(mac["club_id"])
    if col_exists(cur, "events", "host_club_name_raw"):
        cols.append("host_club_name_raw")
        vals.append(HOST_FULLNAME)
    if col_exists(cur, "events", "event_status"):
        cols.append("event_status")
        vals.append("upcoming")
    if col_exists(cur, "events", "event_year"):
        cols.append("event_year")
        vals.append(YEAR)
    if col_exists(cur, "events", "category"):
        cols.append("category")
        vals.append("Team Sailing Events")
    placeholders = ", ".join(["%s"] * len(cols))
    print(f"events: INSERT SAS {SAS_EVENT_ID} (not yet in scrape)")
    if dry_run:
        return {
            "event_id": None,
            "event_name": EVENT_NAME,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "source": "sas",
            "source_event_id": SAS_EVENT_ID,
            "source_url": SAS_URL,
            "host_club_id": mac["club_id"],
            "host_club_name_raw": HOST_FULLNAME,
            "venue_raw": HOST_FULLNAME,
            "regatta_id": None,
        }
    cur.execute(
        f"INSERT INTO events ({', '.join(cols)}) VALUES ({placeholders}) RETURNING event_id",
        tuple(vals),
    )
    new_id = cur.fetchone()["event_id"]
    row = resolve_event(cur) or {"event_id": new_id, "regatta_id": None, "source_event_id": SAS_EVENT_ID}
    return dict(row)


def resolve_mac(cur) -> dict:
    name_col = "club_fullname" if col_exists(cur, "clubs", "club_fullname") else "club_name"
    row = fetch_one(
        cur,
        f"""
        SELECT club_id, club_abbrev, {name_col} AS club_fullname
        FROM clubs
        WHERE upper(trim(club_abbrev)) = 'MAC'
           OR lower(trim({name_col})) = 'milnerton aquatic club'
        ORDER BY CASE WHEN upper(trim(club_abbrev)) = 'MAC' THEN 0 ELSE 1 END
        LIMIT 1
        """,
    )
    if not row:
        raise SystemExit("ERROR: MAC / Milnerton Aquatic Club not found in clubs.")
    return dict(row)


def resolve_class_tsl(cur) -> dict:
    row = fetch_one(
        cur,
        """
        SELECT class_id, class_name
        FROM classes
        WHERE lower(trim(class_name)) IN ('tsl', 'team sailing league', 'team sailing')
        ORDER BY CASE WHEN lower(trim(class_name)) = 'tsl' THEN 0 ELSE 1 END
        LIMIT 1
        """,
    )
    if row:
        return dict(row)
    print("WARN: class TSL not in classes — block will still use class_canonical='TSL' (no classes INSERT).")
    return {"class_id": None, "class_name": CLASS_NAME}


def next_regatta_number(cur) -> int:
    cur.execute(
        "SELECT COALESCE(MAX(regatta_number), 0) + 1 AS next_num FROM regattas WHERE regatta_number IS NOT NULL"
    )
    row = cur.fetchone()
    if isinstance(row, dict):
        return int(row["next_num"])
    return int(row[0])


def ensure_regatta(cur, mac: dict, dry_run: bool) -> str:
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
        "host_club_id",
        "import_status",
    ]
    vals = [
        REGATTA_ID,
        EVENT_NAME,
        YEAR,
        START_DATE,
        END_DATE,
        mac["club_id"],
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
        vals.append(mac.get("club_fullname") or HOST_FULLNAME)
    if col_exists(cur, "regattas", "province_name"):
        cols.append("province_name")
        vals.append(PROVINCE)
    if col_exists(cur, "regattas", "source_url"):
        cols.append("source_url")
        vals.append(SAS_URL)
    # No result_status / as_at_time until racing — omit the status line.

    placeholders = ", ".join(["%s"] * len(cols))
    print(f"regattas: INSERT {REGATTA_ID} number={number} host=MAC")
    if not dry_run:
        cur.execute(
            f"INSERT INTO regattas ({', '.join(cols)}) VALUES ({placeholders})",
            tuple(vals),
        )
    return REGATTA_ID


def ensure_block(cur, class_tsl: dict, dry_run: bool) -> None:
    existing = fetch_one(
        cur,
        "SELECT block_id FROM regatta_blocks WHERE block_id = %s OR (regatta_id = %s AND lower(trim(COALESCE(class_canonical, class_original, ''))) = 'tsl')",
        (BLOCK_ID, REGATTA_ID),
    )
    if existing:
        print(f"regatta_blocks: already present {existing['block_id']}")
        return

    class_name = (class_tsl.get("class_name") or CLASS_NAME).strip()
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
        vals.append(SCORING)
    if col_exists(cur, "regatta_blocks", "handicap_system"):
        cols.append("handicap_system")
        vals.append(SCORING)
    if col_exists(cur, "regatta_blocks", "class_id") and class_tsl.get("class_id") is not None:
        cols.append("class_id")
        vals.append(class_tsl["class_id"])
    if col_exists(cur, "regatta_blocks", "entries_raced"):
        cols.append("entries_raced")
        vals.append(0)
    if col_exists(cur, "regatta_blocks", "block_label_raw"):
        cols.append("block_label_raw")
        vals.append("TSL")

    placeholders = ", ".join(["%s"] * len(cols))
    print(f"regatta_blocks: INSERT {BLOCK_ID} class={class_name} scoring={SCORING}")
    if not dry_run:
        cur.execute(
            f"INSERT INTO regatta_blocks ({', '.join(cols)}) VALUES ({placeholders})",
            tuple(vals),
        )


def link_event(cur, event: dict, mac: dict, dry_run: bool) -> None:
    if event.get("event_id") is None:
        print("events: dry-run placeholder — no event_id to link")
        return
    sets = []
    args = []
    if (event.get("regatta_id") or "").strip() != REGATTA_ID:
        sets.append("regatta_id = %s")
        args.append(REGATTA_ID)
    if event.get("host_club_id") != mac["club_id"]:
        sets.append("host_club_id = %s")
        args.append(mac["club_id"])
    if col_exists(cur, "events", "host_club_name_raw"):
        raw = (event.get("host_club_name_raw") or "").strip()
        if "milnerton" not in raw.lower() and "mac" not in raw.lower():
            sets.append("host_club_name_raw = %s")
            args.append(HOST_FULLNAME)
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
    parser = argparse.ArgumentParser(description="Create MAC TSL WC 2026 Event URL.")
    parser.add_argument("--dry-run", action="store_true", help="Print plan; do not write.")
    args = parser.parse_args()
    if psycopg2 is None or RealDictCursor is None:
        print("ERROR: psycopg2 required. pip install psycopg2-binary", file=sys.stderr)
        return 1

    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        mac = resolve_mac(cur)
        class_tsl = resolve_class_tsl(cur)
        event = ensure_event(cur, mac, args.dry_run)
        print("Matched events row:")
        print(f"  event_id={event.get('event_id')} name={event.get('event_name')!r}")
        print(f"  dates={event.get('start_date')} → {event.get('end_date')}")
        print(f"  source={event.get('source')}/{event.get('source_event_id')} {event.get('source_url')}")
        print(f"  venue={event.get('venue_raw')!r} host_raw={event.get('host_club_name_raw')!r}")
        print(f"  current regatta_id={event.get('regatta_id')!r}")
        print(f"Host: {mac.get('club_abbrev')} ({mac.get('club_fullname')}) club_id={mac['club_id']}")
        print(f"Class: {class_tsl['class_name']!r} class_id={class_tsl.get('class_id')}")
        print(f"SAS: {SAS_URL}")
        print(f"Event URL: {EVENT_URL}")
        print("Header: TSL logo left · event data centre · MAC logo right. No Venue (same club).")
        print("Fleet: TSL Fleet · Sailed: 0 · Scoring: Team Racing · empty table until Saturday.")

        ensure_regatta(cur, mac, args.dry_run)
        ensure_block(cur, class_tsl, args.dry_run)
        link_event(cur, event, mac, args.dry_run)

        if args.dry_run:
            conn.rollback()
            print("DRY RUN — no writes. Re-run without --dry-run to apply.")
        else:
            conn.commit()
            print("Applied. Seed teams onto this Event URL; admin enters race W/L live.")
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
