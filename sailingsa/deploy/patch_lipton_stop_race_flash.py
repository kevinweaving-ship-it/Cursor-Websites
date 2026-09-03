#!/usr/bin/env python3
"""Stop Lipton URL flashing: not race mode.

1) Persist LIVE on all icons mirrors + live-race JSON (clear gun).
2) Patch live api.py JS so paintFinishTimes does not rewrite the sheet
   unless phase=racing AND board=RACING.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

RID = "2026-08-29-lipton-challenge-cup"
API_PY = Path("/var/www/sailingsa/api/api.py")
LIVE_JSON = Path(f"/var/tmp/sailingsa_live_race_{RID}.json")

ICON_PATHS = [
    Path("/var/www/sailingsa/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/api/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/api/data/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/data/wc_regatta_header_icons.json"),
    Path("/var/www/sailingsa/static/data/wc_regatta_header_icons.json"),
]

PAINT_OLD = """  function paintFinishTimes(st){
    try{ pruneInflatedRaceCols(); }catch(e){}
    try{ ensureRaceCol('R4'); ensurePlusTCol('R4'); }catch(e){}
    try{ pruneInflatedRaceCols(); }catch(e){}
"""

PAINT_NEW = """  function paintFinishTimes(st){
    var phase=String((st&&st.phase)||'').toLowerCase();
    var board=String((st&&(st.board_status||st.status))||'').toUpperCase();
    /* Not race mode: do not inject R+T columns or rewrite cells (that flashes the URL). */
    if(phase!=='racing' || board!=='RACING' || st.day_done || st.track_idle){
      try{ pruneInflatedRaceCols(); }catch(e){}
      return;
    }
    try{ pruneInflatedRaceCols(); }catch(e){}
    try{ ensureRaceCol('R4'); ensurePlusTCol('R4'); }catch(e){}
    try{ pruneInflatedRaceCols(); }catch(e){}
"""

LASTSIG_OLD = """        if(sig===lastSig){
          updateFinishWindowReady(st);
          paintFinishTimes(st);
          if(String((st.phase||'')).toLowerCase()==='racing'){
            sortRowsBySheetNett();
          }
          return;
        }
        lastSig=sig;
        paintFinishTimes(st);
        /* Overall rank = lowest sheet Nett = 1st. Do not re-rank from tracker while racing. */
        if(String((st.phase||'')).toLowerCase()==='racing'){
          sortRowsBySheetNett();
        } else if(doneKeys.length || (st.rankings&&st.rankings.length)){
          sortRowsFromCompleted(st);
        } else {
          sortRowsBySheetNett();
        }
"""

LASTSIG_NEW = """        if(sig===lastSig){
          updateFinishWindowReady(st);
          if(String((st.phase||'')).toLowerCase()==='racing' && String((st.board_status||st.status||'')).toUpperCase()==='RACING'){
            paintFinishTimes(st);
            sortRowsBySheetNett();
          }
          return;
        }
        lastSig=sig;
        if(String((st.phase||'')).toLowerCase()==='racing' && String((st.board_status||st.status||'')).toUpperCase()==='RACING'){
          paintFinishTimes(st);
          sortRowsBySheetNett();
        }
        /* Not racing: leave checksum sheet still. Do not paint/sort from tracker. */
"""

RACEUI_OLD = """    var boardRacing = pageStatus()==='RACING';
    var phaseRacing = !!(use && String(use.phase||'').toLowerCase()==='racing');
    var raceDone = !!(use && (String(use.phase||'').toLowerCase()==='finished' || use.race_complete));
    /* Underway = racing; between races (ended) show Class/Helm/Crew/Sail again on MP. */
    var underway = (boardRacing || phaseRacing) && !raceDone;
    /* Don't wipe SSR/underway on null tick before /live-race answers (board poll→LIVE used to clear hide). */
    if(!use && !boardRacing && page.getAttribute('data-live-race-underway')==='1'){
      underway = true;
    }
"""

RACEUI_NEW = """    var boardRacing = pageStatus()==='RACING';
    var phaseRacing = !!(use && String(use.phase||'').toLowerCase()==='racing');
    var raceDone = !!(use && (String(use.phase||'').toLowerCase()==='finished' || use.race_complete || use.day_done));
    /* Underway only when board AND phase are racing. LIVE/finished must not hide/show columns (flash). */
    var underway = boardRacing && phaseRacing && !raceDone;
    if(pageStatus()==='LIVE' || pageStatus()==='POSTPONED'){
      underway = false;
    }
"""


def _load_json(path: Path):
    try:
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return None
        o = json.loads(raw)
        return o if isinstance(o, dict) else None
    except Exception:
        return None


def sync_live_not_racing() -> None:
    for p in ICON_PATHS:
        d = _load_json(p)
        if d is None:
            print("skip icons", p)
            continue
        ent = dict(d.get(RID) or {})
        ent["live_board_status"] = "LIVE"
        ent.pop("live_race_gun_at", None)
        d[RID] = ent
        p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("icons LIVE", p)

    st = _load_json(LIVE_JSON) or {}
    st["regatta_id"] = RID
    st["phase"] = "finished"
    st["status"] = "LIVE"
    st["board_status"] = "LIVE"
    st["gun_at"] = None
    st["gun_source"] = None
    st["day_done"] = True
    st["track_idle"] = True
    st["race_armed"] = False
    st["schedule_slot"] = "day_close"
    st["elapsed"] = None
    st["elapsed_raw"] = None
    LIVE_JSON.write_text(json.dumps(st, indent=2), encoding="utf-8")
    try:
        shutil.chown(str(LIVE_JSON), user="www-data", group="www-data")
    except Exception:
        os.system(f"chown www-data:www-data {LIVE_JSON}")
    os.chmod(LIVE_JSON, 0o664)
    print("live-race JSON LIVE", LIVE_JSON)


def patch_api_text(s: str) -> str:
    if "Not race mode: do not inject R+T columns" in s and "leave checksum sheet still" in s:
        return s
    reps = [
        (PAINT_OLD, PAINT_NEW, "paintFinishTimes guard"),
        (LASTSIG_OLD, LASTSIG_NEW, "poller lastSig"),
        (RACEUI_OLD, RACEUI_NEW, "onRacingUi underway"),
    ]
    for old, new, label in reps:
        if new in s and old not in s:
            continue
        n = s.count(old)
        if n != 1:
            raise SystemExit(f"{label}: expected 1, found {n}")
        s = s.replace(old, new, 1)
    if "Not race mode: do not inject R+T columns" not in s:
        raise SystemExit("paintFinishTimes guard missing after patch")
    return s


def patch_api_py() -> None:
    original = API_PY.read_text(encoding="utf-8")
    updated = patch_api_text(original)
    if updated == original:
        print("api.py already patched")
        return
    bak = API_PY.with_name(API_PY.name + ".bak-stop-flash-" + time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(API_PY, bak)
    API_PY.write_text(updated, encoding="utf-8")
    print("patched", API_PY, "backup", bak)


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else "all"
    if only in ("all", "state"):
        sync_live_not_racing()
    if only in ("all", "js"):
        patch_api_py()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
