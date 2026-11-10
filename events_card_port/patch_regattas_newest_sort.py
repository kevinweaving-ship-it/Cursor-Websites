#!/usr/bin/env python3
"""Ensure /regattas directory list sorts newest-first like landing."""
from pathlib import Path
import sys

path = Path(sys.argv[1])
t = path.read_text(encoding="utf-8")

if "sortRegattasNewestFirst" in t:
    print("already patched")
    sys.exit(0)

if "allParents=filterList(src,q);" in t:
    t = t.replace(
        "allParents=filterList(src,q);",
        "allParents=sortRegattasNewestFirst(filterList(src,q));",
        1,
    )
else:
    raise SystemExit("allParents assignment not found")

marker = "  function icoCal(){return '<svg width=\"12\""
sort_fn = """  function regattaSortDay(r){
    var keys=["end_date","start_date","as_at_time"];
    for(var i=0;i<keys.length;i++){
      var v=r[keys[i]];
      if(v==null) continue;
      var s=String(v).slice(0,10);
      if(/^\\d{4}-\\d{2}-\\d{2}$/.test(s)) return s;
    }
    return "0000-00-00";
  }
  function sortRegattasNewestFirst(list){
    return (list||[]).slice().sort(function(a,b){
      var da=regattaSortDay(a), db=regattaSortDay(b);
      if(da!==db) return db.localeCompare(da);
      var na=String(a.regatta_number||""), nb=String(b.regatta_number||"");
      if(na!==nb) return nb.localeCompare(na,undefined,{numeric:true});
      return String(a.event_name||"").toLowerCase().localeCompare(String(b.event_name||"").toLowerCase());
    });
  }
"""

if marker not in t:
    raise SystemExit("icoCal marker not found")
t = t.replace(marker, sort_fn + marker, 1)

path.write_text(t, encoding="utf-8")
print("patched regattas newest-first sort")
