#!/usr/bin/env python3
"""Sim: overnight restore merges icon stubs into the full catalog and pins last filled Rn."""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import restore_lipton_live_overnight as m


def main() -> int:
    d = Path(tempfile.mkdtemp(prefix="lipton-restore-"))
    full = d / "full.json"
    stub = d / "stub.json"
    state = d / "state.json"
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
    state.write_text(
        json.dumps(
            {
                "race_times": {
                    "R5": [{"bow": "26", "place": 1}],
                    "R6": [{"bow": "26"}],
                }
            }
        ),
        encoding="utf-8",
    )
    m.STATE = state
    m.ICON_PATHS = [full, stub]
    m.main()
    a = json.loads(full.read_text(encoding="utf-8"))
    b = json.loads(stub.read_text(encoding="utf-8"))
    st = json.loads(state.read_text(encoding="utf-8"))
    assert a == b, (a, b)
    assert "other-regatta" in a
    lipton = a["2026-08-29-lipton-challenge-cup"]
    assert lipton["live_race_key"] == "R5", lipton
    assert lipton["live_board_status"] == "LIVE"
    assert lipton.get("live_race_gun_at") is None
    assert lipton.get("venue") == "Royal Cape Yacht Club"
    assert "first_gun" not in lipton
    assert st["race_key"] == "R5"
    assert st["day_done"] is True
    assert st["race_armed"] is False
    print("PASS restore merges catalog, pins R5, keeps venue, drops 15:51")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
