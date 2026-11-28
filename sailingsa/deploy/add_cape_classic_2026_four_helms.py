#!/usr/bin/env python3
"""Add 4 Cape Classic 2026 helms and refresh fleet entry counts / ranks.

ILCA 4.7: Dwayne McCombe 144417, Nathan McCombe 191082
Optimist A: Maximus Taylor 1261, Bastien Taylor 1400
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras

REGATTA_ID = "2026-09-13-zvyc-cape-classic"
ILCA_BLOCK = f"{REGATTA_ID}:ilca-4.7-fleet"
OPTI_BLOCK = f"{REGATTA_ID}:optimist-a-fleet"
RACE_SCORES = {"R1": "", "R2": "", "R3": "", "R4": "", "R5": ""}

NEW_HELMS = [
    {
        "helm_name": "Dwayne McCombe",
        "sa_id": 25013,
        "sail": "144417",
        "club": "HYC",
        "club_id": 10,
        "block_id": ILCA_BLOCK,
        "fleet_label": "ILCA 4.7",
        "class_original": "ILCA 4.7",
        "class_canonical": "Ilca 4.7",
        "class_id": 8,
    },
    {
        "helm_name": "Nathan McCombe",
        "sa_id": 21517,
        "sail": "191082",
        "club": "HYC",
        "club_id": 10,
        "block_id": ILCA_BLOCK,
        "fleet_label": "ILCA 4.7",
        "class_original": "ILCA 4.7",
        "class_canonical": "Ilca 4.7",
        "class_id": 8,
    },
    {
        "helm_name": "Maximus Taylor",
        "sa_id": 26381,
        "sail": "1261",
        "club": "HYC",
        "club_id": 10,
        "block_id": OPTI_BLOCK,
        "fleet_label": "Optimist",
        "class_original": "Optimist A",
        "class_canonical": "Optimist A",
        "class_id": 62,
    },
    {
        "helm_name": "Bastien Taylor",
        "sa_id": 26382,
        "sail": "1400",
        "club": "HYC",
        "club_id": 10,
        "block_id": OPTI_BLOCK,
        "fleet_label": "Optimist",
        "class_original": "Optimist A",
        "class_canonical": "Optimist A",
        "class_id": 62,
    },
]


def db_url() -> str:
    text = Path("/etc/systemd/system/sailingsa-api.service").read_text()
    m = re.search(r"DB_URL=([^\s]+)", text)
    return (m.group(1) if m else "").strip().strip("\"'")


def rerank_and_count(cur, block_id: str) -> int:
    cur.execute(
        """
        SELECT result_id, helm_name
        FROM results
        WHERE block_id = %s
        ORDER BY lower(helm_name), result_id
        """,
        (block_id,),
    )
    rows = cur.fetchall()
    for i, row in enumerate(rows, start=1):
        cur.execute("UPDATE results SET rank = %s WHERE result_id = %s", (i, row["result_id"]))
    n = len(rows)
    cur.execute(
        "UPDATE regatta_blocks SET entries_raced = %s WHERE block_id = %s",
        (n, block_id),
    )
    return n


def main() -> int:
    now = datetime.now(timezone.utc).astimezone()
    conn = psycopg2.connect(db_url())
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS results_bak_cape_classic_20260912_entries
            AS SELECT * FROM results WHERE false
            """
        )
        added = []
        skipped = []
        for p in NEW_HELMS:
            cur.execute(
                """
                SELECT result_id, helm_name, sail_number, class_canonical, block_id
                FROM results
                WHERE regatta_id = %s
                  AND (
                    helm_sa_sailing_id = %s
                    OR lower(helm_name) = lower(%s)
                  )
                """,
                (REGATTA_ID, p["sa_id"], p["helm_name"]),
            )
            hit = cur.fetchone()
            if hit:
                skipped.append((p["helm_name"], dict(hit)))
                continue
            cur.execute(
                """
                INSERT INTO results (
                    regatta_id, block_id, rank,
                    fleet_label, class_original, class_canonical, class_id,
                    sail_number, club_raw, club_id,
                    helm_name, helm_sa_sailing_id,
                    races_sailed, discard_count, race_scores,
                    raced, result_status, as_at_time,
                    row_validation_status, manually_parsed, ranks_sailed
                ) VALUES (
                    %s, %s, 0,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    0, 0, %s,
                    true, 'Provisional', %s,
                    'validated', false, 0
                )
                RETURNING result_id
                """,
                (
                    REGATTA_ID,
                    p["block_id"],
                    p["fleet_label"],
                    p["class_original"],
                    p["class_canonical"],
                    p["class_id"],
                    p["sail"],
                    p["club"],
                    p["club_id"],
                    p["helm_name"],
                    p["sa_id"],
                    psycopg2.extras.Json(RACE_SCORES),
                    now,
                ),
            )
            rid = cur.fetchone()["result_id"]
            cur.execute(
                """
                INSERT INTO results_bak_cape_classic_20260912_entries
                SELECT * FROM results WHERE result_id = %s
                """,
                (rid,),
            )
            added.append((p["helm_name"], rid, p["block_id"], p["sail"]))

        ilca_n = rerank_and_count(cur, ILCA_BLOCK)
        opti_n = rerank_and_count(cur, OPTI_BLOCK)
        conn.commit()

        print("ADDED")
        for row in added:
            print(" ", row)
        print("SKIPPED")
        for row in skipped:
            print(" ", row)
        print("COUNTS", {"ilca-4.7": ilca_n, "optimist-a": opti_n})

        print("\nILCA 4.7")
        cur.execute(
            """
            SELECT rank, helm_name, sail_number, helm_sa_sailing_id
            FROM results WHERE block_id = %s ORDER BY rank
            """,
            (ILCA_BLOCK,),
        )
        for r in cur.fetchall():
            print(dict(r))
        print("\nOPTIMIST A FLEET")
        cur.execute(
            """
            SELECT rank, helm_name, sail_number, class_canonical, helm_sa_sailing_id
            FROM results WHERE block_id = %s ORDER BY rank
            """,
            (OPTI_BLOCK,),
        )
        for r in cur.fetchall():
            print(dict(r))
        print("\nBLOCK entries_raced")
        cur.execute(
            """
            SELECT block_id, class_canonical, entries_raced
            FROM regatta_blocks
            WHERE block_id IN (%s, %s)
            """,
            (ILCA_BLOCK, OPTI_BLOCK),
        )
        for r in cur.fetchall():
            print(dict(r))
        try:
            import sys
            from pathlib import Path as _P

            sys.path.insert(0, str(_P(__file__).resolve().parent))
            from invalidate_regatta_list_and_events_logos_cache import invalidate

            gone = invalidate(named_event_slug="zvyc-cape-classic")
            print("CACHE_BUST", gone)
        except Exception as exc:
            print("CACHE_BUST_FAIL", exc)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
