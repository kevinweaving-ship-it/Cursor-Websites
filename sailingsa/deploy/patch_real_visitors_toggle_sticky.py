#!/usr/bin/env python3
"""Real visitors ▶ trails: don't rebuild table on every poll while a trail is open."""
from __future__ import annotations

import py_compile
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    orig = text

    # 1) Stop wiping off: sticky opens on page load (default is already collapsed)
    old_wipe = """  /* OFF_TRAIL_DEFAULT_HIDE — collapse offline trails once per page load */
  if(!window.__offTrailHideInit){ window.__offTrailHideInit=true;
    Object.keys(LIVE_TRAIL_OPEN).forEach(function(k){ if(k.indexOf("off:")===0||k.indexOf("offbot:")===0) delete LIVE_TRAIL_OPEN[k]; }); }
"""
    new_wipe = """  /* OFF_TRAIL_STICKY — keep Real visitors ▶ open state across polls (no wipe) */
"""
    if "OFF_TRAIL_STICKY" not in text:
        if old_wipe in text:
            text = text.replace(old_wipe, new_wipe, 1)
            print("OK removed off: wipe on load")
        else:
            print("WARN off-trail wipe block missing")

    # 2) Skip full Real visitors rebuild while any off: trail is open (unless data fingerprint changed for open rows)
    old_ro = """  function renderOffline(d){
    var box=$("offlineBox");
    if(!box) return;
    var note=$("realSinceNote");
    if(note && d.real_since){
      note.textContent="Since reset "+String(d.real_since).replace("T"," ").slice(0,19)+" — every real visitor (scroll/click). All pages in trail (sailors, clubs, events, boats…). Nothing hidden if real.";
    }
    var rows=(d.offline||[]).filter(function(r){ return r && r.kind!=="bot"; }); /* guest+staff */
    if(!rows.length){
      box.innerHTML="<p class='note'>No real visitors since reset yet (need scroll or click).</p>";
    } else {
      var pages=0;
      rows.forEach(function(r){ pages += (r.pages_count!=null?r.pages_count:((r.page_trail||[]).length)); });
      var summary="<p class='note' style='font-weight:700;margin:0 0 8px'>"+rows.length+" real visitor"+(rows.length===1?"":"s")+" · "+pages+" page"+(pages===1?"":"s")+" — tap ▶ for full trail</p>";
      box.innerHTML=summary+renderOfflineRows(rows, "off");
      bindTrailToggleButtons(box);
    }
    try{renderOfflineFb(d);}catch(eF){}
    try{renderOfflineBots(d);}catch(eB){}
  }
"""
    new_ro = """  function offlineRowsFingerprint(rows){
    return rows.map(function(r){
      var n=r.pages_count!=null?r.pages_count:((r.page_trail||[]).length);
      var id=r.ip||r.visitor_id||r.session_id||r.who||"";
      return id+"#"+n+"#"+(r.path||"")+"#"+((r.page_trail&&r.page_trail.length)||0);
    }).join("|");
  }
  function anyOfflineTrailOpen(){
    return Object.keys(LIVE_TRAIL_OPEN).some(function(k){
      return LIVE_TRAIL_OPEN[k] && (k.indexOf("off:")===0 || k.indexOf("offfb:")===0 || k.indexOf("offbot:")===0);
    });
  }
  function renderOffline(d){
    var box=$("offlineBox");
    if(!box) return;
    var note=$("realSinceNote");
    if(note && d.real_since){
      note.textContent="Since reset "+String(d.real_since).replace("T"," ").slice(0,19)+" — every real visitor (scroll/click). All pages in trail (sailors, clubs, events, boats…). Nothing hidden if real.";
    }
    var rows=(d.offline||[]).filter(function(r){ return r && r.kind!=="bot"; }); /* guest+staff */
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
    if(!rows.length){
      box.innerHTML="<p class='note'>No real visitors since reset yet (need scroll or click).</p>";
    } else {
      var pages=0;
      rows.forEach(function(r){ pages += (r.pages_count!=null?r.pages_count:((r.page_trail||[]).length)); });
      var summary="<p class='note' style='font-weight:700;margin:0 0 8px'>"+rows.length+" real visitor"+(rows.length===1?"":"s")+" · "+pages+" page"+(pages===1?"":"s")+" — tap ▶ for full trail</p>";
      box.innerHTML=summary+renderOfflineRows(rows, "off");
      bindTrailToggleButtons(box);
    }
    try{ window.scrollTo(0, y); }catch(eScr){}
    try{renderOfflineFb(d);}catch(eF){}
    try{renderOfflineBots(d);}catch(eB){}
  }
"""
    if "offlineRowsFingerprint" not in text:
        if old_ro not in text:
            raise SystemExit("renderOffline block missing/changed")
        text = text.replace(old_ro, new_ro, 1)
        print("OK renderOffline hold-open skip rebuild")
    else:
        print("SKIP renderOffline fingerprint already")

    # 3) Same for Live list — skip rebuild if any live trail open and fingerprint same
    # Find renderLive start through liveBox innerHTML assign — lighter touch: wrap liveBox assign
    if "window.__liveRowsFp" not in text:
        old_live_assign = """    $("liveBox").innerHTML="<div class=\\"table-scroll\\">"+html+"</div>";
    $("liveBox").querySelectorAll(".live-exp").forEach(function(btn){
"""
        # Prefer inserting fingerprint gate at start of renderLive body after rows=
        # Safer: after building html, before assign — check open + fp
        # Need live fingerprint helper near liveTrailKey
        anchor = "  function liveTrailKey(r){"
        if anchor not in text:
            print("WARN liveTrailKey missing")
        else:
            helper = """  function liveRowsFingerprint(rows){
    return (rows||[]).slice(0,30).map(function(r){
      var id=r.ip||r.visitor_id||r.session_id||"";
      var n=(r.page_trail&&r.page_trail.length)||0;
      return id+"#"+(r.path||"")+"#"+n+"#"+(r.session_dwell_label||"");
    }).join("|");
  }
  function anyLiveTrailOpen(){
    return Object.keys(LIVE_TRAIL_OPEN).some(function(k){
      return LIVE_TRAIL_OPEN[k] && k.indexOf("off")!==0;
    });
  }
"""
            text = text.replace(anchor, helper + anchor, 1)
            print("OK live fingerprint helpers")

        # Gate the liveBox innerHTML replace inside renderLive
        # Look for the pattern after html is built
        old_gate = """    html+="</tbody></table>";
    $("liveBox").innerHTML="<div class=\\"table-scroll\\">"+html+"</div>";
"""
        new_gate = """    html+="</tbody></table>";
    var liveFp=liveRowsFingerprint(rows);
    if(anyLiveTrailOpen() && window.__liveRowsFp===liveFp && $("liveBox").querySelector("table")){
      return;
    }
    window.__liveRowsFp=liveFp;
    var liveY=window.scrollY||0;
    $("liveBox").innerHTML="<div class=\\"table-scroll\\">"+html+"</div>";
    try{ window.scrollTo(0, liveY); }catch(eLY){}
"""
        if "window.__liveRowsFp===liveFp" not in text:
            if old_gate not in text:
                print("WARN liveBox assign gate missing")
            else:
                text = text.replace(old_gate, new_gate, 1)
                print("OK live hold-open skip rebuild")
        else:
            print("SKIP live gate")
    else:
        print("SKIP live fingerprint already")

    if text != orig:
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print("OK compiled")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
