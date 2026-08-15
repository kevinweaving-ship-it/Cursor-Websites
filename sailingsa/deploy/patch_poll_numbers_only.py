#!/usr/bin/env python3
"""Stop 3s poll from rewriting Real visitors / Live tables (fixes flash)."""
from __future__ import annotations

import py_compile
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    orig = text

    # Replace both poll branches: only update KPI numbers on interval; never rebuild tables
    old1 = """        if(live && live.ok){
          var trailHold=Object.keys(LIVE_TRAIL_OPEN).some(function(k){ return !!LIVE_TRAIL_OPEN[k]; })
            || !!document.querySelector("#liveBox .live-exp[aria-expanded='true'], #offlineBox .live-exp[aria-expanded='true'], #offlineFbBox .live-exp[aria-expanded='true'], #offlineBotsBox .live-exp[aria-expanded='true']");
          if(!trailHold){
            renderLive(live);
            try{renderOffline(live);}catch(eOff){}
          } else {
            // keep open trails usable — only refresh the LIVE NOW number
            if(live.human_live!=null) $("kLive").textContent=String(live.human_live);
          }
          if(!trailHold && live.human_live!=null) $("kLive").textContent=String(live.human_live);
        }
"""
    new1 = """        if(live && live.ok){
          // POLL: numbers only — never rebuild Live/Real visitors tables (was flashing every 3s)
          if(live.human_live!=null) $("kLive").textContent=String(live.human_live);
          else if(live.rows) $("kLive").textContent=String((live.rows||[]).length);
        }
"""
    if "POLL: numbers only — never rebuild" in text:
        print("SKIP poll1 already")
    elif old1 in text:
        text = text.replace(old1, new1, 1)
        print("OK poll1 numbers-only")
    else:
        print("WARN poll1 block missing — trying loose match")

    old2 = """    fetchJson("/traffic/api/live").then(function(d){
      if(!d.ok) return;
      var trailHold=Object.keys(LIVE_TRAIL_OPEN).some(function(k){ return !!LIVE_TRAIL_OPEN[k]; });
      if(trailHold){ if(d.human_live!=null) $("kLive").textContent=String(d.human_live); return; }
      renderLive(d); try{renderOffline(d);}catch(eOff){}
    }).catch(function(){});
"""
    # also match the DOM aria trailHold variant
    old2b = """    fetchJson("/traffic/api/live").then(function(d){
      if(!d.ok) return;
      var trailHold=Object.keys(LIVE_TRAIL_OPEN).some(function(k){ return !!LIVE_TRAIL_OPEN[k]; })
            || !!document.querySelector("#liveBox .live-exp[aria-expanded='true'], #offlineBox .live-exp[aria-expanded='true'], #offlineFbBox .live-exp[aria-expanded='true'], #offlineBotsBox .live-exp[aria-expanded='true']");
      if(trailHold){ if(d.human_live!=null) $("kLive").textContent=String(d.human_live); return; }
      renderLive(d); try{renderOffline(d);}catch(eOff){}
    }).catch(function(){});
"""
    new2 = """    fetchJson("/traffic/api/live").then(function(d){
      if(!d.ok) return;
      // POLL: numbers only — tables only refresh on range change / full loadAll
      if(d.human_live!=null) $("kLive").textContent=String(d.human_live);
    }).catch(function(){});
"""
    if "tables only refresh on range change" in text:
        print("SKIP poll2 already")
    elif old2b in text:
        text = text.replace(old2b, new2, 1)
        print("OK poll2 numbers-only (aria variant)")
    elif old2 in text:
        text = text.replace(old2, new2, 1)
        print("OK poll2 numbers-only")
    else:
        # find setInterval live fetch and show context
        i = text.find('fetchJson("/traffic/api/live").then(function(d){')
        print("WARN poll2 missing; context:\n", text[i : i + 500] if i >= 0 else "no fetch")

    # Also: if ANY other setInterval path still calls renderOffline(live) inside interval
    # Count renderOffline in setInterval region
    si = text.find("setInterval(function(){")
    # find traffic one near trailHold or kLive
    si = text.find('setInterval(function(){\n    if(RANGE==="live"){')
    if si < 0:
        si = text.find('setInterval(function(){\n    if(RANGE===\"live\"){')
    chunk = text[si : si + 2500] if si >= 0 else ""
    if "renderOffline" in chunk:
        print("WARN renderOffline still inside setInterval chunk")
        print(chunk[:1500])
    else:
        print("OK no renderOffline in live setInterval")

    if text != orig:
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print("OK compiled")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
