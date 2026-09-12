#!/usr/bin/env python3
"""Revert global sheet re-sort on live. Do not reshuffle other events' pages.

Keep Appendix A only for rank assignment on score-save (this block), not HTML read path.
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
    src = API.read_text(encoding="utf-8")
    orig = src

    src = must_swap(
        src,
        "import json\nfrom appendix_a import appendix_a_result_sort_key, sort_result_rows_appendix_a\nimport hmac\n",
        "import json\nfrom appendix_a import sort_result_rows_appendix_a\nimport hmac\n",
        "import only write-path helper",
    )

    src = must_swap(
        src,
        """    rows = sort_result_rows_appendix_a(list(fleet.get("rows") or []))
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
""",
        "restore stored-rank sheet order (no A8 reshuffle of old events)",
    )

    src = must_swap(
        src,
        "out.sort(key=appendix_a_result_sort_key)",
        'out.sort(key=lambda x: (int(x.get("rank")) if x.get("rank") is not None and str(x.get("rank")).isdigit() else 9999, x.get("result_id") or 0))',
        "restore class-filter stored order",
    )

    src = must_swap(
        src,
        """      var na=sheetNettVal(a), nb=sheetNettVal(b);
      if(na!==nb) return na-nb;
      function racePlaces(tr){
        var out=[];
        tr.querySelectorAll('td.race-col[data-race-key]').forEach(function(td){
          var n=parseFloat(String(td.textContent||'').replace(/[()]/g,'').trim());
          if(isFinite(n)) out.push(n);
        });
        return out;
      }
      var pa=racePlaces(a), pb=racePlaces(b);
      var as=pa.slice().sort(function(x,y){return x-y;});
      var bs=pb.slice().sort(function(x,y){return x-y;});
      var i,n=Math.max(as.length,bs.length);
      for(i=0;i<n;i++){
        var va=i<as.length?as[i]:9999, vb=i<bs.length?bs[i]:9999;
        if(va!==vb) return va-vb;
      }
      return (pa.length?pa[pa.length-1]:9999)-(pb.length?pb[pb.length-1]:9999);
""",
        """      var na=sheetNettVal(a), nb=sheetNettVal(b);
      if(na!==nb) return na-nb;
      return (Number(a.getAttribute('data-sheet-order'))||0)-(Number(b.getAttribute('data-sheet-order'))||0);
""",
        "restore live JS sheet-order (do not retie other events)",
    )

    old_rank_sql = '''            # Re-rank entire fleet by nett scores (lower nett = better rank)
            # Each sailor must have unique rank (no ties) - break ties by result_id
            # NULL/0 nett scores rank last (treated as 999999)
            cur.execute("""
                WITH ranked AS (
                    SELECT result_id,
                           ROW_NUMBER() OVER (
                               ORDER BY 
                                   COALESCE(
                                       NULLIF(nett_points_raw, 0), 
                                       999999
                                   ) ASC, 
                                   result_id ASC
                           ) as new_rank
                    FROM results
                    WHERE block_id = %s
                )
                UPDATE results r
                SET rank = ranked.new_rank
                FROM ranked
                WHERE r.result_id = ranked.result_id
            """, (block_id,))
'''
    new_rank_sql = '''            # Re-rank this fleet only (score save). Appendix A: low nett, then last race. Never result_id.
            cur.execute(
                """
                SELECT result_id, nett_points_raw, race_scores
                FROM results
                WHERE block_id = %s
                """,
                (block_id,),
            )
            fleet_for_rank = cur.fetchall() or []
            for i, row in enumerate(sort_result_rows_appendix_a(fleet_for_rank), 1):
                cur.execute(
                    "UPDATE results SET rank = %s WHERE result_id = %s AND block_id = %s",
                    (i, row["result_id"], block_id),
                )
'''
    if old_rank_sql in src:
        src = must_swap(src, old_rank_sql, new_rank_sql, "score-save rank uses A8 not result_id")
    elif "Never result_id. Does not rewrite other events." in src:
        print("score-save already A8")
    else:
        print("WARN: live score-save rank SQL not found; display revert still applied")

    if src == orig:
        raise SystemExit("no changes")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(f"/root/backups/api.py.no_global_a8_{ts}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    API.write_text(src, encoding="utf-8")
    print(f"patched backup={bak}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
