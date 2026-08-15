#!/usr/bin/env python3
"""
Make The North Sails J22 Championships live on SailingSA.

- regatta_id: 2026-08-16-2026-north-sails-j22-championships  (end_date + name)
- event_name: 2026 North Sails J22 Championships
- Lock events.event_id 169655 → regatta_id
- Header: left North Sails sponsor, right RCYC host
- Results line: Provisional as at 15 August 2026 at 17:25

Run on live:
  python3 /var/www/sailingsa/deploy/make_live_north_sails_j22_2026.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg2
from psycopg2.extras import RealDictCursor

ROOT = Path("/var/www/sailingsa")
DB_URL = os.environ.get(
    "DB_URL",
    "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master",
)

REGATTA_ID = "2026-08-16-2026-north-sails-j22-championships"
EVENT_ID = 169655
EVENT_NAME = "2026 North Sails J22 Championships"
START = "2026-08-15"
END = "2026-08-16"
AS_AT = datetime(2026, 8, 15, 17, 25, 0, tzinfo=ZoneInfo("Africa/Johannesburg"))
RESULT_STATUS = "Provisional"

LEFT_ICON = "/artwork/Sponsor Logo/North-Sails.png"
RIGHT_ICON = "/artwork/Club Logo/RCYC.png"

ICONS_PATHS = [
    ROOT / "data" / "wc_regatta_header_icons.json",  # STATIC_DIR/data — live API reads this
    ROOT / "wc_regatta_header_icons.json",
    ROOT / "static" / "data" / "wc_regatta_header_icons.json",
    ROOT / "deploy" / "wc_regatta_header_icons.json",
    ROOT / "api" / "wc_regatta_header_icons.json",
]
API_PY = ROOT / "api" / "api.py"

ICON_ENTRY = {
    "left": LEFT_ICON,
    "right": RIGHT_ICON,
    "show_fleet_header_logos": True,
    "fleet_logos": {"j22": "/artwork/Class Logo/J22-Class-Logo.png"},
    "fleet_logos_right": {"j22": "/artwork/Class Logo/J22-Class-Logo.png"},
}


def upsert_regatta(cur) -> None:
    cur.execute(
        """
        INSERT INTO regattas (
            regatta_id, event_name, year, start_date, end_date,
            result_status, as_at_time,
            host_club_id, host_club_code, host_club_name, province_code, province_name,
            class_layout, result_type, import_status,
            wc_header_left_icon_url, wc_header_right_icon_url,
            blank_hub_news_show_hero, updated_at
        ) VALUES (
            %s, %s, 2026, %s::date, %s::date,
            %s, %s,
            11, 'RCYC', 'Royal Cape Yacht Club', 'WC', 'Western Cape',
            'single', 'UNKNOWN', 'verified_shell',
            %s, %s,
            TRUE, NOW()
        )
        ON CONFLICT (regatta_id) DO UPDATE SET
            event_name = EXCLUDED.event_name,
            year = EXCLUDED.year,
            start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date,
            result_status = EXCLUDED.result_status,
            as_at_time = EXCLUDED.as_at_time,
            host_club_id = EXCLUDED.host_club_id,
            host_club_code = EXCLUDED.host_club_code,
            host_club_name = EXCLUDED.host_club_name,
            province_code = EXCLUDED.province_code,
            province_name = EXCLUDED.province_name,
            class_layout = EXCLUDED.class_layout,
            wc_header_left_icon_url = EXCLUDED.wc_header_left_icon_url,
            wc_header_right_icon_url = EXCLUDED.wc_header_right_icon_url,
            blank_hub_news_show_hero = EXCLUDED.blank_hub_news_show_hero,
            updated_at = NOW()
        """,
        (
            REGATTA_ID,
            EVENT_NAME,
            START,
            END,
            RESULT_STATUS,
            AS_AT,
            LEFT_ICON,
            RIGHT_ICON,
        ),
    )


def lock_event(cur) -> None:
    cur.execute(
        """
        UPDATE events
        SET regatta_id = %s,
            match_method = COALESCE(match_method, 'manual_lock'),
            match_score = COALESCE(match_score, 100),
            last_seen_at = NOW()
        WHERE event_id = %s
        """,
        (REGATTA_ID, EVENT_ID),
    )
    if cur.rowcount != 1:
        raise RuntimeError(f"event lock expected 1 row, got {cur.rowcount}")


def patch_icons_json() -> None:
    for path in ICONS_PATHS:
        if not path.is_file():
            print("skip missing", path)
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise RuntimeError(f"icons json not dict: {path}")
        if data.get(REGATTA_ID) != ICON_ENTRY:
            data[REGATTA_ID] = ICON_ENTRY
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            print("icons updated", path)
        else:
            print("icons ok", path)


def patch_api_custom_slugs() -> None:
    if not API_PY.is_file():
        print("skip api.py missing")
        return
    text = API_PY.read_text(encoding="utf-8")
    if "REGATTA_CUSTOM_HEADER_ICON_SLUGS" not in text:
        print("skip: REGATTA_CUSTOM_HEADER_ICON_SLUGS not in api.py")
        return
    # already present
    section = text.split("REGATTA_CUSTOM_HEADER_ICON_SLUGS", 1)[1].split(")", 1)[0]
    if REGATTA_ID in section:
        print("api slug already listed")
        return
    for anchor in (
        '"2026-07-26-brass-monkey-regatta",',
        '"2026-06-16-shane-s-gaul-regatta",',
        '"2026-06-15-kzn-505-regionals",',
    ):
        if anchor in text:
            text = text.replace(anchor, anchor + f'\n        "{REGATTA_ID}",', 1)
            API_PY.write_text(text, encoding="utf-8")
            print("api patched via", anchor.strip().strip(",").strip('"'))
            return
    # fallback: insert after frozenset((
    m = re.search(
        r"(REGATTA_CUSTOM_HEADER_ICON_SLUGS:\s*FrozenSet\[str\]\s*=\s*frozenset\(\s*\(\s*)",
        text,
    )
    if not m:
        print("WARN: could not patch api slug set", file=sys.stderr)
        return
    text = text[: m.end()] + f'"{REGATTA_ID}",\n        ' + text[m.end() :]
    API_PY.write_text(text, encoding="utf-8")
    print("api patched via frozenset head")


def main() -> int:
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    try:
        with conn.cursor() as cur:
            upsert_regatta(cur)
            lock_event(cur)
            cur.execute(
                """
                SELECT event_id, event_name, start_date, end_date, regatta_id
                FROM events WHERE event_id = %s
                """,
                (EVENT_ID,),
            )
            print("event", dict(cur.fetchone()))
            cur.execute(
                """
                SELECT regatta_id, event_name, start_date, end_date, result_status,
                       as_at_time, host_club_code, wc_header_left_icon_url, wc_header_right_icon_url
                FROM regattas WHERE regatta_id = %s
                """,
                (REGATTA_ID,),
            )
            print("regatta", dict(cur.fetchone()))
        conn.commit()
    finally:
        conn.close()

    patch_icons_json()
    patch_api_custom_slugs()
    print("URL https://sailingsa.co.za/regatta/" + REGATTA_ID)
    print("Restart API if api.py was patched: systemctl restart sailingsa-api")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
