#!/usr/bin/env python3
"""Seed the MAC TSL master roster from existing sas_id_personal rows.

Verified sailors only (no invented SAS IDs):

  Boat  Helm                 Crew
  1     Kamva Mgcubhe 13516  Maddison Smit 21052
  2     Tristan Gress 8612   Thandokazi Sibanyoni 29414
  3     Unam Lubhelwana 13517 Alexa Aab 22974

One public.results row (one team = one entry). Boat pairings in
tsl_event_teams / tsl_event_team_boats. Idempotent.

  export DB_URL=postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master
  python3 sailingsa/deploy/seed_mac_tsl_mac_team_roster.py --dry-run
  python3 sailingsa/deploy/seed_mac_tsl_mac_team_roster.py
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
TEAM_NAME = "MAC"
CLUB_ABBREV = "MAC"
CLASS_NAME = "TSL"
CLASS_ID = 148

# User roster. SAS IDs resolved from sas_id_personal on live (2026-10-12).
BOATS = (
    (1, "13516", "21052"),  # Kamva Mgcubhe / Maddison Smit
    (2, "8612", "29414"),  # Tristan Gress / Thandokazi Sibanyoni
    (3, "13517", "22974"),  # Unam Lubhelwana / Alexa Aab
)

TEAMS_DDL = """
CREATE TABLE IF NOT EXISTS public.tsl_event_teams (
  team_id bigserial PRIMARY KEY,
  regatta_id text NOT NULL,
  club_id integer NOT NULL REFERENCES public.clubs(club_id),
  team_name text NOT NULL,
  result_id bigint,
  sort_order integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (regatta_id, team_name)
);
CREATE TABLE IF NOT EXISTS public.tsl_event_team_boats (
  team_id bigint NOT NULL REFERENCES public.tsl_event_teams(team_id) ON DELETE CASCADE,
  boat_no smallint NOT NULL CHECK (boat_no BETWEEN 1 AND 3),
  helm_sas_id text NOT NULL,
  crew_sas_id text NOT NULL,
  PRIMARY KEY (team_id, boat_no)
);
"""


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
    if joined:
        return joined
    return (row.get("full_name") or "").strip()


def load_sailor(cur, sas_id: str) -> dict:
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
    if not row:
        raise SystemExit(f"ERROR: SAS {sas_id} not in sas_id_personal")
    return dict(row)


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
        cur.execute(
            "SELECT club_id, club_abbrev, club_fullname FROM clubs WHERE upper(club_abbrev) = 'MAC' LIMIT 1"
        )
        club = cur.fetchone()
        if not club:
            raise SystemExit("ERROR: MAC club missing")
        club_id = int(club["club_id"])

        cur.execute("SELECT block_id FROM regatta_blocks WHERE block_id = %s", (BLOCK_ID,))
        if not cur.fetchone():
            raise SystemExit(f"ERROR: block {BLOCK_ID} missing")

        boats = []
        for boat_no, helm_id, crew_id in BOATS:
            helm = load_sailor(cur, helm_id)
            crew = load_sailor(cur, crew_id)
            boats.append(
                {
                    "boat_no": boat_no,
                    "helm": helm,
                    "crew": crew,
                    "helm_name": display_name(helm),
                    "crew_name": display_name(crew),
                }
            )
            print(
                f"boat {boat_no}: {display_name(helm)} {helm_id} / {display_name(crew)} {crew_id}"
                f" (helm club={helm.get('primary_club') or helm.get('club_1') or '—'},"
                f" crew club={crew.get('primary_club') or crew.get('club_1') or '—'})"
            )

        helm_names = "; ".join(b["helm_name"] for b in boats)
        crew_names = "; ".join(b["crew_name"] for b in boats)
        first_helm = boats[0]["helm"]["sa_sailing_id"]
        first_crew = boats[0]["crew"]["sa_sailing_id"]

        if args.dry_run:
            print(f"dry-run: team={TEAM_NAME} club_id={club_id} helms={helm_names!r} crews={crew_names!r}")
            return 0

        cur.execute(TEAMS_DDL)

        cur.execute(
            """
            INSERT INTO tsl_event_teams (regatta_id, club_id, team_name, sort_order)
            VALUES (%s, %s, %s, 1)
            ON CONFLICT (regatta_id, team_name)
            DO UPDATE SET club_id = EXCLUDED.club_id
            RETURNING team_id, result_id
            """,
            (REGATTA_ID, club_id, TEAM_NAME),
        )
        team = cur.fetchone()
        team_id = int(team["team_id"])
        result_id = team.get("result_id")

        for b in boats:
            cur.execute(
                """
                INSERT INTO tsl_event_team_boats (team_id, boat_no, helm_sas_id, crew_sas_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (team_id, boat_no)
                DO UPDATE SET helm_sas_id = EXCLUDED.helm_sas_id, crew_sas_id = EXCLUDED.crew_sas_id
                """,
                (team_id, b["boat_no"], b["helm"]["sa_sailing_id"], b["crew"]["sa_sailing_id"]),
            )

        cur.execute(
            """
            SELECT result_id FROM results
            WHERE regatta_id = %s AND block_id = %s
              AND (boat_name = %s OR result_id = %s)
            ORDER BY result_id
            LIMIT 1
            """,
            (REGATTA_ID, BLOCK_ID, TEAM_NAME, result_id),
        )
        existing = cur.fetchone()

        cols = {
            "regatta_id": REGATTA_ID,
            "block_id": BLOCK_ID,
            "class_original": CLASS_NAME,
            "boat_name": TEAM_NAME,
            "club_id": club_id,
            "club_raw": CLUB_ABBREV,
            "helm_name": helm_names,
            "crew_name": crew_names,
            "helm_sa_sailing_id": int(first_helm),
            "crew_sa_sailing_id": int(first_crew),
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

        if existing:
            result_id = int(existing["result_id"])
            sets = ", ".join(f"{k} = %s" for k in cols)
            cur.execute(
                f"UPDATE results SET {sets} WHERE result_id = %s",
                list(cols.values()) + [result_id],
            )
            print(f"results: UPDATE result_id={result_id}")
        else:
            names = ", ".join(cols)
            placeholders = ", ".join(["%s"] * len(cols))
            cur.execute(
                f"INSERT INTO results ({names}) VALUES ({placeholders}) RETURNING result_id",
                list(cols.values()),
            )
            result_id = int(cur.fetchone()["result_id"])
            print(f"results: INSERT result_id={result_id}")

        cur.execute(
            "UPDATE tsl_event_teams SET result_id = %s WHERE team_id = %s",
            (result_id, team_id),
        )
        conn.commit()
        print(f"OK team_id={team_id} result_id={result_id} {TEAM_NAME}")
        return 0
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
