#!/usr/bin/env python3
"""Seed the three known TSL teams. Existing SAS IDs only. No invented pairings.

  MAC — keep verified boat pairings
  MATIES (USYC) — three helms, crews unassigned
  Eden District (GLYC) — six sailors unassigned

  export DB_URL=...
  python3 sailingsa/deploy/seed_mac_tsl_known_teams.py --dry-run
  python3 sailingsa/deploy/seed_mac_tsl_known_teams.py
"""
from __future__ import annotations

import argparse
import os
import sys

try:
    import psycopg2
    from psycopg2.extras import Json, RealDictCursor
except ImportError:
    psycopg2 = None
    Json = None
    RealDictCursor = None

REGATTA_ID = "2026-10-17-mac-tsl-wc-team-sailing"
BLOCK_ID = f"{REGATTA_ID}:tsl"
CLASS_NAME = "TSL"
CLASS_ID = 148

MAC_BOATS = (
    (1, "13516", "21052"),
    (2, "8612", "29414"),
    (3, "13517", "22974"),
)
MATIES_HELMS = ("20389", "8178", "6497")
EDEN_SAILORS = ("15711", "13488", "27609", "27610", "23531", "28588")


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


def display_name(row: dict) -> str:
    first = (row.get("first_name") or "").strip()
    last = (row.get("last_name") or "").strip()
    joined = f"{first} {last}".strip()
    return joined or (row.get("full_name") or "").strip()


