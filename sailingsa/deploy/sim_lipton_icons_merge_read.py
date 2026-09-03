#!/usr/bin/env python3
"""Sim: per-rid merge keeps the catalog when a 1-key Lipton stub is newest."""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path


def merge_read(paths):
    merged = {}
    rid_mt = {}
    for p in paths:
        if not p.is_file():
            continue
        mt = float(p.stat().st_mtime)
        o = json.loads(p.read_text(encoding="utf-8"))
        for rid, rec in o.items():
            k = str(rid)
            if k not in merged or mt >= rid_mt.get(k, -1.0):
                merged[k] = rec
                rid_mt[k] = mt
    return merged


def newest_wins(paths):
    best = {}
    best_mtime = -1.0
    for p in paths:
        mt = float(p.stat().st_mtime)
        o = json.loads(p.read_text(encoding="utf-8"))
        if mt >= best_mtime:
            best = o
            best_mtime = mt
    return best


def main() -> int:
    d = Path(tempfile.mkdtemp(prefix="lipton-icons-"))
    full = d / "full.json"
    stub = d / "stub.json"
    full.write_text(
        json.dumps(
            {
                "other-regatta": {"venue": "Keep Me"},
                "2026-08-29-lipton-challenge-cup": {
                    "live_board_status": "LIVE",
                    "live_race_key": "R5",
                    "venue": "Royal Cape Yacht Club",
                    "first_gun": "15:51",
                },
            }
        ),
        encoding="utf-8",
    )
    time.sleep(0.05)
    stub.write_text(
        json.dumps(
            {
                "2026-08-29-lipton-challenge-cup": {
                    "live_board_status": "LIVE",
                    "live_race_key": "R6",
                }
            }
        ),
        encoding="utf-8",
    )
    paths = [full, stub]
    old = newest_wins(paths)
    new = merge_read(paths)
    assert "other-regatta" not in old, old
    assert old["2026-08-29-lipton-challenge-cup"]["live_race_key"] == "R6"
    assert "other-regatta" in new, new
    assert new["other-regatta"]["venue"] == "Keep Me"
    assert new["2026-08-29-lipton-challenge-cup"]["live_race_key"] == "R6"
    print("PASS merge keeps catalog; Lipton from newest stub")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
