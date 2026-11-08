#!/usr/bin/env python3
"""Show home/landing dwell on Live main row; treat / as a real human page."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-home-dwell-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text
    changes = []

    # 1) human_pass: landing / is a real page (document), not "untrackable"
    old_pass = '''def _lean_human_traffic_pass(user_agent: str, path: Optional[str] = None) -> bool:
    """Valid clickable page + real browser UA => treat as real traffic (not bot)."""
    if not _is_human_browser_ua(user_agent):
        return False
    if path is None or path == "":
        return True
    try:
        return bool(_is_trackable_page_path(path))
    except Exception:
        p = (path or "").split("?", 1)[0]
        return p.startswith("/") and not p.startswith("/api/") and not p.startswith("/wp-")
'''
    new_pass = '''def _lean_human_traffic_pass(user_agent: str, path: Optional[str] = None) -> bool:
    """Valid clickable page + real browser UA => treat as real traffic (not bot).

    Landing `/` counts — visitors must get a chance to click through from home.
    """
    if not _is_human_browser_ua(user_agent):
        return False
    if path is None or path == "":
        return True
    try:
        # Home/landing is a real document stay (dwell shown in Live); not "noise".
        if _is_document_page_path_for_hit(path):
            return True
        return bool(_is_trackable_page_path(path))
    except Exception:
        p = (path or "").split("?", 1)[0]
        return p.startswith("/") and not p.startswith("/api/") and not p.startswith("/wp-")
'''
    if old_pass not in text:
        if "Landing `/` counts" in text:
            changes.append("human_pass already allows landing")
        else:
            raise SystemExit("human_pass block not found")
    else:
        text = text.replace(old_pass, new_pass, 1)
        changes.append("human_pass allows home/landing")

    # 2) Live UI: show dwell on main Page cell; label / as home
    old_js = '''      var path=r.path||"—";
      var link=r.href?("<a href='"+esc(r.href)+"'>"+esc(path)+"</a>"):esc(path);
      var when=(r.last_activity||"").replace("T"," ").slice(0,19);'''
    new_js = '''      var path=r.path||"—";
      var pathLabel=(path==="/"||path==="/index.html")?"home":path;
      var trail=Array.isArray(r.page_trail)?r.page_trail:[];
      var dwellNow="";
      for(var ti=trail.length-1;ti>=0;ti--){
        var tp=trail[ti]||{};
        var tpath=tp.path||"";
        if(tpath===path || ((path==="/"||path==="/index.html")&&(tpath==="/"||tpath==="/index.html"))){
          dwellNow=tp.dwell_label||"";
          break;
        }
      }
      if(!dwellNow && trail.length){
        var last=trail[trail.length-1]||{};
        if((last.path||"")===path || path==="/"||path==="/index.html") dwellNow=last.dwell_label||"";
      }
      var link=r.href?("<a href='"+esc(r.href)+"'>"+esc(pathLabel)+"</a>"):esc(pathLabel);
      if(dwellNow) link+=" <span class='dwell'>· "+esc(dwellNow)+"</span>";
      var when=(r.last_activity||"").replace("T"," ").slice(0,19);'''
    if old_js not in text:
        raise SystemExit("live path/link js not found")
    text = text.replace(old_js, new_js, 1)
    changes.append("live main row shows page dwell + home label")

    # Avoid double `var trail=` — the later declaration becomes assignment or remove duplicate
    old_trail_decl = '''      var trail=Array.isArray(r.page_trail)?r.page_trail:[];
      var nPages=r.pages_count!=null?r.pages_count:trail.length;'''
    new_trail_decl = '''      // trail already resolved above for dwell
      var nPages=r.pages_count!=null?r.pages_count:trail.length;'''
    if old_trail_decl not in text:
        raise SystemExit("duplicate trail decl not found")
    text = text.replace(old_trail_decl, new_trail_decl, 1)

    # Trail table: show home label for /
    old_trail_row = '''        trail.forEach(function(pt){
          var p=pt.path||"/";
          var href=p.indexOf("/")===0?p:"";
          var pl=href?("<a href='"+esc(href)+"'>"+esc(p)+"</a>"):esc(p);'''
    new_trail_row = '''        trail.forEach(function(pt){
          var p=pt.path||"/";
          var pLab=(p==="/"||p==="/index.html")?"home":p;
          var href=p.indexOf("/")===0?p:"";
          var pl=href?("<a href='"+esc(href)+"'>"+esc(pLab)+"</a>"):esc(pLab);'''
    if old_trail_row not in text:
        raise SystemExit("trail row js not found")
    text = text.replace(old_trail_row, new_trail_row, 1)
    changes.append("trail lists home label")

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print("OK:", "; ".join(changes))


if __name__ == "__main__":
    main()