def load_sailor(cur, sas_id: str):
    cur.execute(
        """
        SELECT sa_sailing_id, full_name, first_name, last_name, club_1, primary_club
        FROM sas_id_personal
        WHERE sa_sailing_id::text = %s
        LIMIT 1
        """,
        (sas_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def club_by_abbrev(cur, abbrev: str) -> dict:
    cur.execute(
        """
        SELECT club_id, club_abbrev, club_fullname
        FROM clubs
        WHERE upper(club_abbrev) = upper(%s)
        LIMIT 1
        """,
        (abbrev,),
    )
    row = cur.fetchone()
    if not row:
        raise SystemExit(f"ERROR: club {abbrev} missing")
    return dict(row)


def upsert_team(cur, club: dict, team_name: str, team_abbrev: str, sort_order: int, boats: list) -> tuple:
    cur.execute(
        """
        INSERT INTO tsl_event_teams (regatta_id, club_id, team_name, team_abbrev, sort_order)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (regatta_id, team_name)
        DO UPDATE SET club_id = EXCLUDED.club_id, team_abbrev = COALESCE(EXCLUDED.team_abbrev, tsl_event_teams.team_abbrev)
        RETURNING team_id, result_id
        """,
        (REGATTA_ID, int(club["club_id"]), team_name, team_abbrev, sort_order),
    )
    team = dict(cur.fetchone())
    team_id = int(team["team_id"])
    for n in range(1, 4):
        b = next((x for x in boats if int(x["boat_no"]) == n), {"boat_no": n, "helm": None, "crew": None})
        helm_id = b["helm"]["sa_sailing_id"] if b.get("helm") else None
        crew_id = b["crew"]["sa_sailing_id"] if b.get("crew") else None
        cur.execute(
            """
            INSERT INTO tsl_event_team_boats (team_id, boat_no, helm_sas_id, crew_sas_id)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (team_id, boat_no)
            DO UPDATE SET helm_sas_id = EXCLUDED.helm_sas_id, crew_sas_id = EXCLUDED.crew_sas_id
            """,
            (team_id, n, helm_id, crew_id),
        )
    helm_names = "; ".join(display_name(b["helm"]) for b in boats if b.get("helm"))
    crew_names = "; ".join(display_name(b["crew"]) for b in boats if b.get("crew"))
    first_helm = next((b["helm"]["sa_sailing_id"] for b in boats if b.get("helm")), None)
    first_crew = next((b["crew"]["sa_sailing_id"] for b in boats if b.get("crew")), None)
    cols = {
        "regatta_id": REGATTA_ID,
        "block_id": BLOCK_ID,
        "class_original": CLASS_NAME,
        "boat_name": team_name,
        "club_id": int(club["club_id"]),
        "club_raw": club["club_abbrev"],
        "helm_name": helm_names,
        "crew_name": crew_names,
        "race_scores": Json({}),
        "races_sailed": 0,
        "ranks_sailed": 0,
        "discard_count": 0,
        "manually_parsed": False,
    }
    if col_exists(cur, "results", "class_canonical"):
        cols["class_canonical"] = CLASS_NAME
    if col_exists(cur, "results", "class_id"):
        cols["class_id"] = CLASS_ID
    if col_exists(cur, "results", "raced"):
        cols["raced"] = False
    if first_helm and str(first_helm).isdigit():
        cols["helm_sa_sailing_id"] = int(first_helm)
    if first_crew and str(first_crew).isdigit():
        cols["crew_sa_sailing_id"] = int(first_crew)

    cur.execute(
        """
        SELECT result_id FROM results
        WHERE regatta_id = %s AND block_id = %s
          AND (boat_name = %s OR result_id = %s)
        ORDER BY result_id
        LIMIT 1
        """,
        (REGATTA_ID, BLOCK_ID, team_name, team.get("result_id")),
    )
    existing = cur.fetchone()
    if existing:
        result_id = int(existing["result_id"])
        sets = ", ".join(f"{k} = %s" for k in cols)
        cur.execute(f"UPDATE results SET {sets} WHERE result_id = %s", list(cols.values()) + [result_id])
        action = "UPDATE"
    else:
        names = ", ".join(cols)
        placeholders = ", ".join(["%s"] * len(cols))
        cur.execute(f"INSERT INTO results ({names}) VALUES ({placeholders}) RETURNING result_id", list(cols.values()))
        result_id = int(cur.fetchone()["result_id"])
        action = "INSERT"
    cur.execute("UPDATE tsl_event_teams SET result_id = %s WHERE team_id = %s", (result_id, team_id))
    print(f"OK {team_name} team_id={team_id} result_id={result_id} {action}")
    return team_id, result_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if psycopg2 is None:
        print("ERROR: psycopg2 required", file=sys.stderr)
        return 2

    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("SELECT block_id FROM regatta_blocks WHERE block_id = %s", (BLOCK_ID,))
        if not cur.fetchone():
            raise SystemExit(f"ERROR: block {BLOCK_ID} missing")

        mac = club_by_abbrev(cur, "MAC")
        usyc = club_by_abbrev(cur, "USYC")
        glyc = club_by_abbrev(cur, "GLYC")

        mac_boats = []
        for boat_no, helm_id, crew_id in MAC_BOATS:
            helm = load_sailor(cur, helm_id)
            crew = load_sailor(cur, crew_id)
            if not helm or not crew:
                raise SystemExit(f"ERROR: MAC boat {boat_no} sailor missing")
            mac_boats.append({"boat_no": boat_no, "helm": helm, "crew": crew})
            print(f"MAC {boat_no}: {display_name(helm)} {helm_id} / {display_name(crew)} {crew_id}")

        maties_boats = []
        for i, hid in enumerate(MATIES_HELMS, start=1):
            helm = load_sailor(cur, hid)
            if not helm:
                print(f"SKIP Maties helm SAS {hid} — not in sas_id_personal")
                continue
            maties_boats.append({"boat_no": i, "helm": helm, "crew": None})
            print(f"MATIES helm {i}: {display_name(helm)} {hid} (crew unassigned)")

        print("Eden sailors (unassigned):")
        for sid in EDEN_SAILORS:
            row = load_sailor(cur, sid)
            print(f"  {sid} {display_name(row) if row else 'NOT IN DB — not invented'}")

        if args.dry_run:
            print("dry-run: no writes")
            return 0

        upsert_team(cur, mac, "MAC", "MAC", 1, mac_boats)
        upsert_team(cur, usyc, "MATIES", "MATIES", 2, maties_boats)
        upsert_team(cur, glyc, "Eden District", "EDEN", 3, [])
        conn.commit()
        return 0
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
