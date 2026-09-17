#!/usr/bin/env python3
"""Create Midmar Cup Event URL (gold, Hunter 19 fleet) and list it Upcoming on HMYC.

Idempotent. Live-only: inserts/updates DB and patches upcoming Event URL links.
Entries list is not invented — left empty until supplied.
"""
from pathlib import Path
import shutil
import time

import psycopg2
import psycopg2.extras

API = Path("/var/www/sailingsa/api/api.py")
MARK = "MIDMAR_CUP_EVENT_URL_v1"
DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"

RID = "2026-09-19-hmyc-midmar-cup"
BLOCK = "2026-09-19-hmyc-midmar-cup:hunter-19"
EVENT_ID = 139940
CLUB_ID = 98

DETAILS_OLD = """    if is_upcoming:
        details_url = source_url if source_url else ""
"""

DETAILS_NEW = """    if is_upcoming:
        # MIDMAR_CUP_EVENT_URL_v1: Upcoming Details → Event URL when linked.
        reg_id = (r.get("regatta_id") or "").strip() if has_regatta_id else ""
        details_url = ("/regatta/" + reg_id) if reg_id else (source_url or "")
"""

CLUB_OLD = """        if not allow_regatta_links:
            # Upcoming: never deep-link into /regatta/.
            if rurl.startswith("/regatta/"):
                rurl = ""
            if details.startswith("/regatta/"):
                details = ""
"""

CLUB_NEW = """        if not allow_regatta_links:
            # MIDMAR_CUP_EVENT_URL_v1: keep Event URL when a linked regatta exists.
            _rid = str(c.get("regatta_id") or "").strip()
            if rurl.startswith("/regatta/"):
                rurl = ""
            if details.startswith("/regatta/") and not _rid:
                details = ""
"""


def apply_sql() -> None:
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO regattas (
            regatta_id, event_name, year,
            host_club_id, host_club_code, host_club_name,
            province_code, start_date, end_date,
            result_status, result_type, class_layout,
            scoring_system, scoring_mode, fleet_classes,
            source_url, import_status, provenance_status, manually_parsed
        ) VALUES (
            %s, 'The Midmar Cup', 2026,
            %s, 'HMYC', 'Henley Midmar Yacht Club',
            'KZN', DATE '2026-09-19', DATE '2026-09-20',
            'Provisional', 'LOW_POINT', 'single',
            'Appendix A', 'appendix_a_low_point', 'Hunter 19',
            'https://www.hmyc.org.za/events/326017',
            'pending', 'manual', TRUE
        )
        ON CONFLICT (regatta_id) DO UPDATE SET
            event_name = EXCLUDED.event_name,
            year = EXCLUDED.year,
            host_club_id = EXCLUDED.host_club_id,
            host_club_code = EXCLUDED.host_club_code,
            host_club_name = EXCLUDED.host_club_name,
            province_code = EXCLUDED.province_code,
            start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date,
            result_status = EXCLUDED.result_status,
            result_type = EXCLUDED.result_type,
            class_layout = EXCLUDED.class_layout,
            scoring_system = EXCLUDED.scoring_system,
            scoring_mode = EXCLUDED.scoring_mode,
            fleet_classes = EXCLUDED.fleet_classes,
            source_url = EXCLUDED.source_url,
            updated_at = now()
        """,
        (RID, CLUB_ID),
    )
    print("REGATTA", cur.rowcount)

    cur.execute(
        """
        INSERT INTO regatta_blocks (
            block_id, regatta_id, class_original, class_canonical,
            class_id, races_sailed, discard_count, to_count, scoring_system,
            entries_raced, entries_closed
        ) VALUES (
            %s, %s, 'Hunter 19', 'Hunter 19',
            209, 0, 0, 0, 'Appendix A',
            0, FALSE
        )
        ON CONFLICT (block_id) DO UPDATE SET
            class_original = EXCLUDED.class_original,
            class_canonical = EXCLUDED.class_canonical,
            class_id = EXCLUDED.class_id,
            scoring_system = EXCLUDED.scoring_system,
            entries_raced = EXCLUDED.entries_raced
        """,
        (BLOCK, RID),
    )
    print("BLOCK", cur.rowcount)

    cur.execute(
        """
        UPDATE events
        SET host_club_id = %s,
            regatta_id = %s
        WHERE event_id = %s
        """,
        (CLUB_ID, RID, EVENT_ID),
    )
    print("EVENT", cur.rowcount)

    cur.execute(
        """
        INSERT INTO event_regatta_links (
            event_id, regatta_id, match_score, match_reason, match_source
        )
        SELECT %s, %s, 100, 'midmar_cup_2026_event_url', 'manual'
        WHERE NOT EXISTS (
            SELECT 1 FROM event_regatta_links
            WHERE event_id = %s AND regatta_id = %s
        )
        """,
        (EVENT_ID, RID, EVENT_ID, RID),
    )
    print("LINK", cur.rowcount)
    conn.commit()
    cur.close()
    conn.close()


def apply_api() -> None:
    api = API.read_text()
    if MARK in api and DETAILS_NEW in api and CLUB_NEW in api:
        print("API_ALREADY")
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_name(f"api.py.bak.midmar_cup.{ts}"))
    missing = []
    if DETAILS_OLD not in api:
        missing.append("DETAILS")
    if CLUB_OLD not in api:
        missing.append("CLUB")
    if missing:
        raise SystemExit("MISSING:" + ",".join(missing))
    api = api.replace(DETAILS_OLD, DETAILS_NEW, 1)
    api = api.replace(CLUB_OLD, CLUB_NEW, 1)
    API.write_text(api)
    print("API_OK", MARK)


def main() -> None:
    apply_sql()
    apply_api()


if __name__ == "__main__":
    main()
