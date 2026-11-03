#!/usr/bin/env python3
"""Fix ▶ tap: event delegation + class toggle; stop refresh fighting show/hide."""
from __future__ import annotations

import py_compile
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    orig = text

    # --- 1) CSS: class-based trail visibility (hidden on <tr> is unreliable) ---
    old_css = ".live-trail td{background:#f8fafc;padding:8px 6px}"
    new_css = (
        "tr.live-trail{display:none}"
        "tr.live-trail.is-open{display:table-row}"
        ".live-trail td{background:#f8fafc;padding:8px 6px}"
        ".live-main{cursor:pointer}"
        ".live-exp{min-width:44px;min-height:44px}"
    )
    if "tr.live-trail.is-open" not in text:
        if old_css not in text:
            raise SystemExit("live-trail css missing")
        text = text.replace(old_css, new_css, 1)
        print("OK trail CSS class toggle")
    else:
        print("SKIP trail CSS")

    # --- 2) Replace bindTrailToggleButtons with document-level delegation (once) ---
    old_bind = """  function bindTrailToggleButtons(root){
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
          window.__liveTrailOpen=LIVE_TRAIL_OPEN;
        } else {
          row.setAttribute("hidden","");
          btn.setAttribute("aria-expanded","false");
          btn.textContent="▶";
          delete LIVE_TRAIL_OPEN[k];
          window.__liveTrailOpen=LIVE_TRAIL_OPEN;
        }
      });
    });
  }
"""
    new_bind = """  function trailSetOpen(k, wantOpen){
    if(!k) return;
    document.querySelectorAll("tr.live-trail[data-trail]").forEach(function(tr){
      if(tr.getAttribute("data-trail")!==k) return;
      if(wantOpen) tr.classList.add("is-open"); else tr.classList.remove("is-open");
      tr.removeAttribute("hidden");
    });
    document.querySelectorAll(".live-exp[data-trail]").forEach(function(btn){
      if(btn.getAttribute("data-trail")!==k) return;
      btn.setAttribute("aria-expanded", wantOpen?"true":"false");
      btn.textContent=wantOpen?"▼":"▶";
    });
    if(wantOpen) LIVE_TRAIL_OPEN[k]=true; else delete LIVE_TRAIL_OPEN[k];
    window.__liveTrailOpen=LIVE_TRAIL_OPEN;
  }
  function trailToggle(k){
    if(!k) return;
    trailSetOpen(k, !LIVE_TRAIL_OPEN[k]);
  }
  function bindTrailToggleButtons(root){ /* legacy no-op — delegation below */ }
  if(!window.__trailDelegated){
    window.__trailDelegated=true;
    document.addEventListener("click", function(ev){
      var t=ev.target;
      if(!t || !t.closest) return;
      // ignore real links inside trail
      if(t.closest("a[href]") && !t.closest(".live-exp")) return;
      var btn=t.closest(".live-exp[data-trail]");
      var main=t.closest("tr.live-main[data-trail]");
      var k=btn ? btn.getAttribute("data-trail") : (main ? main.getAttribute("data-trail") : null);
      if(!k) return;
      // only within traffic trail tables
      if(!t.closest("#liveBox, #offlineBox, #offlineFbBox, #offlineBotsBox")) return;
      ev.preventDefault();
      ev.stopPropagation();
      trailToggle(k);
    }, true);
  }
"""
    if "window.__trailDelegated" not in text:
        if old_bind not in text:
            # try without window.__liveTrailOpen lines (older)
            old_bind2 = old_bind.replace(
                "          LIVE_TRAIL_OPEN[k]=true;\n          window.__liveTrailOpen=LIVE_TRAIL_OPEN;\n",
                "          LIVE_TRAIL_OPEN[k]=true;\n",
            ).replace(
                "          delete LIVE_TRAIL_OPEN[k];\n          window.__liveTrailOpen=LIVE_TRAIL_OPEN;\n",
                "          delete LIVE_TRAIL_OPEN[k];\n",
            )
            if old_bind2 in text:
                text = text.replace(old_bind2, new_bind, 1)
                print("OK delegation toggle (alt bind)")
            else:
                raise SystemExit("bindTrailToggleButtons block missing")
        else:
            text = text.replace(old_bind, new_bind, 1)
            print("OK delegation toggle")
    else:
        print("SKIP delegation already")

    # --- 3) renderOfflineRows: use is-open class, not hidden attr ---
    old_trail_tr = """html+="<tr class='live-trail' data-trail='"+esc(key)+"'"+(isOpen?"":" hidden")+"><td colspan='3'>"+thtml+"</td></tr>";"""
    new_trail_tr = """html+="<tr class='live-trail"+(isOpen?" is-open":"")+"' data-trail='"+esc(key)+"'><td colspan='3'>"+thtml+"</td></tr>";"""
    if old_trail_tr in text:
        text = text.replace(old_trail_tr, new_trail_tr)
        print("OK offline trail is-open class")
    else:
        print("WARN offline trail tr pattern missing")

    # live renderLive trail row
    old_live_tr = """html+="<tr class='live-trail' data-trail='"+keyAttr+"'"+(isOpen?"":" hidden")+"><td colspan='3'>"+thtml+"</td></tr>";"""
    new_live_tr = """html+="<tr class='live-trail"+(isOpen?" is-open":"")+"' data-trail='"+keyAttr+"'><td colspan='3'>"+thtml+"</td></tr>";"""
    if old_live_tr in text:
        text = text.replace(old_live_tr, new_live_tr)
        print("OK live trail is-open class")
    else:
        print("WARN live trail tr pattern missing")

    # --- 4) Remove duplicate liveBox per-button binders (double-toggle = looks broken) ---
    old_live_bind = """    $("liveBox").querySelectorAll(".live-exp").forEach(function(btn){
      btn.addEventListener("click", function(ev){
        ev.preventDefault();
        ev.stopPropagation();
        var k=btn.getAttribute("data-trail");
        if(!k) return;
        var row=null;
        $("liveBox").querySelectorAll("tr.live-trail").forEach(function(tr){
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
"""
    if old_live_bind in text:
        text = text.replace(old_live_bind, "    /* trail clicks: document delegation */\n", 1)
        print("OK removed duplicate liveBox binders")
    else:
        # maybe already has window.__liveTrailOpen in bind
        old_live_bind2 = old_live_bind.replace(
            "          LIVE_TRAIL_OPEN[k]=true;\n",
            "          LIVE_TRAIL_OPEN[k]=true;\n          window.__liveTrailOpen=LIVE_TRAIL_OPEN;\n",
        ).replace(
            "          delete LIVE_TRAIL_OPEN[k];\n",
            "          delete LIVE_TRAIL_OPEN[k];\n          window.__liveTrailOpen=LIVE_TRAIL_OPEN;\n",
        )
        if old_live_bind2 in text:
            text = text.replace(old_live_bind2, "    /* trail clicks: document delegation */\n", 1)
            print("OK removed duplicate liveBox binders (alt)")
        else:
            print("WARN liveBox binder block missing")

    # --- 5) Poll: do not call renderOffline/renderLive at all while any trail open ---
    old_poll = """        if(live && live.ok){
          renderLive(live);
          try{renderOffline(live);}catch(eOff){}
          if(live.human_live!=null) $("kLive").textContent=String(live.human_live);
        }
"""
    new_poll = """        if(live && live.ok){
          var trailHold=Object.keys(LIVE_TRAIL_OPEN).some(function(k){ return !!LIVE_TRAIL_OPEN[k]; });
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
    if "var trailHold=Object.keys(LIVE_TRAIL_OPEN)" in text:
        print("SKIP poll trailHold")
    elif old_poll in text:
        text = text.replace(old_poll, new_poll, 1)
        print("OK poll freezes list while trail open")
    else:
        print("WARN poll block missing")

    # also the non-RANGE live branch
    old_poll2 = """    fetchJson("/traffic/api/live").then(function(d){ if(d.ok){ renderLive(d); try{renderOffline(d);}catch(eOff){} } }).catch(function(){});
"""
    new_poll2 = """    fetchJson("/traffic/api/live").then(function(d){
      if(!d.ok) return;
      var trailHold=Object.keys(LIVE_TRAIL_OPEN).some(function(k){ return !!LIVE_TRAIL_OPEN[k]; });
      if(trailHold){ if(d.human_live!=null) $("kLive").textContent=String(d.human_live); return; }
      renderLive(d); try{renderOffline(d);}catch(eOff){}
    }).catch(function(){});
"""
    if old_poll2 in text and "if(trailHold){ if(d.human_live!=null)" not in text:
        text = text.replace(old_poll2, new_poll2, 1)
        print("OK poll2 freezes while open")
    else:
        print("SKIP/WARN poll2")

    if text != orig:
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print("OK compiled")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
