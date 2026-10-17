#!/usr/bin/env python3
"""Real visitors: NEVER rebuild table while any ▶ trail is open (fingerprint was defeating sticky)."""
from __future__ import annotations

import py_compile
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    orig = text

    old = """    var rows=(d.offline||[]).filter(function(r){ return r && r.kind!=="bot"; }); /* guest+staff */
    var fp=offlineRowsFingerprint(rows);
    var holdOpen=anyOfflineTrailOpen();
    // While a Real visitors trail is open, skip full table rebuild unless the list fingerprint changed
    if(holdOpen && window.__offlineRealFp===fp && box.querySelector("table")){
      var sumEl=box.querySelector("p.note");
      if(sumEl && rows.length){
        var pagesHold=0;
        rows.forEach(function(r){ pagesHold += (r.pages_count!=null?r.pages_count:((r.page_trail||[]).length)); });
        sumEl.textContent=rows.length+" real visitor"+(rows.length===1?"":"s")+" · "+pagesHold+" page"+(pagesHold===1?"":"s")+" — tap ▶ for full trail";
      }
      try{renderOfflineFb(d);}catch(eF){}
      try{renderOfflineBots(d);}catch(eB){}
      return;
    }
    window.__offlineRealFp=fp;
    var y=window.scrollY||0;
"""
    new = """    var rows=(d.offline||[]).filter(function(r){ return r && r.kind!=="bot"; }); /* guest+staff */
    // CRITICAL: while any Real visitors ▶ is open, do NOT touch the table at all.
    // Fingerprint always changes (path/pages/dwell) — that must not rebuild / collapse trails.
    if(anyOfflineTrailOpen() && box.querySelector("table.live-main, table")){
      try{renderOfflineFb(d);}catch(eF){}
      try{renderOfflineBots(d);}catch(eB){}
      return;
    }
    var y=window.scrollY||0;
"""
    if "CRITICAL: while any Real visitors" in text:
        print("SKIP hard hold already")
    elif old not in text:
        raise SystemExit("expected soft-hold block missing")
    else:
        text = text.replace(old, new, 1)
        print("OK hard hold — never rebuild while trail open")

    # Live: same — never rebuild while any live trail open (ignore fp)
    old_live = """    html+="</tbody></table>";
    var liveFp=liveRowsFingerprint(rows);
    if(anyLiveTrailOpen() && window.__liveRowsFp===liveFp && $("liveBox").querySelector("table")){
      return;
    }
    window.__liveRowsFp=liveFp;
    var liveY=window.scrollY||0;
    $("liveBox").innerHTML="<div class=\\"table-scroll\\">"+html+"</div>";
    try{ window.scrollTo(0, liveY); }catch(eLY){}
"""
    new_live = """    html+="</tbody></table>";
    // While any Live ▶ trail is open, leave the DOM alone (poll must not collapse it)
    if(anyLiveTrailOpen() && $("liveBox").querySelector("table")){
      return;
    }
    var liveY=window.scrollY||0;
    $("liveBox").innerHTML="<div class=\\"table-scroll\\">"+html+"</div>";
    try{ window.scrollTo(0, liveY); }catch(eLY){}
"""
    if "While any Live ▶ trail is open" in text:
        print("SKIP live hard hold already")
    elif old_live not in text:
        print("WARN live soft-hold block missing — try alt")
        # maybe never had live gate applied correctly
    else:
        text = text.replace(old_live, new_live, 1)
        print("OK live hard hold")

    # Also: re-check hold immediately before offline innerHTML (race with in-flight poll)
    old_assign = """    } else {
      var pages=0;
      rows.forEach(function(r){ pages += (r.pages_count!=null?r.pages_count:((r.page_trail||[]).length)); });
      var summary="<p class='note' style='font-weight:700;margin:0 0 8px'>"+rows.length+" real visitor"+(rows.length===1?"":"s")+" · "+pages+" page"+(pages===1?"":"s")+" — tap ▶ for full trail</p>";
      box.innerHTML=summary+renderOfflineRows(rows, "off");
      bindTrailToggleButtons(box);
    }
"""
    new_assign = """    } else {
      if(anyOfflineTrailOpen() && box.querySelector("table")){
        try{renderOfflineFb(d);}catch(eF){}
        try{renderOfflineBots(d);}catch(eB){}
        return;
      }
      var pages=0;
      rows.forEach(function(r){ pages += (r.pages_count!=null?r.pages_count:((r.page_trail||[]).length)); });
      var summary="<p class='note' style='font-weight:700;margin:0 0 8px'>"+rows.length+" real visitor"+(rows.length===1?"":"s")+" · "+pages+" page"+(pages===1?"":"s")+" — tap ▶ for full trail</p>";
      box.innerHTML=summary+renderOfflineRows(rows, "off");
      bindTrailToggleButtons(box);
    }
"""
    if "if(anyOfflineTrailOpen() && box.querySelector(\"table\")){\n        try{renderOfflineFb(d);}" in text:
        print("SKIP pre-assign race guard")
    elif old_assign not in text:
        print("WARN assign block missing")
    else:
        text = text.replace(old_assign, new_assign, 1)
        print("OK pre-assign race guard")

    # Make trail keys stable + store open on window explicitly in bind
    old_bind_open = """        if(open){
          row.removeAttribute("hidden");
          btn.setAttribute("aria-expanded","true");
          btn.textContent="▼";
          LIVE_TRAIL_OPEN[k]=true;
        } else {
          row.setAttribute("hidden","");
          btn.setAttribute("aria-expanded","false");
          btn.textContent="▶";
          delete LIVE_TRAIL_OPEN[k];
        }
"""
    new_bind_open = """        if(open){
          row.removeAttribute("hidden");
          btn.setAttribute("aria-expanded","true");
          btn.textContent="▼";
          LIVE_TRAIL_OPEN[k]=true;
          window.__liveTrailOpen=LIVE_TRAIL_OPEN;
        } else {
          row.setAttribute("hidden","");
          btn.setAttribute("aria-expanded","false");
          btn.textContent="▶";
          delete LIVE_TRAIL_OPEN[k];
          window.__liveTrailOpen=LIVE_TRAIL_OPEN;
        }
"""
    if "window.__liveTrailOpen=LIVE_TRAIL_OPEN" not in text:
        if old_bind_open not in text:
            print("WARN bind open block missing")
        else:
            text = text.replace(old_bind_open, new_bind_open, 1)
            print("OK bind persists window.__liveTrailOpen")
    else:
        print("SKIP bind window persist")

    if text != orig:
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print("OK compiled")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
