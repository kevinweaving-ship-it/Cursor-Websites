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

# Sponsor-from-name: "North Sails" in event name → left header = Sponsor Logo
LEFT_ICON = "/artwork/Sponsor Logo/North-Sails.png"
RIGHT_ICON = "/artwork/Club Logo/RCYC.png"  # host club right

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


def upsert_j22_block(cur) -> None:
    """Fleet = J22; sailed line: 2 / 0 / 2 / 16 / Appendix A."""
    block_id = f"{REGATTA_ID}:j22"
    cur.execute(
        """
        INSERT INTO regatta_blocks (
            block_id, regatta_id, class_original, class_canonical, fleet_label,
            races_sailed, discard_count, to_count, scoring_system, class_id, entries_raced
        ) VALUES (
            %s, %s, 'J22', 'J22', 'J22',
            2, 0, 2, 'Appendix A', 48, 16
        )
        ON CONFLICT (block_id) DO UPDATE SET
            class_original = EXCLUDED.class_original,
            class_canonical = EXCLUDED.class_canonical,
            fleet_label = EXCLUDED.fleet_label,
            races_sailed = EXCLUDED.races_sailed,
            discard_count = EXCLUDED.discard_count,
            to_count = EXCLUDED.to_count,
            scoring_system = EXCLUDED.scoring_system,
            class_id = EXCLUDED.class_id,
            entries_raced = EXCLUDED.entries_raced
        """,
        (block_id, REGATTA_ID),
    )
    cur.execute(
        """
        UPDATE regattas
        SET scoring_system = 'Appendix A', class_layout = 'single', updated_at = NOW()
        WHERE regatta_id = %s
        """,
        (REGATTA_ID,),
    )


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 13:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def seed_rank_rows_1_to_16(cur) -> None:
    """Ranks 1st–16th with validated bow / sail / boat name from sheet."""
    from psycopg2.extras import Json

    block_id = f"{REGATTA_ID}:j22"
    sheet = [
        (1, "32", "1571", "Nitro Juice", "HYC", "Calvin Gibbs", "Markus Progli"),
        (2, "31", "774", "Nitro Maverick", "UCTYC", "Dale Rae", None),
        (3, "48", "1169", "Ullman Sails Camissa", "FBYC", "Henry Daniels", None),
        (4, "23", "763", "Phantom", "KYC", "Greg Davis", "Yogi Davaris"),
        (5, "34", "1116", "G'day J", "PYC", "Richard Weddell", None),
        (6, "49", "1175", "Nitro Monkey", "SBYC", "Stef Marcia", None),
        (7, "26", "766", "Amtec Racing", "RCYC", "Sean van Rensburg", None),
        (8, "28", "768", "Ullman Racing", "RNYC", "Mike Farrington", "Andrea Giovannini"),
        (9, "8", "173", "J-Walker", "RCYC Academy", "Sibu Sizatu", None),
        (10, "14", "185", "Andiamo", "GLYC", "Hamilton Slater", None),
        (11, "55", "1239", "CaCanny", "TSC", "Jimmy Jacka", None),
        (12, "52", "1277", "22-ATE", "WBYC", "Bjorn Geiger", None),
        (13, "63", "771", "Donna Mia Forever", "IZI", "Thando Mntambo", None),
        (14, "46", "1176", "Wildcard", "LDYC", "Aaron Biagio", "Henning Kock"),
        (15, "43", "1138", "Laugh a minute", "WYAC", "Travis Clack", None),
        (16, "51", "1237", "Attacke", "LYC", "Pascal Allers", None),
    ]
    cur.execute(
        "DELETE FROM results WHERE regatta_id = %s AND block_id = %s",
        (REGATTA_ID, block_id),
    )
    race_scores = {"R1": "", "R2": ""}
    for rank, bow, sail, boat, club_raw, helm, crew in sheet:
        cur.execute(
            """
            INSERT INTO results (
                regatta_id, block_id, rank, rank_ordinal,
                fleet_label, class_original, class_canonical, class_id,
                bow_no, sail_number, boat_name, club_raw,
                helm_name, crew_name,
                races_sailed, discard_count, race_scores,
                result_status, as_at_time
            ) VALUES (
                %s, %s, %s, %s,
                'J22', 'J22', 'J22', 48,
                %s, %s, %s, %s,
                %s, %s,
                2, 0, %s,
                'Provisional', %s
            )
            """,
            (
                REGATTA_ID,
                block_id,
                rank,
                _ordinal(rank),
                bow,
                sail,
                boat,
                club_raw,
                helm,
                crew,
                Json(race_scores),
                AS_AT,
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
            upsert_j22_block(cur)
            seed_rank_rows_1_to_16(cur)
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
