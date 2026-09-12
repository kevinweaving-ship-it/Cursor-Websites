#!/usr/bin/env python3
"""Surgical live api.py: Appendix A order for ALL result sheets. Never result_id."""
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
        "import json\nimport hmac\nimport base64\nimport difflib\n",
        "import json\nfrom appendix_a import appendix_a_result_sort_key, sort_result_rows_appendix_a\nimport hmac\nimport base64\nimport difflib\n",
        "import appendix_a",
    )

    src = must_swap(
        src,
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
        """    rows = sort_result_rows_appendix_a(list(fleet.get("rows") or []))
""",
        "fleet sheet order is Appendix A, not rank+result_id",
    )

    src = must_swap(
        src,
        'out.sort(key=lambda x: (int(x.get("rank")) if x.get("rank") is not None and str(x.get("rank")).isdigit() else 9999, x.get("result_id") or 0))',
        "out.sort(key=appendix_a_result_sort_key)",
        "class filter sort",
    )

    src = must_swap(
        src,
        """      var na=sheetNettVal(a), nb=sheetNettVal(b);
      if(na!==nb) return na-nb;
      return (Number(a.getAttribute('data-sheet-order'))||0)-(Number(b.getAttribute('data-sheet-order'))||0);
""",
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
        "live JS tie = last race, never sheet-order/result_id",
    )

    if src == orig:
        raise SystemExit("no changes")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = Path(f"/root/backups/api.py.appendix_a_{ts}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    API.write_text(src, encoding="utf-8")
    print(f"patched backup={bak}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
