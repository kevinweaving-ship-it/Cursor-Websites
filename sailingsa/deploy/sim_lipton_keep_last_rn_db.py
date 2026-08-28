#!/usr/bin/env python3
"""Sim: overnight last-Rn uses max(tracker race_times, DB race_scores)."""
from __future__ import annotations

import re


def last_rk(race_times: dict, db_keys: list[str], current: str = "R1") -> str:
    filled_n = []
    for k, rows in (race_times or {}).items():
        m = re.match(r"^R(\d+)$", str(k), re.I)
        if not m:
            continue
        if isinstance(rows, list) and any(
            isinstance(r, dict)
            and (r.get("place") is not None or r.get("finish_ms") is not None)
            for r in rows
        ):
            filled_n.append(int(m.group(1)))
    for k in db_keys:
        m = re.match(r"^R(\d+)$", str(k), re.I)
        if m:
            filled_n.append(int(m.group(1)))
    if filled_n:
        return "R" + str(max(filled_n))
    return current


def main() -> int:
    rt = {
        "R4": [{"place": 1}],
        "R5": [{"place": 1}],
    }
    assert last_rk(rt, []) == "R5"
    assert last_rk(rt, ["R1", "R2", "R3", "R4", "R5", "R6"]) == "R6"
    assert last_rk({}, ["R6"]) == "R6"
    assert last_rk({}, [], current="R3") == "R3"
    # Schedule GET pin must not rewind below DB max when race_times lag.
    assert last_rk(rt, ["R6"]) == "R6"
    print("PASS keep-last-rn uses DB max when race_times lag")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
