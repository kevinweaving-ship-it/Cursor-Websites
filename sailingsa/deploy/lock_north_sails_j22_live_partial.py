#!/usr/bin/env python3
"""Lock validated North Sails J22 2026 live result rows (scores still open).

Live multi-day event: more racing to come. Identity / entry fields are checked
and CLOSED — do not re-validate or rewrite them. Scores / total / nett stay OPEN.

LOCKED (override only with explicit user instruction):
  bow_no, sail_number, boat_name, boat_id,
  club_raw, club_id,
  helm_name, helm_sa_sailing_id, helm_temp_id, match_status_helm,
  crew_name, crew_sa_sailing_id, crew_temp_id, match_status_crew,
  class_canonical, class_original, class_id, fleet_label, block_id

OPEN (update as races complete):
  race_scores, total_points_raw, nett_points_raw,
  rank, rank_ordinal, races_sailed, discard_count,
  result_status / as_at_time (regatta + rows as needed)

Markers on each results row:
  validation_flag      = LIVE_PARTIAL_LOCK
  race_updated_status  = Provisional
  row_validation_status = validated
  manually_parsed      = true
  source_row_text      = lock manifest (human + agent readable)

Regatta:
  import_status = live_locked_scores_open
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.environ.get(
    "DB_URL",
    "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master",
)
RID = "2026-08-16-2026-north-sails-j22-championships"

LOCKED_FIELDS = [
    "bow_no",
    "sail_number",
    "boat_name",
    "boat_id",
    "club_raw",
    "club_id",
    "helm_name",
    "helm_sa_sailing_id",
    "helm_temp_id",
    "match_status_helm",
    "crew_name",
    "crew_sa_sailing_id",
    "crew_temp_id",
    "match_status_crew",
    "class_canonical",
    "class_original",
    "class_id",
    "fleet_label",
    "block_id",
]
OPEN_FIELDS = [
    "race_scores",
    "total_points_raw",
    "nett_points_raw",
    "rank",
    "rank_ordinal",
    "races_sailed",
    "discard_count",
]


def main() -> None:
    locked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manifest = {
        "lock": "LIVE_PARTIAL_LOCK",
        "regatta_id": RID,
        "locked_at": locked_at,
        "reason": "live_multi_day; identity_entry_validated; more_racing_to_come",
        "locked_fields": LOCKED_FIELDS,
        "open_fields": OPEN_FIELDS,
        "do_not_revalidate_locked": True,
    }
    manifest_text = "LIVE_PARTIAL_LOCK " + json.dumps(manifest, separators=(",", ":"))

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        UPDATE results
        SET validation_flag = %s,
            race_updated_status = %s,
            row_validation_status = %s,
            manually_parsed = TRUE,
            source_row_text = %s,
            identity_status = CASE
              WHEN helm_sa_sailing_id IS NOT NULL THEN COALESCE(identity_status, 'IDENTITY_OK')
              WHEN match_status_helm = 'name_only_no_sas' THEN 'NAME_ONLY_CONFIRMED'
              ELSE identity_status
            END
        WHERE regatta_id = %s
        RETURNING result_id, rank, sail_number, helm_name, validation_flag,
                  race_updated_status, match_status_helm, match_status_crew
        """,
        (
            "LIVE_PARTIAL_LOCK",
            "Provisional",
            "validated",
            manifest_text,
            RID,
        ),
    )
    rows = cur.fetchall()

    cur.execute(
        """
        UPDATE regattas
        SET import_status = %s,
            updated_at = NOW()
        WHERE regatta_id = %s
        RETURNING regatta_id, import_status, result_status, as_at_time
        """,
        ("live_locked_scores_open", RID),
    )
    reg = cur.fetchone()
    conn.commit()

    print(f"locked_rows={len(rows)} regatta={dict(reg) if reg else None}")
    for r in rows:
        print(
            f"  rank={r['rank']} sail={r['sail_number']} helm={r['helm_name']} "
            f"flag={r['validation_flag']} race_status={r['race_updated_status']} "
            f"helm_match={r['match_status_helm']} crew_match={r['match_status_crew']}"
        )
    print("LOCKED:", ", ".join(LOCKED_FIELDS))
    print("OPEN:", ", ".join(OPEN_FIELDS))
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
