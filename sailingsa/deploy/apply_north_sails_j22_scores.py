#!/usr/bin/env python3
"""Apply / update North Sails J22 race scores; checksum total/nett; re-rank by nett.

Live multi-day event. Identity/entry fields are LIVE_PARTIAL_LOCK — this script
only touches OPEN fields: race_scores, total/nett, rank, sailed/discard counts.

Usage (today — fill SCORES then run):
  DB_URL=... python3 deploy/apply_north_sails_j22_scores.py

Usage (tomorrow — edit SCORES to add R3/R4/… then re-run):
  Same command. Recomputes totals/netts, checksums, re-sorts ranks.

NOR note: event is 6 races, no discards (RCYC). Keep discard_count=0 unless SI changes.

Ranking:
  1) total = sum of all race points (discarded included)
  2) nett = total − discarded  (with discards 0 → nett == total)
  3) checksum: nett + discarded == total
  4) sort nett ASC; tie → lower last-race score ranks above
  5) rewrite rank / rank_ordinal
"""
from __future__ import annotations

import json
import os
import re
import sys
from decimal import Decimal

import psycopg2
from psycopg2.extras import Json, RealDictCursor

DB_URL = os.environ.get(
    "DB_URL",
    "postgresql://sailors_user:SailSA_Pg_Beta2026@localhost:5432/sailors_master",
)
RID = "2026-08-16-2026-north-sails-j22-championships"
BLOCK_ID = f"{RID}:j22"

# sail_number (digits) -> { "R1": "1.0", "R2": "3.0", ... }
# Fill from official sheet. Do NOT invent. Tomorrow: add R3, R4, … here and re-run.
SCORES: dict[str, dict[str, str]] = {
    # "1571": {"R1": "1.0", "R2": "2.0"},
}

# Optional override path: JSON file {"1571":{"R1":"1.0","R2":"2.0"}, ...}
SCORES_JSON = os.environ.get("SCORES_JSON", "")


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 13:
        suf = "th"
    else:
        suf = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def parse_points(raw: str) -> tuple[Decimal, bool]:
    """Return (points, is_discard). Discard = parentheses."""
    s = (raw or "").strip()
    if not s:
        raise ValueError("empty score")
    discarded = s.startswith("(") and s.endswith(")")
    if discarded:
        s = s[1:-1].strip()
    # "14.0 DNC" / "5.0" / "5"
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)", s)
    if not m:
        raise ValueError(f"no numeric points in {raw!r}")
    return Decimal(m.group(1)), discarded


def normalize_score(raw: str) -> str:
    """Enforce .0 / paren / penalty spacing lightly; keep sheet intent."""
    s = (raw or "").strip()
    if not s:
        return s
    discarded = s.startswith("(") and s.endswith(")")
    core = s[1:-1].strip() if discarded else s
    m = re.match(r"^([0-9]+)(?:\.0)?(\s+[A-Z]+)?$", core)
    if m:
        core = f"{m.group(1)}.0" + (m.group(2) or "")
    return f"({core})" if discarded else core


def load_scores() -> dict[str, dict[str, str]]:
    if SCORES_JSON:
        with open(SCORES_JSON, encoding="utf-8") as f:
            data = json.load(f)
        return {str(k): {rk: normalize_score(str(v)) for rk, v in row.items()} for k, row in data.items()}
    if not SCORES:
        return {}
    return {
        str(k): {rk: normalize_score(str(v)) for rk, v in row.items()} for k, row in SCORES.items()
    }


def total_nett(scores: dict[str, str]) -> tuple[Decimal, Decimal, Decimal]:
    total = Decimal("0")
    discarded_sum = Decimal("0")
    for v in scores.values():
        pts, is_disc = parse_points(v)
        total += pts
        if is_disc:
            discarded_sum += pts
    nett = total - discarded_sum
    return total, nett, discarded_sum


def last_race_points(scores: dict[str, str]) -> Decimal:
    keys = sorted(scores.keys(), key=lambda k: int(re.sub(r"\D", "", k) or "0"))
    if not keys:
        return Decimal("9999")
    pts, _ = parse_points(scores[keys[-1]])
    return pts


