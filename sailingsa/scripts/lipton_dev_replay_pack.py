#!/usr/bin/env python3
"""Build / replace the Lipton -dev replay JSON.

Replay sandbox only. Does not write Nett. Live comes later.

Default: pack frozen Race 5 mark-1 trail + identity already in the JSON,
refreshing gun/finish times from the tracker when available.

  python3 sailingsa/scripts/lipton_dev_replay_pack.py
  python3 sailingsa/scripts/lipton_dev_replay_pack.py --from-tracker
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "sailingsa/frontend/js/lipton-dev-replay.json"
OUT_COPY = ROOT / "js/lipton-dev-replay.json"
MARK_ORDERS = ROOT / "docs/lipton_2026_r5_mark_orders.json"
SAST = ZoneInfo("Africa/Johannesburg")


def ms_iso(value) -> int | None:
    if not value:
        return None
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=SAST)
    return int(dt.timestamp() * 1000)


def load_boats(prev: dict) -> dict:
    boats = (prev or {}).get("boats") or {}
    if len(boats) != 17:
        raise SystemExit("lipton-dev-replay.json is missing the 17-boat identity map")
    return boats


def load_mark1(prev: dict) -> list:
    if prev.get("mark1"):
        return prev["mark1"]
    orders = json.loads(MARK_ORDERS.read_text())
    for passing in orders.get("passes") or []:
        if passing.get("pass_id") == "L1-1":
            return [
                {"boat": row["boat"], "ts_ms": int(row["ts_ms"])}
                for row in passing.get("order") or []
            ]
    raise SystemExit("no mark-1 order in replay JSON or mark_orders file")


def tracker_r5() -> dict | None:
    sys.path.insert(0, str(ROOT / "sailingsa/scripts"))
    from lipton_vakaros import fetch_lipton_from_tracker  # type: ignore

    summary = fetch_lipton_from_tracker()
    for race in summary.get("races") or []:
        if race.get("race_number") == 5:
            return race
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Replace Lipton -dev replay JSON")
    ap.add_argument("--from-tracker", action="store_true", help="Refresh R5 gun/finish from Vakaros")
    args = ap.parse_args()
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    boats = load_boats(prev)
    mark1 = load_mark1(prev)
    gun = int(prev.get("gun_ts_ms") or 1787838601000)
    play_start = int(prev.get("play_start_ts_ms") or (mark1[0]["ts_ms"] - 30000))
    first_finish = int(prev.get("first_finish_ts_ms") or 0)
    end = int(prev.get("end_ts_ms") or (mark1[-1]["ts_ms"] + 8000))
    gun_sast = prev.get("gun_sast")
    first_finish_sast = prev.get("first_finish_sast")
    end_sast = prev.get("end_sast")
    if args.from_tracker:
        r5 = tracker_r5()
        if not r5:
            raise SystemExit("tracker has no Race 5")
        gun = ms_iso(r5.get("gun_at_sast")) or gun
        first_finish = ms_iso(r5.get("first_finish_sast")) or first_finish
        end = ms_iso(r5.get("end_sast")) or end
        gun_sast = r5.get("gun_at_sast")
        first_finish_sast = r5.get("first_finish_sast")
        end_sast = r5.get("end_sast")
        play_start = mark1[0]["ts_ms"] - 30000
    pack = {
        "mode": "replay",
        "live": False,
        "note": "Replay sandbox only. Test here, then live later. Replace this file to refresh old playback data. Not a Nett source.",
        "regatta_id": "2026-08-29-lipton-challenge-cup",
        "dev_slug": "2026-08-29-lipton-challenge-cup-dev",
        "event_id": "Lv9A35uOBSBRmGpHgXtH",
        "fleet": "J22",
        "watch_path": "https://player.vakaros.com/watch/Lv9A35uOBSBRmGpHgXtH/J22",
        "race_number": 5,
        "race_day": 2,
        "gun_ts_ms": gun,
        "gun_sast": gun_sast,
        "play_start_ts_ms": play_start,
        "first_finish_ts_ms": first_finish,
        "first_finish_sast": first_finish_sast,
        "end_ts_ms": end,
        "end_sast": end_sast,
        "default_rate": 8,
        "mark1": mark1,
        "boats": boats,
        "jumps": {"gun": gun, "mark1": play_start, "finish": first_finish},
        "sources": {
            "guns_finishes": "Vakaros Firestore races[R5]",
            "mark1_order": "teleapi GPS trail (docs/lipton_2026_r5_mark_orders.json L1-1)",
            "identity": "public Lipton sheet bow/boat/club logos",
        },
    }
    text = json.dumps(pack, indent=2, ensure_ascii=False) + "\n"
    OUT.write_text(text)
    OUT_COPY.write_text(text)
    print(json.dumps({"ok": True, "path": str(OUT), "boats": len(boats), "mark1": len(mark1), "from_tracker": args.from_tracker}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
