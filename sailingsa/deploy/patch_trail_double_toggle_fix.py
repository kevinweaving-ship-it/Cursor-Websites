#!/usr/bin/env python3
"""Fix dead ▶ (double toggle) + Real visitors empty flicker (API [] wipe)."""
from __future__ import annotations

import py_compile
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    orig = text

    # 1) REMOVE inline onclick — keep only document listener (one toggle per tap)
    old_onclick_off = (
        '        ? ("<button type=\'button\' class=\'live-exp\' data-trail=\'"+esc(key)+"\' aria-expanded=\'"+(isOpen?"true":"false")+"\' "\n'
        '          +"onclick=\\"return window.__ssaTrailToggle(this.getAttribute(\'data-trail\'))\\">"+(isOpen?"▼":"▶")+"</button> ")\n'
        '        : "";'
    )
    new_onclick_off = (
        '        ? ("<button type=\'button\' class=\'live-exp\' data-trail=\'"+esc(key)+"\' aria-expanded=\'"+(isOpen?"true":"false")+"\'>"+(isOpen?"▼":"▶")+"</button> ")\n'
        '        : "";'
    )
    if old_onclick_off in text:
        text = text.replace(old_onclick_off, new_onclick_off, 1)
        print("OK removed offline inline onclick")
    else:
        print("WARN offline onclick pattern missing")

    old_onclick_live = (
        '        ? ("<button type=\'button\' class=\'live-exp\' data-trail=\'"+keyAttr+"\' aria-expanded=\'"+(isOpen?"true":"false")+"\' aria-label=\'Show session pages\' "\n'
        '          +"onclick=\\"return window.__ssaTrailToggle(this.getAttribute(\'data-trail\'))\\">"+(isOpen?"▼":"▶")+"</button> ")\n'
        '        : "";'
    )
    new_onclick_live = (
        '        ? ("<button type=\'button\' class=\'live-exp\' data-trail=\'"+keyAttr+"\' aria-expanded=\'"+(isOpen?"true":"false")+"\' aria-label=\'Show session pages\'>"+(isOpen?"▼":"▶")+"</button> ")\n'
        '        : "";'
    )
    if old_onclick_live in text:
        text = text.replace(old_onclick_live, new_onclick_live, 1)
        print("OK removed live inline onclick")
    else:
        print("WARN live onclick pattern missing")

    # 2) Do NOT wipe Real visitors to empty on a blank poll — keep existing table
    old_empty = """    if(!rows.length){
      box.innerHTML="<p class='note'>No real visitors since reset yet (need scroll or click).</p>";
    } else {
"""
    new_empty = """    if(!rows.length){
      // Do not flash empty on a failed/partial poll if we already have a list
      if(!box.querySelector("table")){
        box.innerHTML="<p class='note'>No real visitors since reset yet (need scroll or click).</p>";
      }
      try{renderOfflineFb(d);}catch(eF){}
      try{renderOfflineBots(d);}catch(eB){}
      return;
    } else {
"""
    if "Do not flash empty on a failed/partial poll" in text:
        print("SKIP empty wipe guard")
    elif old_empty in text:
        text = text.replace(old_empty, new_empty, 1)
        print("OK no empty wipe over existing table")
    else:
        print("WARN empty block missing")

    # 3) Mark delegation as the only path; stopImmediatePropagation so nothing else double-fires
    old_del = """    document.addEventListener("click", function(ev){
      var el=ev.target && ev.target.closest && ev.target.closest("button.live-exp[data-trail], tr.live-main[data-trail]");
      if(!el) return;
      if(!el.closest("#liveBox, #offlineBox, #offlineFbBox, #offlineBotsBox")) return;
      if(el.closest("a[href]") && el.tagName!=="BUTTON") return;
      var k=el.getAttribute("data-trail");
      if(!k) return;
      ev.preventDefault();
      ev.stopPropagation();
      trailToggle(k);
    });
"""
    new_del = """    document.addEventListener("click", function(ev){
      var el=ev.target && ev.target.closest && ev.target.closest("button.live-exp[data-trail], tr.live-main[data-trail]");
      if(!el) return;
      if(!el.closest("#liveBox, #offlineBox, #offlineFbBox, #offlineBotsBox")) return;
      if(el.tagName!=="BUTTON" && ev.target.closest && ev.target.closest("a[href]")) return;
      var k=el.getAttribute("data-trail");
      if(!k) return;
      // Ignore FB/bots section header buttons (class live-exp but no data-trail) — already filtered
      ev.preventDefault();
      ev.stopPropagation();
      if(ev.stopImmediatePropagation) ev.stopImmediatePropagation();
      trailToggle(k);
    }, false);
"""
    if "stopImmediatePropagation) ev.stopImmediatePropagation" in text:
        print("SKIP delegation harden")
    elif old_del in text:
        text = text.replace(old_del, new_del, 1)
        print("OK single delegation hardened")
    else:
        print("WARN delegation block missing")

    if text != orig:
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print("OK compiled")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
