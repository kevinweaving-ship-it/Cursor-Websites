#!/usr/bin/env python3
"""Run on live host. Stubs all writers. Does not persist schedule sim."""
from __future__ import annotations

import json
import sys
from pathlib import Path

RID = "2026-08-29-lipton-challenge-cup"
JSON_PATH = Path("/var/tmp/sailingsa_live_race_2026-08-29-lipton-challenge-cup.json")
API_PATH = Path("/var/www/sailingsa/api/api.py")

sys.path.insert(0, "/var/www/sailingsa/api")
import importlib.util

spec = importlib.util.spec_from_file_location("api_sim", API_PATH)
mod = importlib.util.module_from_spec(spec)
print("loading api.py…", flush=True)
spec.loader.exec_module(mod)
print("loaded", flush=True)

mem = json.loads(JSON_PATH.read_text(encoding="utf-8"))
keys = ("phase", "status", "board_status", "gun_at", "day_done", "track_idle", "race_armed", "race_complete", "race_key", "schedule_slot")


def fake_read(rid):
    return dict(mem)


def fake_write(rid, st):
    mem.clear()
    mem.update(st)
    return st


def fake_set(rid, status):
    # Reproduce LIVE overnight keep-last-Rn without touching icons.
    st = str(status or "").strip().upper()
    lr = dict(mem)
    if st == "LIVE":
        overnight = bool(lr.get("day_done")) or str(lr.get("schedule_slot") or "") == "day_close"
        lr["gun_at"] = None
        lr["gun_source"] = None
        if overnight:
            lr["phase"] = "finished" if lr.get("race_times") else "idle"
            # keep race_key
        else:
            lr["phase"] = "idle"
            try:
                lr["race_key"] = mod._live_race_next_race_key(rid)
            except Exception:
                pass
        mem.clear()
        mem.update(lr)
    return st


mod._read_live_race_state = fake_read
mod._write_live_race_state = fake_write
mod._set_regatta_live_board_status = fake_set
mod._persist_live_race_gun_to_icons = lambda *a, **k: None
mod._write_wc_regatta_header_icons = lambda *a, **k: None

print("START", {k: mem.get(k) for k in keys})
print("next_now", mod._live_race_next_race_key(RID))

orig = json.loads(JSON_PATH.read_text(encoding="utf-8"))
leftover = dict(orig)
leftover["phase"] = "racing"
leftover["status"] = "RACING"
leftover["board_status"] = "RACING"
leftover["gun_at"] = "2026-08-27T16:45:00+02:00"
leftover["race_complete"] = False
leftover["day_done"] = False
mem.clear()
mem.update(leftover)
mod._live_race_sa_minutes_now = lambda: 2 * 60
st02 = mod._live_race_apply_sa_schedule(RID, dict(mem))
print("02:00 leftover gun", {k: st02.get(k) for k in keys})
ok02 = (
    not st02.get("gun_at")
    and st02.get("day_done") is True
    and str(st02.get("board_status") or "") == "LIVE"
    and str(st02.get("race_key") or "") == "R5"
)

mem.clear()
mem.update(orig)
mod._live_race_sa_minutes_now = lambda: 10 * 60
st10 = mod._live_race_apply_sa_schedule(RID, dict(mem))
print("10:00", {k: st10.get(k) for k in keys})
print("next_after_10", mod._live_race_next_race_key(RID))

mod._live_race_sa_minutes_now = lambda: 12 * 60
st12 = mod._live_race_apply_sa_schedule(RID, dict(mem))
print("12:00", {k: st12.get(k) for k in keys})
print("gun_at_12", st12.get("gun_at"))

ok = (
    ok02
    and st10.get("race_key") == "R6"
    and st10.get("day_done") is False
    and not st10.get("gun_at")
    and st12.get("race_key") == "R6"
    and st12.get("race_armed") is True
    and not st12.get("gun_at")
    and str(st12.get("board_status") or "") == "LIVE"
)
print("RESULT", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
