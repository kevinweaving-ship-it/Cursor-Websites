"""Sailfish (saill.cn) open_trac parity helpers for tracking-dev2."""

from __future__ import annotations

from typing import Any, Dict

# From docs/sailfish-china-extracts/open_trac/viewConfig.json (ILCA6 sample race)
SAILFISH_VIEW_CONFIG: Dict[str, Any] = {
    "orderType": 1,
    "rotate": True,
    "playbarCalendar": False,
    "laylineAngle": 44.2,
    "targetMark": True,
    "maxZoom": 20,
    "sogUnit": "kts",
    "cameraRace": True,
    "simulationLength": 5,
    "zoomSnap": False,
    "trackLength": 90,
    "weather": False,
    "layline": True,
    "timeSpan": 6,
    "buffer": 5000,
    "scopeRadius": 24,
    "replaySpeed": 5,
    "showDots": False,
    "windwardLeg": 1,
    "showJury": False,
    "ColMaxSOG": False,
    "ColDTLv": False,
    "countdown": 300000,
    "ColTimeCost": False,
    "ColVMC": False,
    "ColTotalDist": False,
    "ColVMG": False,
    "referenceLine": True,
    "startingAnalysis": True,
    "ColDTS": False,
    "windCompass": True,
    "readyShow": 0,
    "legAnalysis": True,
    "timeout": 15,
    "ColRTS": False,
    "ColAveVMC": False,
    "camera": True,
    "ColAveSOG": False,
    "ColRanking": True,
    "trajMode": 2,
    "ColAveVMG": False,
    "leaderline": True,
    "ColDTF": False,
    "maxPlaySpeed": 500,
    "ColDTL": False,
    "ColSOG": True,
    "ColCOG": True,
    "ColStatus": True,
    "sailWithTitle": True,
    "graticule": True,
}

WS_TOPICS_TEMPLATE = [
    "/topic/SAIL_DATA_BATCH_P_{raceCd}",
    "/topic/BUOY_DATA_{raceCd}",
    "/topic/RACE_CONTROL_{raceCd}",
]

PROD_WSS = "wss://www.saill.cn/sailfish-ntwss?token=sailfish"


def merge_view_config(overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    cfg = dict(SAILFISH_VIEW_CONFIG)
    if overrides:
        cfg.update(overrides)
    return cfg


def get_race_payload(bootstrap: Dict[str, Any]) -> Dict[str, Any]:
    """Shape compatible with Sailfish getRace?pageName=open_trac."""
    race_cd = bootstrap.get("raceCd") or ""
    vc = bootstrap.get("viewConfig") or {}
    return {
        "success": True,
        "flag": True,
        "data": {
            "raceCd": race_cd,
            "matchName": bootstrap.get("matchName"),
            "raceName": bootstrap.get("raceName"),
            "rounds": bootstrap.get("rounds"),
            "status": bootstrap.get("status"),
            "replayFlag": bootstrap.get("replayFlag"),
            "fleet": bootstrap.get("fleet"),
            "readyTime": bootstrap.get("readyTime"),
            "startTime": bootstrap.get("startTime"),
            "endTime": bootstrap.get("endTime"),
            "searouteRole": bootstrap.get("searouteRole"),
            "viewConfig": vc,
            "viewConfigJson": __import__("json").dumps(vc),
            "windInstruments": bootstrap.get("windInstruments"),
            "deviceCdList": bootstrap.get("deviceCdList"),
        },
    }


def get_race_datas_payload(bootstrap: Dict[str, Any]) -> Dict[str, Any]:
    """Shape compatible with replay2/getRaceDatas (plain JSON dev mode — no LZ)."""
    race_cd = bootstrap.get("raceCd") or ""
    transport = bootstrap.get("transport") or {}
    out = dict(bootstrap)
    out["devMode"] = True
    out["stomp"] = None if transport.get("mode") == "replay" else PROD_WSS
    out["wsTopics"] = [t.format(raceCd=race_cd) for t in WS_TOPICS_TEMPLATE]
    return out


def get_replay_chunk_payload(bootstrap: Dict[str, Any]) -> Dict[str, Any]:
    """Dev stand-in for getEncryptionReplayData — points at static Lipton JSON."""
    urls = bootstrap.get("chunkUrls") or {}
    return {
        "success": True,
        "flag": True,
        "devMode": True,
        "note": "Sailfish LZ result omitted; use chunkUrls.replay (Lipton packed JSON).",
        "replayUrl": urls.get("replay"),
        "trailUrl": urls.get("trail"),
        "timeSpan": (bootstrap.get("viewConfig") or {}).get("timeSpan", 6),
        "raceCd": bootstrap.get("raceCd"),
        "teamCount": len(bootstrap.get("teamList") or []),
    }
