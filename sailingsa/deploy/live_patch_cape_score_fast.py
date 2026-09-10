#!/usr/bin/env python3
"""Bump Cape Classic club-score JS to ccr4; skip snapshot on Cape recalc."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
src = API.read_text(encoding="utf-8")

old_js = "club-score-edit.js?v=ccr3"
new_js = "club-score-edit.js?v=ccr4"
if new_js in src:
    print("JS_ALREADY_CCR4")
elif old_js not in src:
    raise SystemExit("ANCHOR_JS_MISSING")
else:
    src = src.replace(old_js, new_js, 1)
    print("JS_BUMPED_CCR4")

old_snap = """            WHERE r.result_id = ranked.result_id
            """,
            (block_id,),
        )

    _ensure_snapshot_integrity(conn, regatta_id)


def _recalculate_fleet_block_scoring_and_ranks"""
new_snap = """            WHERE r.result_id = ranked.result_id
            """,
            (block_id,),
        )

    if not str(regatta_id or "").startswith("2026-09-13-zvyc-cape-classic"):
        _ensure_snapshot_integrity(conn, regatta_id)


def _recalculate_fleet_block_scoring_and_ranks"""
if "if not str(regatta_id or \"\").startswith(\"2026-09-13-zvyc-cape-classic\"):\n        _ensure_snapshot_integrity(conn, regatta_id)" in src:
    print("SNAP_ALREADY")
elif old_snap not in src:
    raise SystemExit("ANCHOR_SNAP_MISSING")
else:
    src = src.replace(old_snap, new_snap, 1)
    print("SNAP_SKIP_CAPE")

API.write_text(src, encoding="utf-8")
print("PATCHED_OK")
print("ccr4", new_js in src)
