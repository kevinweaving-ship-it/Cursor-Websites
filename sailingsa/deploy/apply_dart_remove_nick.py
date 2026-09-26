#!/usr/bin/env python3
"""Surgical: remove Nick Somerville from Dart and rewrite code points to entries+1."""
import json
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

DSN = "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master"
RID = "2026-09-24-hmyc-dart-18-nationals"
NICK_ID = 21252
NICK_SAS = 8444
NICK_SAIL = "3599"
NICK_NAME = "Nick Somerville"
CODES = {
    "DNC",
    "DNS",
    "DNF",
    "RET",
    "DSQ",
    "UFD",
    "BFD",
    "OCS",
    "OCF",
    "NSC",
    "DNE",
    "TLE",
}
NUM_CODE = re.compile(r"^(\d+(?:\.\d+)?)\s+([A-Z]+)$", re.I)
BARE_CODE = re.compile(r"^([A-Z]+)$", re.I)


def parse_cell(raw):
    v = str(raw or "").strip()
    disc = v.startswith("(") and v.endswith(")")
    src = v[1:-1].strip() if disc else v
    m = NUM_CODE.match(src)
    if m:
        return float(m.group(1)), m.group(2).upper(), disc
    m = BARE_CODE.match(src)
    if m and m.group(1).upper() in CODES:
        return None, m.group(1).upper(), disc
    if re.fullmatch(r"\d+(?:\.\d+)?", src):
        return float(src), None, disc
    return None, None, disc


def points_of(raw):
    n, code, _ = parse_cell(raw)
    if n is not None:
        return n
    return 0.0


def rewrite_cell(raw, pts):
    n, code, disc = parse_cell(raw)
    if not code or code not in CODES:
        return raw, False
    new = f"{int(pts)} {code}"
    if disc:
        new = f"({new})"
    return new, str(raw or "").strip() != new


def main():
    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM results WHERE result_id=%s", (NICK_ID,))
    nick = cur.fetchone()
    if not nick:
        raise SystemExit("NICK_MISSING")
    assert nick["regatta_id"] == RID, nick["regatta_id"]
    assert nick["helm_name"] == NICK_NAME, nick["helm_name"]
    assert int(nick["helm_sa_sailing_id"]) == NICK_SAS
    assert str(nick["sail_number"]) == NICK_SAIL
    assert nick["fleet_label"] == "SH"
    print("NICK_OK", nick["result_id"], nick["helm_name"], nick["sail_number"], nick["race_scores"])
    cur.execute("SELECT * FROM results WHERE regatta_id=%s ORDER BY result_id", (RID,))
    snap = [dict(r) for r in cur.fetchall()]

    class Enc(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, (datetime, date)):
                return o.isoformat()
            if isinstance(o, Decimal):
                return float(o)
            return super().default(o)

    bak = Path("/root/backup_dart_nick_results.json")
    bak.write_text(json.dumps(snap, cls=Enc))
    print("JSON_BACKUP", bak, len(snap))

    cur.execute("SELECT COUNT(*) AS c FROM results WHERE regatta_id=%s", (RID,))
    before = int(cur.fetchone()["c"])
    print("BEFORE", before)
    if before != 39:
        raise SystemExit(f"UNEXPECTED_COUNT {before}")

    cur.execute("DELETE FROM results WHERE result_id=%s AND helm_sa_sailing_id=%s", (NICK_ID, NICK_SAS))
    print("DELETED", cur.rowcount)
    if cur.rowcount != 1:
        conn.rollback()
        raise SystemExit("DELETE_FAIL")

    cur.execute(
        "SELECT result_id, race_scores, rank FROM results WHERE regatta_id=%s ORDER BY result_id",
        (RID,),
    )
    rows = cur.fetchall()
    print("AFTER_COUNT", len(rows))
    if len(rows) != 38:
        conn.rollback()
        raise SystemExit(f"AFTER_COUNT {len(rows)}")
    pts = 38 + 1
    changed_rows = 0
    code_cells = 0
    for r in rows:
        rs = r["race_scores"] or {}
        if isinstance(rs, str):
            rs = json.loads(rs)
        if not isinstance(rs, dict):
            rs = {}
        new_rs = dict(rs)
        row_changed = False
        for k, v in list(new_rs.items()):
            nv, ch = rewrite_cell(v, pts)
            if ch:
                new_rs[k] = nv
                row_changed = True
                code_cells += 1
        total = sum(points_of(v) for v in new_rs.values())
        cur.execute(
            """
            UPDATE results
            SET race_scores = %s,
                total_points_raw = %s,
                nett_points_raw = %s
            WHERE result_id = %s AND regatta_id = %s
            """,
            (json.dumps(new_rs), Decimal(str(total)), Decimal(str(total)), r["result_id"], RID),
        )
        if row_changed:
            changed_rows += 1
        print(
            f"UPD {r['result_id']} tot={total} codes={row_changed} {new_rs}"
        )

    cur.execute(
        """
        UPDATE results r
        SET rank = x.rn
        FROM (
            SELECT result_id,
                   ROW_NUMBER() OVER (
                       ORDER BY nett_points_raw ASC,
                                total_points_raw ASC,
                                rank ASC NULLS LAST,
                                result_id ASC
                   ) AS rn
            FROM results
            WHERE regatta_id = %s
        ) x
        WHERE r.result_id = x.result_id
          AND r.regatta_id = %s
        """,
        (RID, RID),
    )
    print("RANKED", cur.rowcount)

    cur.execute(
        """
        SELECT COUNT(*) AS c FROM results
        WHERE regatta_id=%s AND helm_name=%s
        """,
        (RID, NICK_NAME),
    )
    if int(cur.fetchone()["c"]) != 0:
        conn.rollback()
        raise SystemExit("NICK_STILL_THERE")

    cur.execute(
        "SELECT race_scores FROM results WHERE regatta_id=%s",
        (RID,),
    )
    leftover_40 = 0
    for r in cur.fetchall():
        rs = r["race_scores"] or {}
        if isinstance(rs, str):
            rs = json.loads(rs)
        for v in (rs or {}).values():
            if str(v).strip().startswith("40 "):
                leftover_40 += 1
    if leftover_40:
        conn.rollback()
        raise SystemExit(f"LEFTOVER_40 {leftover_40}")

    conn.commit()
    print("CHANGED_ROWS", changed_rows, "CODE_CELLS", code_cells, "PTS", pts)
    print("DONE")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
