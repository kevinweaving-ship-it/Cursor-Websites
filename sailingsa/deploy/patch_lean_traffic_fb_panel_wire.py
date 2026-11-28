#!/usr/bin/env python3
"""Wire /traffic Facebook share-crawls panel from /traffic/api/live.

Prevents real-visitors (no offline_fb) from blanking the FB section.
"""
from __future__ import annotations
import shutil, time
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

def must_replace(text, old, new, label):
    if text.count(old) != 1:
        raise SystemExit(f"FAIL {label}: {text.count(old)}")
    return text.replace(old, new, 1)

def main():
    text = API.read_text(encoding="utf-8", errors="replace")
    if "renderOfflineFb(live)" in text and "Array.isArray(d.offline_fb)" in text:
        print("ALREADY_PATCHED")
        return
    bak = Path(f"/root/backups/api.py.fb_panel.{time.strftime('%Y%m%d_%H%M%S')}")
    bak.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(API, bak)
    print("BACKUP", bak)
    text = must_replace(text,
'''      try{renderOfflineFb(d);}catch(eF){}
      try{renderOfflineBots(d);}catch(eB){}
      return;
    }
    window.__rvLastOffline = rows;
''',
'''      try{ if(d && Array.isArray(d.offline_fb)) renderOfflineFb(d); }catch(eF){}
      try{ if(d && Array.isArray(d.offline_bots)) renderOfflineBots(d); }catch(eB){}
      return;
    }
    window.__rvLastOffline = rows;
''', "empty")
    text = must_replace(text,
'''    try{renderOfflineFb(d);}catch(eF){}
    try{renderOfflineBots(d);}catch(eB){}
  }

    function renderLive(d){
''',
'''    try{ if(d && Array.isArray(d.offline_fb)) renderOfflineFb(d); }catch(eF){}
    try{ if(d && Array.isArray(d.offline_bots)) renderOfflineBots(d); }catch(eB){}
  }

    function renderLive(d){
''', "success")
    text = must_replace(text,
'''    fetchJson("/traffic/api/live").then(function(live){
      if(live.ok){
        renderLive(live);
        try{ loadRealVisitors({full: !window.__rvFetchedAt}); }catch(eOff){ var ob=$("offlineBox"); if(ob) ob.innerHTML="<p class='note'>No offline data.</p>"; }
''',
'''    fetchJson("/traffic/api/live").then(function(live){
      if(live.ok){
        renderLive(live);
        try{ renderOfflineFb(live); }catch(eF){}
        try{ renderOfflineBots(live); }catch(eB){}
        try{ loadRealVisitors({full: !window.__rvFetchedAt}); }catch(eOff){ var ob=$("offlineBox"); if(ob) ob.innerHTML="<p class='note'>No offline data.</p>"; }
''', "loadAll")
    text = must_replace(text,
'''    function renderLive(d){

    var rows=d.rows||[];
    if(!rows.length){$("liveBox").innerHTML="<p class='note'>Nobody active in the last "+(d.live_minutes||15)+" minutes."+(d.human_live!=null?(" · humans "+d.human_live+" / "+(d.human_pages||0)+" pages"):"")+"</p>"; return;}
''',
'''    function renderLive(d){

    var rows=d.rows||[];
    if(!rows.length){
      $("liveBox").innerHTML="<p class='note'>Nobody active in the last "+(d.live_minutes||15)+" minutes."+(d.human_live!=null?(" · humans "+d.human_live+" / "+(d.human_pages||0)+" pages"):"")+"</p>";
      try{ if(d && Array.isArray(d.offline_fb)) renderOfflineFb(d); }catch(eF){}
      try{ if(d && Array.isArray(d.offline_bots)) renderOfflineBots(d); }catch(eB){}
      return;
    }
''', "early")
    API.write_text(text, encoding="utf-8")
    print("OK")

if __name__ == "__main__":
    main()
