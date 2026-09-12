#!/usr/bin/env python3
"""Surgical live api.py patch: lock Cape Classic Open 1st/2nd to official+A8.2.

Official PDF = truth for fleet/rank/scores/total/nett (not names).
Sean 585 2+1=3, Gordon 589 1+2=3; A8.2 last race Sean R2=1 → rank 1.

Never replace live api.py wholesale. Run on the server against
/var/www/sailingsa/api/api.py after chattr -i.
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def must_swap(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise SystemExit(f"{label}: expected 1 occurrence, found {n}")
    return text.replace(old, new, 1)


def main() -> int:
    if not API.is_file():
        raise SystemExit(f"missing {API}")
    src = API.read_text(encoding="utf-8")
    orig = src

    src = must_swap(
        src,
        """        if _bow_attr:
            _tr_extra += f' data-bow="{_bow_attr}"'
        if _rid_tr:
            _tr_extra += f' data-result-id="{_rid_tr}"'
        row_html = f'<tr class="{row_classes}"{_tr_extra}>'
""",
        """        if _bow_attr:
            _tr_extra += f' data-bow="{_bow_attr}"'
        if _rid_tr:
            _tr_extra += f' data-result-id="{_rid_tr}"'
        try:
            _orank = r.get("rank")
            if _orank is not None and str(_orank).strip() != "":
                _tr_extra += f' data-official-rank="{html_module.escape(str(int(float(_orank))), quote=True)}"'
        except (TypeError, ValueError):
            pass
        row_html = f'<tr class="{row_classes}"{_tr_extra}>'
""",
        "data-official-rank on result rows",
    )

    src = must_swap(
        src,
        """    rows = list(fleet.get("rows") or [])
    is_wc_fleet_sheet = str(regatta_id or "") == WC_DINGHY_CHAMPS_REGATTA_SLUG
""",
        """    rows = list(fleet.get("rows") or [])

    def _sheet_official_rank_sort_key(x: dict):
        rk = x.get("rank")
        try:
            ir = int(float(rk)) if rk is not None else 10**9
        except (TypeError, ValueError):
            ir = 10**9
        return (ir, str(x.get("result_id") or ""))

    rows.sort(key=_sheet_official_rank_sort_key)
    is_wc_fleet_sheet = str(regatta_id or "") == WC_DINGHY_CHAMPS_REGATTA_SLUG
""",
        "sort fleet rows by official rank",
    )

    src = must_swap(
        src,
        """    /* Rank = lowest sheet Nett = 1st. Tracker re-rank only after the race is not racing. */
    if(String((st&&st.phase)||'').toLowerCase()==='racing'){
      sortRowsBySheetNett();
    } else {
      sortRowsFromCompleted(st);
    }
""",
        """    /* Official posted ranks (PDF checksum + Appendix A8) are HARD LOCK.
       Live tracker must not rewrite 1st/2nd when data-official-rank is on the sheet. */
    if(document.querySelector('.fleet-results-table tbody tr[data-official-rank]')){
      sortRowsByOfficialRank();
    } else if(String((st&&st.phase)||'').toLowerCase()==='racing'){
      sortRowsBySheetNett();
    } else {
      sortRowsFromCompleted(st);
    }
""",
        "live JS skip tracker re-rank when official ranks exist",
    )

    src = must_swap(
        src,
        """  function sortRowsBySheetNett(){
    /* Lowest sheet Nett = 1st. Ties keep original sheet order (A8 already applied). */
""",
        """  function sortRowsByOfficialRank(){
    /* PDF + A8 ranks already on the sheet. Keep that order; never invent 1st/2nd from tracker. */
    var tb=tbody();
    if(!tb) return;
    var rows=[].slice.call(tb.querySelectorAll('tr[data-official-rank]'));
    if(!rows.length) rows=[].slice.call(tb.querySelectorAll('tr[data-result-id]'));
    if(!rows.length) return;
    rows.sort(function(a,b){
      var na=Number(a.getAttribute('data-official-rank'));
      var nb=Number(b.getAttribute('data-official-rank'));
      if(!isFinite(na)) na=9999;
      if(!isFinite(nb)) nb=9999;
      if(na!==nb) return na-nb;
      return (Number(a.getAttribute('data-result-id'))||0)-(Number(b.getAttribute('data-result-id'))||0);
    });
    rows.forEach(function(tr,i){
      var p=Number(tr.getAttribute('data-official-rank'));
      if(!isFinite(p)) p=i+1;
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
  function sortRowsBySheetNett(){
    /* Lowest sheet Nett = 1st. Ties keep original sheet order (A8 already applied). */
""",
        "insert sortRowsByOfficialRank",
    )

    src = must_swap(
        src,
        """    if is_lipton:
        live_ok = False

""",
        """    if is_lipton:
        live_ok = False
    # Official Cape Classic PDF stamp: do not tick wall clock over 17:46 checksum.
    if str(regatta_id or "").strip() == "2026-09-13-zvyc-cape-classic":
        live_ok = False

""",
        "freeze Cape Classic official as-at",
    )

    if src == orig:
        raise SystemExit("no changes applied")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(f"/root/backups/api.py.open_a8_lock_{ts}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    API.write_text(src, encoding="utf-8")
    print(f"patched {API} backup={bak} bytes={len(src)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
