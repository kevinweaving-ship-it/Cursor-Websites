#!/usr/bin/env python3
"""Checksum Lipton -dev mark passes and finishes. Do not invent GPS.

A pass is complete only when every still-racing boat has a received
rounding (or finish) timestamp. Empty cell = tracker never gave that visit.
"""
from __future__ import annotations

import hashlib
import json


def canonical_rows(boats: list[dict]) -> list[list]:
    rows = []
    for row in boats or []:
        sail = row.get("boat")
        ts = row.get("ts_ms", row.get("ts"))
        if sail is None or ts is None:
            continue
        rows.append([str(sail), int(ts)])
    rows.sort(key=lambda r: (r[1], r[0]))
    return rows


def sha16(payload) -> str:
    blob = json.dumps(payload, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def one_pass(pass_id: str, boats: list[dict], fleet: list[str]) -> dict:
    have = {str(r.get("boat")): int(r.get("ts_ms", r.get("ts"))) for r in (boats or []) if r.get("boat") is not None}
    missing = [s for s in fleet if s not in have]
    rows = canonical_rows(boats)
    return {
        "id": pass_id,
        "n": len(have),
        "fleet_n": len(fleet),
        "missing": missing,
        "ok": len(missing) == 0 and len(have) == len(fleet),
        "sha256": sha16({"id": pass_id, "rows": rows}),
    }


def expected_mark_specs(course_passes: list[dict], mark_passes: list[dict]) -> list[dict]:
    """Course template may list extra laps. Only checksum marks the fleet actually sailed.

    A later spec with zero boats means the race was shortened (finish after the previous mark).
    A spec with some boats is still required for the whole fleet — those gaps are checksum failures.
    """
    packed = {p["id"]: p for p in mark_passes}
    out = []
    for spec in course_passes:
        got = packed.get(spec["id"])
        n = len((got or {}).get("boats") or [])
        if n == 0:
            break
        out.append(spec)
    return out


def build_checksum(*, fleet: list[str], st: list[dict], mark_passes: list[dict], finish: list[dict], course_passes: list[dict]) -> dict:
    fleet = [str(s) for s in fleet]
    parts = [one_pass("ST", st, fleet)]
    for spec in expected_mark_specs(course_passes, mark_passes):
        got = next((p for p in mark_passes if p["id"] == spec["id"]), {"boats": []})
        parts.append(one_pass(spec["id"], got.get("boats") or [], fleet))
    parts.append(one_pass("FIN", finish, fleet))
    missing = [{"id": p["id"], "missing": p["missing"]} for p in parts if not p["ok"]]
    return {
        "fleet_n": len(fleet),
        "ok": not missing,
        "sha256": sha16([p["sha256"] for p in parts]),
        "passes": parts,
        "gaps": missing,
        "note": (
            "Each pass sha256 is boat+ts from tracker GPS (marks) or Firestore (finish). "
            "Missing boats are GPS holes or a rounding we did not receive — not filled in."
        ),
    }
