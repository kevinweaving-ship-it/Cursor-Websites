from pathlib import Path
import py_compile, shutil
from datetime import datetime, timezone

API = Path("/var/www/sailingsa/api/api.py")
stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
shutil.copy2(API, API.with_suffix(f".bak-off-bind-{stamp}"))
text = API.read_text(encoding="utf-8")

# 1) Add bindTrailToggleButtons after LIVE_TRAIL_OPEN definition
anchor = "var LIVE_TRAIL_OPEN = window.__liveTrailOpen || (window.__liveTrailOpen = {});"
if "function bindTrailToggleButtons" not in text:
    if anchor not in text:
        raise SystemExit("LIVE_TRAIL_OPEN missing")
    helper = anchor + r'''
  function bindTrailToggleButtons(root){
    if(!root) return;
    root.querySelectorAll(".live-exp[data-trail]").forEach(function(btn){
      if(btn._trailBound) return;
      btn._trailBound=true;
      btn.addEventListener("click", function(ev){
        ev.preventDefault();
        ev.stopPropagation();
        var k=btn.getAttribute("data-trail");
        if(!k) return;
        var row=null;
        root.querySelectorAll("tr.live-trail").forEach(function(tr){
          if(tr.getAttribute("data-trail")===k) row=tr;
        });
        if(!row) return;
        var open=row.hasAttribute("hidden");
        if(open){
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
      });
    });
  }
'''
    text = text.replace(anchor, helper, 1)

# 2) After renderOffline sets innerHTML, bind + clear sticky off: opens so default is hide
old_ro = '''      var summary="<p class='note' style='font-weight:700;margin:0 0 8px'>"+rows.length+" visitor"+(rows.length===1?"":"s")+" · "+pages+" URL"+(pages===1?"":"s")+" — tap ▶ to show/hide each URL trail</p>";
      box.innerHTML=summary+renderOfflineRows(rows, "off");
    }
    try{renderOfflineBots(d);}catch(eB){}
  }'''
new_ro = '''      // Default hide: clear sticky open for offline guests so trails start collapsed
      Object.keys(LIVE_TRAIL_OPEN).forEach(function(k){ if(k.indexOf("off:")===0) delete LIVE_TRAIL_OPEN[k]; });
      var summary="<p class='note' style='font-weight:700;margin:0 0 8px'>"+rows.length+" visitor"+(rows.length===1?"":"s")+" · "+pages+" URL"+(pages===1?"":"s")+" — tap ▶ to show/hide URLs</p>";
      box.innerHTML=summary+renderOfflineRows(rows, "off");
      bindTrailToggleButtons(box);
    }
    try{renderOfflineBots(d);}catch(eB){}
  }'''
if old_ro not in text:
    raise SystemExit("renderOffline block not found")
text = text.replace(old_ro, new_ro, 1)

# 3) bind on bots panel too
old_bots = '''    if(!rows.length){ box.innerHTML="<p class='note'>No quarantined bots in the last 24h.</p>"; return; }
    box.innerHTML=renderOfflineRows(rows, "offbot");
  }'''
new_bots = '''    if(!rows.length){ box.innerHTML="<p class='note'>No quarantined bots in the last 24h.</p>"; return; }
    Object.keys(LIVE_TRAIL_OPEN).forEach(function(k){ if(k.indexOf("offbot:")===0) delete LIVE_TRAIL_OPEN[k]; });
    box.innerHTML=renderOfflineRows(rows, "offbot");
    bindTrailToggleButtons(box);
  }'''
if old_bots not in text:
    print("WARN bots bind skipped", "renderOfflineBots" in text)
else:
    text = text.replace(old_bots, new_bots, 1)

# 4) Optionally use bindTrailToggleButtons in renderLive too (keep existing; or replace)
# Leave live as-is for safety.

API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print("OK offline trail toggle bind")
