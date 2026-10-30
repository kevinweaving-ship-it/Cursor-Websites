#!/usr/bin/env python3
"""Traffic UI: keep show/hide toggle state across poll updates (don't reset)."""
from __future__ import annotations

import py_compile
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    orig = text

    # 1) Don't drop sticky open when trail briefly empty (timeout / aborted txn)
    old_drop = """      } else if(LIVE_TRAIL_OPEN[key]){
        // session gone / no trail yet — drop sticky open
        delete LIVE_TRAIL_OPEN[key];
      }
"""
    new_drop = """      }
      // Keep LIVE_TRAIL_OPEN sticky across polls (empty trail = timeout, not user hide)
"""
    if "Keep LIVE_TRAIL_OPEN sticky across polls" not in text:
        if old_drop not in text:
            raise SystemExit("drop-open block missing")
        text = text.replace(old_drop, new_drop, 1)
        print("OK sticky trail open")
    else:
        print("SKIP sticky already")

    # 2) Persist FB/bots section toggles on window; re-apply after render
    old_fb_vars = """  var OFFLINE_BOTS_OPEN=false;
  function renderOfflineRows(rows, keyPrefix){
"""
    # There may be two OFFLINE_BOTS_OPEN decls - normalize to window
    text2 = text
    if "window.__offlineFbOpen" not in text:
        text2 = text2.replace(
            "  var OFFLINE_FB_OPEN=false;\n  (function wireOfflineFbToggle(){",
            "  var OFFLINE_FB_OPEN=!!window.__offlineFbOpen;\n"
            "  var OFFLINE_BOTS_OPEN=!!window.__offlineBotsOpen;\n"
            "  (function wireOfflineFbToggle(){",
            1,
        )
        # remove early duplicate OFFLINE_BOTS_OPEN=false if still present before renderOfflineRows
        text2 = text2.replace(
            "  var OFFLINE_BOTS_OPEN=false;\n  function renderOfflineRows(rows, keyPrefix){",
            "  function renderOfflineRows(rows, keyPrefix){",
            1,
        )
        text = text2
        print("OK window-persisted section toggles")
    else:
        print("SKIP section toggles already on window")

    old_fb_click = """    btn.addEventListener("click", function(){
      OFFLINE_FB_OPEN=!OFFLINE_FB_OPEN;
      box.hidden=!OFFLINE_FB_OPEN;
      btn.textContent=OFFLINE_FB_OPEN?"▼":"▶";
      btn.setAttribute("aria-expanded", OFFLINE_FB_OPEN?"true":"false");
    });
"""
    new_fb_click = """    btn.addEventListener("click", function(){
      OFFLINE_FB_OPEN=!OFFLINE_FB_OPEN;
      window.__offlineFbOpen=OFFLINE_FB_OPEN;
      box.hidden=!OFFLINE_FB_OPEN;
      btn.textContent=OFFLINE_FB_OPEN?"▼":"▶";
      btn.setAttribute("aria-expanded", OFFLINE_FB_OPEN?"true":"false");
    });
"""
    if "window.__offlineFbOpen=OFFLINE_FB_OPEN" not in text:
        if old_fb_click not in text:
            raise SystemExit("fb click missing")
        text = text.replace(old_fb_click, new_fb_click, 1)
        print("OK fb toggle persists")
    else:
        print("SKIP fb persist click")

    old_bot_click = """    btn.addEventListener("click", function(){
      OFFLINE_BOTS_OPEN=!OFFLINE_BOTS_OPEN;
      box.hidden=!OFFLINE_BOTS_OPEN;
      btn.textContent=OFFLINE_BOTS_OPEN?"▼":"▶";
      btn.setAttribute("aria-expanded", OFFLINE_BOTS_OPEN?"true":"false");
    });
"""
    new_bot_click = """    btn.addEventListener("click", function(){
      OFFLINE_BOTS_OPEN=!OFFLINE_BOTS_OPEN;
      window.__offlineBotsOpen=OFFLINE_BOTS_OPEN;
      box.hidden=!OFFLINE_BOTS_OPEN;
      btn.textContent=OFFLINE_BOTS_OPEN?"▼":"▶";
      btn.setAttribute("aria-expanded", OFFLINE_BOTS_OPEN?"true":"false");
    });
"""
    if "window.__offlineBotsOpen=OFFLINE_BOTS_OPEN" not in text:
        if old_bot_click not in text:
            raise SystemExit("bots click missing")
        text = text.replace(old_bot_click, new_bot_click, 1)
        print("OK bots toggle persists")
    else:
        print("SKIP bots persist click")

    # 3) After renderOfflineFb/Bots, re-apply section hidden from saved toggle
    old_fb_render_end = """    box.innerHTML=renderOfflineRows(rows, "offfb");
    bindTrailToggleButtons(box);
  }
  function renderOfflineBots(d){
"""
    new_fb_render_end = """    box.innerHTML=renderOfflineRows(rows, "offfb");
    bindTrailToggleButtons(box);
    OFFLINE_FB_OPEN=!!window.__offlineFbOpen;
    box.hidden=!OFFLINE_FB_OPEN;
    var tbtn=$("offlineFbToggle");
    if(tbtn){ tbtn.textContent=OFFLINE_FB_OPEN?"▼":"▶"; tbtn.setAttribute("aria-expanded", OFFLINE_FB_OPEN?"true":"false"); }
  }
  function renderOfflineBots(d){
"""
    if 'OFFLINE_FB_OPEN=!!window.__offlineFbOpen' not in text.split("function renderOfflineFb", 1)[-1][:800]:
        if old_fb_render_end not in text:
            raise SystemExit("fb render end missing")
        text = text.replace(old_fb_render_end, new_fb_render_end, 1)
        print("OK re-apply fb section state after render")
    else:
        print("SKIP fb re-apply")

    old_bot_render_end = """    box.innerHTML=renderOfflineRows(rows, "offbot");
    bindTrailToggleButtons(box);
  }
    function renderOffline(d){
"""
    new_bot_render_end = """    box.innerHTML=renderOfflineRows(rows, "offbot");
    bindTrailToggleButtons(box);
    OFFLINE_BOTS_OPEN=!!window.__offlineBotsOpen;
    box.hidden=!OFFLINE_BOTS_OPEN;
    var tbtn2=$("offlineBotsToggle");
    if(tbtn2){ tbtn2.textContent=OFFLINE_BOTS_OPEN?"▼":"▶"; tbtn2.setAttribute("aria-expanded", OFFLINE_BOTS_OPEN?"true":"false"); }
  }
    function renderOffline(d){
"""
    if 'OFFLINE_BOTS_OPEN=!!window.__offlineBotsOpen' not in text.split("function renderOfflineBots", 1)[-1][:800]:
        if old_bot_render_end not in text:
            # try without extra indent
            old_bot_render_end2 = """    box.innerHTML=renderOfflineRows(rows, "offbot");
    bindTrailToggleButtons(box);
  }
  function renderOffline(d){
"""
            new_bot_render_end2 = """    box.innerHTML=renderOfflineRows(rows, "offbot");
    bindTrailToggleButtons(box);
    OFFLINE_BOTS_OPEN=!!window.__offlineBotsOpen;
    box.hidden=!OFFLINE_BOTS_OPEN;
    var tbtn2=$("offlineBotsToggle");
    if(tbtn2){ tbtn2.textContent=OFFLINE_BOTS_OPEN?"▼":"▶"; tbtn2.setAttribute("aria-expanded", OFFLINE_BOTS_OPEN?"true":"false"); }
  }
  function renderOffline(d){
"""
            if old_bot_render_end2 in text:
                text = text.replace(old_bot_render_end2, new_bot_render_end2, 1)
                print("OK re-apply bots section state")
            else:
                raise SystemExit("bots render end missing")
        else:
            text = text.replace(old_bot_render_end, new_bot_render_end, 1)
            print("OK re-apply bots section state")
    else:
        print("SKIP bots re-apply")

    # 4) Poll: use human_live for card; don't flash Loading
    old_poll = """        if(live && live.ok){ renderLive(live); try{renderOffline(live);}catch(eOff){} }
"""
    new_poll = """        if(live && live.ok){
          renderLive(live);
          try{renderOffline(live);}catch(eOff){}
          if(live.human_live!=null) $("kLive").textContent=String(live.human_live);
        }
"""
    if 'if(live.human_live!=null) $("kLive").textContent=String(live.human_live)' in text:
        print("SKIP poll human_live")
    elif old_poll in text:
        text = text.replace(old_poll, new_poll, 1)
        print("OK poll preserves human_live card")
    else:
        print("WARN poll live block missing (may already differ)")

    # 4b) Empty FB/bots lists still re-apply section open state
    old_fb_empty = """    if(!rows.length){ box.innerHTML="<p class='note'>No Facebook share crawls since reset.</p>"; return; }
"""
    new_fb_empty = """    if(!rows.length){
      box.innerHTML="<p class='note'>No Facebook share crawls since reset.</p>";
      OFFLINE_FB_OPEN=!!window.__offlineFbOpen;
      box.hidden=!OFFLINE_FB_OPEN;
      var tbtnE=$("offlineFbToggle");
      if(tbtnE){ tbtnE.textContent=OFFLINE_FB_OPEN?"▼":"▶"; tbtnE.setAttribute("aria-expanded", OFFLINE_FB_OPEN?"true":"false"); }
      return;
    }
"""
    if "No Facebook share crawls since reset" in text and "tbtnE" not in text:
        if old_fb_empty in text:
            text = text.replace(old_fb_empty, new_fb_empty, 1)
            print("OK fb empty re-apply")
        else:
            print("WARN fb empty block missing")

    old_bot_empty = """    if(!rows.length){ box.innerHTML="<p class='note'>No other bots in lookback.</p>"; return; }
"""
    new_bot_empty = """    if(!rows.length){
      box.innerHTML="<p class='note'>No other bots in lookback.</p>";
      OFFLINE_BOTS_OPEN=!!window.__offlineBotsOpen;
      box.hidden=!OFFLINE_BOTS_OPEN;
      var tbtnE2=$("offlineBotsToggle");
      if(tbtnE2){ tbtnE2.textContent=OFFLINE_BOTS_OPEN?"▼":"▶"; tbtnE2.setAttribute("aria-expanded", OFFLINE_BOTS_OPEN?"true":"false"); }
      return;
    }
"""
    if "No other bots in lookback" in text and "tbtnE2" not in text:
        if old_bot_empty in text:
            text = text.replace(old_bot_empty, new_bot_empty, 1)
            print("OK bots empty re-apply")
        else:
            print("WARN bots empty block missing")

    # 5) loadAll: only show Loading on first paint / range change, not when boxes already have content
    old_load = """    $("liveBox").innerHTML="<p class='note'>Loading…</p>";
    $("topBox").innerHTML="<p class='note'>Loading…</p>";
"""
    new_load = """    // Don't wipe open trails / toggles — only placeholder if empty
    if(!$("liveBox").querySelector("table")) $("liveBox").innerHTML="<p class='note'>Loading…</p>";
    if(!$("topBox").querySelector("table") && !$("topBox").querySelector(".table-scroll")) $("topBox").innerHTML="<p class='note'>Loading…</p>";
"""
    if "Don't wipe open trails" not in text:
        if old_load not in text:
            print("WARN loadAll wipe not found")
        else:
            text = text.replace(old_load, new_load, 1)
            print("OK loadAll no wipe if content exists")
    else:
        print("SKIP loadAll wipe")

    # 6) Stable offline trail keys — prefer ip always
    old_key = """      var key=keyPrefix+":"+(r.ip||r.visitor_id||who);
"""
    new_key = """      var key=keyPrefix+":"+(r.ip||r.visitor_id||r.session_id||who);
"""
    if old_key in text:
        text = text.replace(old_key, new_key, 1)
        print("OK stabler offline keys")

    if text != orig:
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print("OK compiled")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
