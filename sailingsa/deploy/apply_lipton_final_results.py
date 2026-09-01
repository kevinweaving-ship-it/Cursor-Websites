#!/usr/bin/env python3
"""Apply official Lipton 2026 overall scores + Final status to live DB.

Source: sailingsa/frontend/js/lipton-dev-series-scores.json (verified vs overall PDF).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REGATTA_ID = "2026-08-29-lipton-challenge-cup"
SERIES_PATH = Path(__file__).resolve().parents[2] / "sailingsa/frontend/js/lipton-dev-series-scores.json"

# JSON boat key → sail_number on results rows
BOAT_SAIL: dict[str, str] = {
    "HYC": "1571",
    "RCYC": "766",
    "UCTYC": "774",
    "FBYC": "1169",
    "SBYC": "1175",
    "RNYC": "768",
    "PYC": "1116",
    "RCYC Academy": "173",
    "WBYC": "1277",
    "KYC": "763",
    "LDYC": "1167",
    "GLYC": "185",
    "BYC": "1139",
    "LYC": "1237",
    "IZIVUNGUVUNGU": "771",
    "TSC": "1239",
    "WYAC": "1138",
}

# Sailwave overall PDF CreationDate (after 10 races, post-protest scores)
FINAL_AS_AT = "2026-08-29 15:24:06+02"
RESULT_STATUS = "Final"


def _fmt_race_cell(points: float, code: str | None) -> str:
    if code in ("DSQ", "RET"):
        if float(points) == int(points):
            return f"{int(points)}.0 {code}" if code == "DSQ" else f"{int(points)} {code}"
        return f"{points:.1f} {code}"
    if float(points) == int(points):
        return f"{int(points)}.0"
    return f"{points:.1f}"


def _race_scores_json(boat: dict) -> str:
    pts = boat.get("points") or {}
    codes = boat.get("codes") or {}
    cells = {}
    for i in range(1, 11):
        key = str(i)
        p = float(pts[key])
        c = codes.get(key) or ""
        cells[f"R{i}"] = _fmt_race_cell(p, c or None)
    return json.dumps(cells, separators=(",", ": "))


def main() -> int:
    data = json.loads(SERIES_PATH.read_text(encoding="utf-8"))
    boats = data.get("boats") or {}
    publish = data.get("publish") or {}
    as_at = publish.get("as_at_time") or FINAL_AS_AT
    status = publish.get("result_status") or RESULT_STATUS

    lines = [
        "-- Lipton Challenge Cup 2026 — official overall after 10 races",
        f"-- Source: {SERIES_PATH.name}",
        "BEGIN;",
    ]

    for boat_key, sail in BOAT_SAIL.items():
        row = boats.get(boat_key)
        if not row:
            print(f"WARN: missing boat {boat_key!r} in JSON", file=sys.stderr)
            continue
        pts = row.get("points") or {}
        total = sum(float(pts[str(i)]) for i in range(1, 11))
        race_scores = _race_scores_json(row)
        lines.append(
            f"UPDATE results SET "
            f"race_scores = '{race_scores}'::jsonb, "
            f"total_points_raw = {total:.1f}, "
            f"nett_points_raw = {total:.1f}, "
            f"result_status = '{status}', "
            f"as_at_time = '{as_at}'::timestamptz "
            f"WHERE regatta_id = '{REGATTA_ID}' AND sail_number = '{sail}';"
        )

    lines.append(
        f"UPDATE regattas SET result_status = '{status}', as_at_time = '{as_at}'::timestamptz "
        f"WHERE regatta_id = '{REGATTA_ID}';"
    )
    lines.append("COMMIT;")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
