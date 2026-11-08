#!/usr/bin/env python3
"""Nuclear fix: inline onclick + style.display toggle; poll skips when any aria-expanded true."""
from __future__ import annotations

import py_compile
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    orig = text

    # Replace trailSetOpen / trailToggle / delegation with window-global simple API
    old_block_start = "  function trailSetOpen(k, wantOpen){"
    if old_block_start not in text:
        raise SystemExit("trailSetOpen missing")
    # from trailSetOpen through end of __trailDelegated block
    start = text.find(old_block_start)
    end_marker = "  if(!window.__trailDelegated){"
    end = text.find(end_marker, start)
    if end < 0:
        raise SystemExit("delegated block missing")
    # find closing of delegated if block - after `}, true);\n  }\n`
    end2 = text.find("}, true);\n  }\n", end)
    if end2 < 0:
        raise SystemExit("delegated end missing")
    end2 = end2 + len("}, true);\n  }\n")

    new_block = r'''  function trailSetOpen(k, wantOpen){
    if(!k) return;
    wantOpen=!!wantOpen;
    document.querySelectorAll("tr.live-trail").forEach(function(tr){
      if(tr.getAttribute("data-trail")!==k) return;
      tr.style.display = wantOpen ? "table-row" : "none";
      if(wantOpen) tr.classList.add("is-open"); else tr.classList.remove("is-open");
    });
    document.querySelectorAll("button.live-exp").forEach(function(btn){
      if(btn.getAttribute("data-trail")!==k) return;
      btn.setAttribute("aria-expanded", wantOpen ? "true" : "false");
      btn.textContent = wantOpen ? "▼" : "▶";
    });
    if(wantOpen) LIVE_TRAIL_OPEN[k]=true; else delete LIVE_TRAIL_OPEN[k];
    window.__liveTrailOpen = LIVE_TRAIL_OPEN;
  }
  function trailToggle(k){
    if(!k) return false;
    trailSetOpen(k, !LIVE_TRAIL_OPEN[k]);
    return false;
  }
  window.__ssaTrailToggle = trailToggle;
  function bindTrailToggleButtons(root){ /* noop — buttons use onclick=__ssaTrailToggle */ }
'''
    text = text[:start] + new_block + text[end2:]
    print("OK replaced delegation with window.__ssaTrailToggle")

    # Offline arrow: use onclick inline (most reliable on mobile WebKit)
    old_arrow = (
        "? (\"<button type='button' class='live-exp' data-trail='\"+esc(key)+\"' aria-expanded='\"+(isOpen?\"true\":\"false\")+\"'>\"+(isOpen?\"▼\":\"▶\")+\"</button> \")\n"
        "        : \"\";"
    )
    new_arrow = (
        "? (\"<button type='button' class='live-exp' data-trail='\"+esc(key)+\"' aria-expanded='\"+(isOpen?\"true\":\"false\")+\"' \"\n"
        "          +\"onclick=\\\"return window.__ssaTrailToggle(this.getAttribute('data-trail'))\\\" \"\n"
        "          +\">\"+(isOpen?\"▼\":\"▶\")+\"</button> \")\n"
        "        : \"\";"
    )
    # try exact from file
    old_arrow2 = (
        '        ? ("<button type=\'button\' class=\'live-exp\' data-trail=\'"+esc(key)+"\' aria-expanded=\'"+(isOpen?"true":"false")+"\'>"+(isOpen?"▼":"▶")+"</button> ")\n'
        '        : "";'
    )
    new_arrow2 = (
        '        ? ("<button type=\'button\' class=\'live-exp\' data-trail=\'"+esc(key)+"\' aria-expanded=\'"+(isOpen?"true":"false")+"\' "\n'
        '          +"onclick=\\"return window.__ssaTrailToggle(this.getAttribute(\'data-trail\'))\\">"+(isOpen?"▼":"▶")+"</button> ")\n'
        '        : "";'
    )
    if "window.__ssaTrailToggle(this.getAttribute" in text and text.count("window.__ssaTrailToggle(this.getAttribute") >= 1:
        # may need both offline and live
        pass
    if old_arrow2 in text:
        text = text.replace(old_arrow2, new_arrow2, 1)
        print("OK offline inline onclick")
    else:
        print("WARN offline arrow pattern missing")

    old_live_arrow = (
        '        ? ("<button type=\'button\' class=\'live-exp\' data-trail=\'"+keyAttr+"\' aria-expanded=\'"+(isOpen?"true":"false")+"\' aria-label=\'Show session pages\'>"+(isOpen?"▼":"▶")+"</button> ")\n'
        '        : "";'
    )
    new_live_arrow = (
        '        ? ("<button type=\'button\' class=\'live-exp\' data-trail=\'"+keyAttr+"\' aria-expanded=\'"+(isOpen?"true":"false")+"\' aria-label=\'Show session pages\' "\n'
        '          +"onclick=\\"return window.__ssaTrailToggle(this.getAttribute(\'data-trail\'))\\">"+(isOpen?"▼":"▶")+"</button> ")\n'
        '        : "";'
    )
    if old_live_arrow in text:
        text = text.replace(old_live_arrow, new_live_arrow, 1)
        print("OK live inline onclick")
    else:
        print("WARN live arrow pattern missing")

    # Trail rows: default style display none/table-row inline so CSS fights can't win
    old_tr = """html+="<tr class='live-trail"+(isOpen?" is-open":"")+"' data-trail='"+esc(key)+"'><td colspan='3'>"+thtml+"</td></tr>";"""
    new_tr = """html+="<tr class='live-trail"+(isOpen?" is-open":"")+"' data-trail='"+esc(key)+"' style='display:"+(isOpen?"table-row":"none")+"'><td colspan='3'>"+thtml+"</td></tr>";"""
    if old_tr in text:
        text = text.replace(old_tr, new_tr, 1)
        print("OK offline inline display style")
    else:
        print("WARN offline tr missing")

    old_tr_l = """html+="<tr class='live-trail"+(isOpen?" is-open":"")+"' data-trail='"+keyAttr+"'><td colspan='3'>"+thtml+"</td></tr>";"""
    new_tr_l = """html+="<tr class='live-trail"+(isOpen?" is-open":"")+"' data-trail='"+keyAttr+"' style='display:"+(isOpen?"table-row":"none")+"'><td colspan='3'>"+thtml+"</td></tr>";"""
    if old_tr_l in text:
        text = text.replace(old_tr_l, new_tr_l, 1)
        print("OK live inline display style")
    else:
        print("WARN live tr missing")

    # Make main row also toggle via onclick on tr - use data attribute + handler on box
    # Simpler: add onclick on the first td's badge area via button only for now

    # Poll freeze: also check aria-expanded in DOM (not just LIVE_TRAIL_OPEN memory)
    old_hold = """          var trailHold=Object.keys(LIVE_TRAIL_OPEN).some(function(k){ return !!LIVE_TRAIL_OPEN[k]; });
"""
    new_hold = """          var trailHold=Object.keys(LIVE_TRAIL_OPEN).some(function(k){ return !!LIVE_TRAIL_OPEN[k]; })
            || !!document.querySelector("#liveBox .live-exp[aria-expanded='true'], #offlineBox .live-exp[aria-expanded='true'], #offlineFbBox .live-exp[aria-expanded='true'], #offlineBotsBox .live-exp[aria-expanded='true']");
"""
    if old_hold in text:
        text = text.replace(old_hold, new_hold)
        print("OK trailHold also checks DOM aria-expanded")
    else:
        print("WARN trailHold pattern count", text.count("var trailHold=Object.keys"))

    # CSS: force open visibility
    if "tr.live-trail.is-open{display:table-row!important}" not in text:
        text = text.replace(
            "tr.live-trail.is-open{display:table-row}",
            "tr.live-trail.is-open{display:table-row!important}",
            1,
        )
        print("OK CSS !important open")

    if text != orig:
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print("OK compiled")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