def main() -> int:
    scores_by_sail = load_scores()
    if not scores_by_sail:
        print(
            "ERROR: no scores loaded. Fill SCORES in this script or set SCORES_JSON=/path/file.json",
            file=sys.stderr,
        )
        return 2

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT result_id, rank, sail_number, bow_no, helm_name, validation_flag
        FROM results WHERE regatta_id = %s ORDER BY rank
        """,
        (RID,),
    )
    rows = list(cur.fetchall() or [])
    if not rows:
        print("ERROR: no result rows", file=sys.stderr)
        return 1

    # Guard: only open fields if locked
    for r in rows:
        flag = r.get("validation_flag") or ""
        if flag and flag != "LIVE_PARTIAL_LOCK":
            print(f"WARN: result_id={r['result_id']} validation_flag={flag!r}")

    missing = []
    computed = []
    for r in rows:
        sail = re.sub(r"[^0-9]", "", r["sail_number"] or "")
        sc = scores_by_sail.get(sail) or scores_by_sail.get(r["sail_number"] or "")
        if not sc:
            missing.append(sail or r["sail_number"])
            continue
        total, nett, discarded = total_nett(sc)
        if nett + discarded != total:
            print(f"CHECKSUM FAIL sail={sail} total={total} nett={nett} disc={discarded}")
            return 1
        computed.append(
            {
                "result_id": r["result_id"],
                "sail": sail,
                "helm": r["helm_name"],
                "scores": sc,
                "total": total,
                "nett": nett,
                "discarded": discarded,
                "last": last_race_points(sc),
                "n_races": len(sc),
                "n_disc_brackets": sum(
                    1 for v in sc.values() if str(v).strip().startswith("(")
                ),
            }
        )

    if missing:
        print("ERROR: missing scores for sails:", ", ".join(str(m) for m in missing))
        return 1
    if len(computed) != len(rows):
        print("ERROR: row/score count mismatch")
        return 1

    # Place checksum per race: when all numeric places, expect 1..N each race (ties share)
    race_keys = sorted(
        {rk for c in computed for rk in c["scores"]},
        key=lambda k: int(re.sub(r"\D", "", k) or "0"),
    )
    n_entries = len(computed)
    for rk in race_keys:
        vals = []
        for c in computed:
            raw = c["scores"].get(rk, "")
            pts, _ = parse_points(raw)
            # skip non-finish codes for unique-place check if letter present
            if re.search(r"[A-Z]", raw.upper()):
                continue
            vals.append(pts)
        if len(vals) == n_entries:
            s = sum(vals)
            expected = Decimal(n_entries * (n_entries + 1)) / 2
            if s != expected:
                print(f"WARN place-sum {rk}: sum={s} expected={expected} (ties/penalties?)")

    # Sort: nett ASC, last race ASC
    computed.sort(key=lambda c: (c["nett"], c["last"], c["sail"]))

    discard_count = max((c["n_disc_brackets"] for c in computed), default=0)
    # NOR: no discards — force 0 if no brackets present
    if all(c["n_disc_brackets"] == 0 for c in computed):
        discard_count = 0
    races_sailed = len(race_keys)
    to_count = races_sailed - discard_count

    for i, c in enumerate(computed, start=1):
        cur.execute(
            """
            UPDATE results
            SET race_scores = %s,
                total_points_raw = %s,
                nett_points_raw = %s,
                rank = %s,
                rank_ordinal = %s,
                races_sailed = %s,
                discard_count = %s,
                race_updated_status = 'Provisional'
            WHERE result_id = %s
            """,
            (
                Json(c["scores"]),
                float(c["total"]),
                float(c["nett"]),
                i,
                _ordinal(i),
                races_sailed,
                discard_count,
                c["result_id"],
            ),
        )
        print(
            f"{_ordinal(i):>4} sail={c['sail']:>5} nett={c['nett']} total={c['total']} "
            f"last={c['last']} {c['scores']}  {c['helm']}"
        )

    cur.execute(
        """
        UPDATE regatta_blocks
        SET races_sailed = %s,
            discard_count = %s,
            to_count = %s,
            entries_raced = %s,
            scoring_system = COALESCE(scoring_system, 'Appendix A')
        WHERE block_id = %s
        RETURNING races_sailed, discard_count, to_count, entries_raced
        """,
        (races_sailed, discard_count, to_count, n_entries, BLOCK_ID),
    )
    block = cur.fetchone()
    conn.commit()
    print("block", dict(block) if block else None)
    print(
        f"OK: {n_entries} rows ranked by nett ASC "
        f"(tie → lower last-race score). races={races_sailed} discards={discard_count}"
    )
    cur.close()
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
