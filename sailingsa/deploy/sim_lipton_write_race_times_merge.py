#!/usr/bin/env python3
"""On live: stub state path and prove pending R6 is kept with R4/R5.

Does not write production live-race JSON. Uses a temp file.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

RID = "2026-08-29-lipton-challenge-cup"
API_PATH = Path("/var/www/sailingsa/api/api.py")
sys.path.insert(0, "/var/www/sailingsa/api")
import importlib.util

spec = importlib.util.spec_from_file_location("api_sim_merge", API_PATH)
mod = importlib.util.module_from_spec(spec)
print("loading api.py…", flush=True)
spec.loader.exec_module(mod)
print("loaded", flush=True)

td = Path(tempfile.mkdtemp(prefix="lipton-merge-"))
state_path = td / "state.json"
prev = {
    "regatta_id": RID,
    "phase": "finished",
    "race_key": "R5",
    "race_times": {
        "R4": [{"bow": "26", "place": 4, "finish_ms": 100, "boat_name": "Amtec Racing", "club": "RCYC"}],
        "R5": [{"bow": "26", "place": 1, "finish_ms": 80, "boat_name": "Amtec Racing", "club": "RCYC"}],
    },
}
state_path.write_text(json.dumps(prev) + "\n", encoding="utf-8")
mod._live_race_state_path = lambda rid: state_path
mod._persist_live_race_gun_to_icons = lambda *a, **k: None
mod._write_wc_regatta_header_icons = lambda *a, **k: None

incoming = dict(prev)
incoming["race_times"] = {"R6": [{"bow": "26", "boat_name": "VAKAROS Amtec"}]}
out = mod._write_live_race_state(RID, incoming)
rt = out.get("race_times") or {}
print("keys", sorted(rt.keys()))
ok = (
    set(rt) == {"R4", "R5", "R6"}
    and rt["R5"][0]["place"] == 1
    and rt["R6"][0].get("place") is None
    and rt["R6"][0]["club"] == "RCYC"
    and rt["R6"][0]["boat_name"] == "Amtec Racing"
)
print("RESULT", "PASS" if ok else "FAIL")
try:
    state_path.unlink(missing_ok=True)
    os.rmdir(td)
except Exception:
    pass
sys.exit(0 if ok else 1)
