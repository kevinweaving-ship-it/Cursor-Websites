"""Tracking-dev2 bootstrap — Sailfish-shaped race meta + Lipton R1–R10 fallback data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_FRONTEND_JS = Path(__file__).resolve().parents[1] / "frontend" / "js"
_LIPTON_SLUG = "2026-08-29-lipton-challenge-cup"
_DEV2_SLUG = "2026-08-29-lipton-challenge-cup-dev2"

# Sailfish runtime[] index map (see docs/sailfish-china-extracts/WS_PAYLOAD_SCHEMA.md)
RUNTIME_IDX = {
    "entity_id": 3,
    "status": 4,
    "sog": 10,
    "cog": 16,
    "lat": 17,
    "lng": 18,
    "power": 19,
    "timestamp_ms": 22,
    "rank": 32,
}


def _js_path(name: str) -> Path:
    return _FRONTEND_JS / name


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _replay_path(race: int) -> str:
    if race == 4:
        return "/js/lipton-dev-replay.json"
    return f"/js/lipton-dev-replay-r{race}.json"


def _trail_path(race: int) -> str:
    if race == 4:
        return "/js/lipton-dev-trail.json"
    return f"/js/lipton-dev-trail-r{race}.json"


def _race_meta(race: int) -> Optional[Dict[str, Any]]:
    manifest = _load_json(_js_path("lipton-dev-races.json"))
    for row in manifest.get("races") or []:
        if int(row.get("n") or 0) == race:
            return row
    return None


def _team_list_from_replay(replay: Dict[str, Any]) -> List[Dict[str, Any]]:
    boats = replay.get("boats") or {}
    team_list: List[Dict[str, Any]] = []
    for boat_id, meta in boats.items():
        if not isinstance(meta, dict):
            continue
        team_list.append(
            {
                "teamCd": boat_id,
                "teamName": meta.get("name") or boat_id,
                "sailNo": str(meta.get("bow") or ""),
                "club": meta.get("club") or "",
                "runtime": [""] * 51,
            }
        )
    team_list.sort(key=lambda t: (t.get("sailNo") or "", t.get("teamName") or ""))
    return team_list


def bootstrap_payload(race: int) -> Dict[str, Any]:
    """Build open_trac-like bootstrap for tracking-dev2 (replay-only sample)."""
    race = max(1, min(10, int(race or 1)))
    meta = _race_meta(race)
    if not meta or not meta.get("packed"):
        raise ValueError(f"Race {race} not packed in Lipton fallback set")

    replay_path = _js_path(_replay_path(race).split("/")[-1])
    replay = _load_json(replay_path)

    gun_ms = int(replay.get("gun_ts_ms") or 0)
    race_cd = f"lipton-r{race}"

    return {
        "success": True,
        "flag": True,
        "raceCd": race_cd,
        "regattaSlug": _LIPTON_SLUG,
        "devSlug": _DEV2_SLUG,
        "raceName": f"Race {race}",
        "matchName": "2026 Lipton Challenge Cup",
        "fleet": replay.get("fleet") or "J22",
        "status": "99",
        "replayFlag": "1",
        "rounds": f"R{race}",
        "readyTime": str(gun_ms - 300_000),
        "startTime": gun_ms,
        "endTime": int(replay.get("end_ts_ms") or gun_ms),
        "searouteRole": replay.get("course", {}).get("id") or meta.get("course_id") or "",
        "viewConfig": {
            "sogUnit": "kts",
            "trackLength": 90,
            "timeSpan": 6,
            "replaySpeed": 5,
            "maxPlaySpeed": 500,
            "ColRanking": True,
            "ColSOG": True,
            "ColCOG": True,
            "ColVMG": False,
            "ColDTL": False,
            "layline": True,
            "laylineAngle": 44.2,
            "leaderline": True,
            "windCompass": True,
            "camera": True,
        },
        "teamList": _team_list_from_replay(replay),
        "runtimeIndex": RUNTIME_IDX,
        "chunkUrls": {
            "bootstrap": f"/api/tracking-dev2/bootstrap?race={race}",
            "replay": _replay_path(race),
            "trail": _trail_path(race),
        },
        "transport": {
            "mode": "replay",
            "live2": None,
            "replay2": "static-json",
            "ws": None,
            "note": "Sailfish WS deferred; Lipton packed JSON is fallback sample R1–R10",
        },
        "liptonMeta": meta,
        "ocs": replay.get("ocs") or [],
        "course": replay.get("course") or {},
    }
