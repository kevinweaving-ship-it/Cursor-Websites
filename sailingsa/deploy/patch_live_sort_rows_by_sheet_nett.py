#!/usr/bin/env python3
"""Patch live api.py: overall Rank = lowest sheet Nett = 1st.

The live-results JS (only on production api.py) re-sorted rows from Vakaros
race_times while a race was in progress. That scrambled Rank away from the
official checksum Nett column.

This inserts sortRowsBySheetNett() and uses it while phase==='racing'.
Does not add race scores. Does not overwrite local api.py wholesale.
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

DEFAULT_PATH = Path("/var/www/sailingsa/api/api.py")

SORT_FN = r"""  function sheetNettVal(tr){
    var td=tr.querySelector('td.nett-col');
    var t=td?String(td.textContent||'').replace(/[(),]/g,'').trim():'';
    var n=parseFloat(t);
    return isFinite(n)?n:9999;
  }
  function sortRowsBySheetNett(){
    /* Lowest sheet Nett = 1st. Ties keep original sheet order (A8 already applied). */
    var tb=tbody();
    if(!tb) return;
    var rows=[].slice.call(tb.querySelectorAll('tr[data-bow]'));
    if(!rows.length) return;
    rows.forEach(function(tr,i){
      if(!tr.getAttribute('data-sheet-order')) tr.setAttribute('data-sheet-order', String(i));
    });
    rows.sort(function(a,b){
      var na=sheetNettVal(a), nb=sheetNettVal(b);
      if(na!==nb) return na-nb;
      return (Number(a.getAttribute('data-sheet-order'))||0)-(Number(b.getAttribute('data-sheet-order'))||0);
    });
    rows.forEach(function(tr,i){
      var p=i+1;
      tr.setAttribute('data-live-place', String(p));
      tr.classList.remove('medal-gold','medal-silver','medal-bronze','regatta-live-rank-row');
      if(p===1) tr.classList.add('medal-gold');
      else if(p===2) tr.classList.add('medal-silver');
      else if(p===3) tr.classList.add('medal-bronze');
      var tdRank=tr.querySelector('td.rank-col');
      if(tdRank){
        var del=tdRank.querySelector('.fleet-entry-del');
        var ord=ordinalPlace(p);
        if(del){
          tdRank.innerHTML='';
          tdRank.appendChild(del);
          tdRank.appendChild(document.createTextNode(ord));
        } else {
          tdRank.textContent=ord;
        }
      }
      tb.appendChild(tr);
    });
  }
"""

PAINT_OLD = """    reorderLiveRaceCols(st);
    /* Rank/Nett stay on checksum sheet while current race is in progress. */
    if(String((st&&st.phase)||'').toLowerCase()!=='racing'){
      sortRowsFromCompleted(st);
    }
    updateFinishWindowReady(st);"""

PAINT_NEW = """    reorderLiveRaceCols(st);
    /* Rank = lowest sheet Nett = 1st. Tracker re-rank only after the race is not racing. */
    if(String((st&&st.phase)||'').toLowerCase()==='racing'){
      sortRowsBySheetNett();
    } else {
      sortRowsFromCompleted(st);
    }
    updateFinishWindowReady(st);"""

POLLER_OLD = """        paintFinishTimes(st);
        /* Never re-sort from empty current race — keep prior ranks until new race finishes. */
        if(doneKeys.length || (st.rankings&&st.rankings.length)){
          sortRowsFromCompleted(st);
        }"""

POLLER_NEW = """        paintFinishTimes(st);
        /* Overall rank = lowest sheet Nett = 1st. Do not re-rank from tracker while racing. */
        if(String((st.phase||'')).toLowerCase()==='racing'){
          sortRowsBySheetNett();
        } else if(doneKeys.length || (st.rankings&&st.rankings.length)){
          sortRowsFromCompleted(st);
        } else {
          sortRowsBySheetNett();
        }"""

LASTSIG_OLD = """        if(sig===lastSig){
          updateFinishWindowReady(st);
          paintFinishTimes(st);
          return;
        }"""

LASTSIG_NEW = """        if(sig===lastSig){
          updateFinishWindowReady(st);
          paintFinishTimes(st);
          if(String((st.phase||'')).toLowerCase()==='racing'){
            sortRowsBySheetNett();
          }
          return;
        }"""

FN_ANCHOR = "  function sortRowsFromCompleted(st){"


def patch_text(s: str) -> str:
    if "function sortRowsBySheetNett()" in s and POLLER_NEW in s and PAINT_NEW in s:
        return s  # already applied
    if FN_ANCHOR not in s:
        raise SystemExit("anchor function sortRowsFromCompleted not found")
    if s.count(FN_ANCHOR) != 1:
        raise SystemExit("anchor function sortRowsFromCompleted not unique")
    if "function sortRowsBySheetNett()" not in s:
        s = s.replace(FN_ANCHOR, SORT_FN + FN_ANCHOR, 1)
    replacements = [
        (PAINT_OLD, PAINT_NEW, "paintFinishTimes sort guard"),
        (POLLER_OLD, POLLER_NEW, "poller sortRowsFromCompleted"),
        (LASTSIG_OLD, LASTSIG_NEW, "lastSig racing re-sort"),
    ]
    for old, new, label in replacements:
        if new in s and old not in s:
            continue
        n = s.count(old)
        if n != 1:
            raise SystemExit(f"{label}: expected 1 occurrence, found {n}")
        s = s.replace(old, new, 1)
    if "function sortRowsBySheetNett()" not in s:
        raise SystemExit("sortRowsBySheetNett missing after patch")
    if POLLER_OLD in s:
        raise SystemExit("poller still sorts from tracker while racing")
    return s


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH)
    original = path.read_text(encoding="utf-8")
    updated = patch_text(original)
    if updated == original:
        print("already patched", path)
        return 0
    bak = path.with_name(path.name + ".bak-sort-by-nett-" + time.strftime("%Y%m%d-%H%M%S"))
    shutil.copy2(path, bak)
    path.write_text(updated, encoding="utf-8")
    print("patched", path)
    print("backup", bak)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
