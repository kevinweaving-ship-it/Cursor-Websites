#!/usr/bin/env python3
"""Rebuild Real visitors — since reset UI from scratch (isolated open state, no shared trail mess)."""
from __future__ import annotations

import py_compile
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

NEW_RENDER = r'''
  /* ==== Real visitors (rebuilt) — isolated from Live trail / poll mess ==== */
  window.__rvData = window.__rvData || {};
  window.__rvOpen = window.__rvOpen || {};
  function rvEsc(s){ return esc(s); }
  function rvBuildTrailTable(trail, meta){
    meta = meta || {};
    var bits=[];
    if(meta.ip) bits.push("IP "+rvEsc(meta.ip));
    if(meta.device_type) bits.push(rvEsc(meta.device_type));
    if(meta.browser) bits.push(rvEsc(meta.browser));
    var h="<div class='trail-meta'>"+(bits.join(" · ")||"Session pages")+"</div>";
    h+="<table class='trail'><thead><tr><th>URL</th><th>Arrived</th><th>Dwell</th></tr></thead><tbody>";
    (trail||[]).forEach(function(pt){
      var p=pt.path||"/";
      var lab=(p==="/"||p==="/index.html")?"home":p;
      var href=p.indexOf("/")===0?p:"";
      var cell=href?("<a href='"+rvEsc(href)+"'>"+rvEsc(lab)+"</a>"):rvEsc(lab);
      if(pt.engagement_label) cell+="<div class='trail-engage'>"+rvEsc(pt.engagement_label)+"</div>";
      h+="<tr><td>"+cell+"</td><td>"+rvEsc(String(pt.occurred_at||"").replace("T"," ").slice(0,19))+"</td><td class='dwell'>"+rvEsc(pt.dwell_label||"—")+"</td></tr>";
    });
    h+="</tbody></table>";
    return h;
  }
  function rvFind(box, sel, id){
    var nodes=box.querySelectorAll(sel), i;
    for(i=0;i<nodes.length;i++){ if(nodes[i].getAttribute("data-rvid")===id) return nodes[i]; }
    return null;
  }
  function rvSetOpen(id, open){
    var box=$("offlineBox");
    if(!box) return;
    var btn=rvFind(box, "button.rv-exp[data-rvid]", id);
    var panel=rvFind(box, "tr.rv-trail[data-rvid]", id);
    if(!btn || !panel) return;
    if(open){
      var pack=window.__rvData[id];
      if(pack && panel.getAttribute("data-filled")!=="1"){
        panel.innerHTML="<td colspan='3'>"+rvBuildTrailTable(pack.trail, pack.meta)+"</td>";
        panel.setAttribute("data-filled","1");
      }
      panel.style.display="table-row";
      btn.textContent="▼";
      btn.setAttribute("aria-expanded","true");
      btn.style.background="#ccfbf1";
      window.__rvOpen[id]=true;
    } else {
      panel.style.display="none";
      btn.textContent="▶";
      btn.setAttribute("aria-expanded","false");
      btn.style.background="transparent";
      delete window.__rvOpen[id];
    }
  }
  function rvToggle(id){
    rvSetOpen(id, !window.__rvOpen[id]);
  }
  if(!window.__rvClickWired){
    window.__rvClickWired=true;
    document.addEventListener("click", function(ev){
      var box=$("offlineBox");
      if(!box || !box.contains(ev.target)) return;
      var btn=ev.target.closest && ev.target.closest("button.rv-exp[data-rvid]");
      var row=(!btn && ev.target.closest) ? ev.target.closest("tr.rv-main[data-rvid]") : null;
      if(!btn && !row) return;
      if(ev.target.closest && ev.target.closest("a[href]") && !btn) return;
      var id=(btn||row).getAttribute("data-rvid");
      if(!id) return;
      ev.preventDefault();
      ev.stopPropagation();
      rvToggle(id);
    });
  }
  function renderOffline(d){
    var box=$("offlineBox");
    if(!box) return;
    var note=$("realSinceNote");
    if(note){
      var since=d && d.real_since ? String(d.real_since).replace("T"," ").slice(0,19) : "";
      note.textContent=(since?("Since reset "+since+" — "):"")+"every real visitor (scroll/click). All pages in trail. Nothing hidden if real.";
    }
    var rows=((d && d.offline)||[]).filter(function(r){ return r && r.kind!=="bot"; });
    if(!rows.length){
      box.innerHTML="<p class='note'>No real visitors since reset yet (need scroll or click).</p>";
      try{renderOfflineFb(d);}catch(eF){}
      try{renderOfflineBots(d);}catch(eB){}
      return;
    }
    window.__rvData={};
    var pages=0;
    rows.forEach(function(r){ pages += (r.pages_count!=null?r.pages_count:((r.page_trail||[]).length)); });
    var html="<div class='rv-toolbar'><p class='note' style='font-weight:700;margin:0;flex:1'>"+rows.length+" real visitor"+(rows.length===1?"":"s")+" · "+pages+" page"+(pages===1?"":"s")+" — tap ▶ for trail</p>";
    html+="<button type='button' id='rvRefreshBtn' class='rv-refresh'>Refresh</button></div>";
    html+="<div class='table-scroll'><table><thead><tr><th>Who</th><th>Last page / total</th><th>When done</th></tr></thead><tbody>";
    rows.forEach(function(r, idx){
      var id="rv_"+(r.ip||("i"+idx));
      var trail=Array.isArray(r.page_trail)?r.page_trail:[];
      window.__rvData[id]={trail:trail, meta:{ip:r.ip, device_type:r.device_type, browser:r.browser}};
      var badge=r.kind==="signed"?"signed":"anon";
      var badgeLabel=r.kind==="signed"?"staff":"guest";
      var who=rvEsc(r.who||(r.ip?(badgeLabel==="staff"?("Staff "+r.ip):("Guest "+r.ip)):badgeLabel));
      var n=r.pages_count!=null?r.pages_count:trail.length;
      var path=r.path||"—";
      var pathLab=(path==="/"||path==="/index.html")?"home":path;
      var pathHref=String(path).indexOf("/")===0?path:"";
      var pathHtml=pathHref?("<a href='"+rvEsc(pathHref)+"'>"+rvEsc(pathLab)+"</a>"):rvEsc(pathLab);
      var sess=r.session_dwell_label?(" · session "+rvEsc(r.session_dwell_label)):"";
      var when=String(r.last_activity||"").replace("T"," ").slice(0,19);
      var open=!!window.__rvOpen[id];
      var arrow=trail.length
        ? ("<button type='button' class='rv-exp' data-rvid='"+rvEsc(id)+"' aria-expanded='"+(open?"true":"false")+"' style='min-width:44px;min-height:44px;border:0;background:"+(open?"#ccfbf1":"transparent")+";font-weight:900;cursor:pointer'>"+(open?"▼":"▶")+"</button> ")
        : "";
      html+="<tr class='rv-main' data-rvid='"+rvEsc(id)+"'><td>"+arrow+"<span class='badge "+badge+"'>"+badgeLabel+"</span> "+who+" · done</td>";
      html+="<td>"+pathHtml+sess+" · "+n+"p</td><td>"+rvEsc(when)+"</td></tr>";
      if(trail.length){
        html+="<tr class='rv-trail' data-rvid='"+rvEsc(id)+"' style='display:"+(open?"table-row":"none")+"'><td colspan='3' class='note'>…</td></tr>";
      }
    });
    html+="</tbody></table></div>";
    box.innerHTML=html;
    // restore open panels after rebuild
    Object.keys(window.__rvOpen).forEach(function(id){ if(window.__rvOpen[id]) rvSetOpen(id, true); });
    var rb=$("rvRefreshBtn");
    if(rb){
      rb.addEventListener("click", function(ev){
        ev.preventDefault();
        ev.stopPropagation();
        rb.disabled=true; rb.textContent="…";
        fetchJson("/traffic/api/live").then(function(d){
          if(d && d.ok) renderOffline(d);
        }).catch(function(){}).then(function(){ try{ rb.disabled=false; rb.textContent="Refresh"; }catch(eR){} });
      });
    }
    try{renderOfflineFb(d);}catch(eF){}
    try{renderOfflineBots(d);}catch(eB){}
  }
'''

CSS_ADD = """
.rv-toolbar{display:flex;align-items:center;gap:8px;margin:0 0 8px;flex-wrap:wrap}
.rv-refresh{min-height:36px;padding:0 12px;border:2px solid var(--navy);background:#fff;color:var(--navy);border-radius:8px;font-weight:800;cursor:pointer}
.rv-trail td{background:#f8fafc;padding:8px 6px}
tr.rv-main{cursor:pointer}
"""


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    orig = text

    # CSS once
    if ".rv-toolbar{" not in text:
        anchor = "tr.live-trail{display:none}"
        if anchor in text:
            text = text.replace(anchor, CSS_ADD + anchor, 1)
            print("OK css")
        else:
            # insert before .err{
            if ".err{color:#b91c1c" in text:
                text = text.replace(".err{color:#b91c1c", CSS_ADD + ".err{color:#b91c1c", 1)
                print("OK css via .err")
            else:
                raise SystemExit("css anchor missing")

    # Replace from anyOfflineTrailOpen OR old renderOffline through end of renderOffline function
    start = text.find("function anyOfflineTrailOpen()")
    if start < 0:
        start = text.find("  function renderOffline(d){")
    if start < 0:
        raise SystemExit("renderOffline start missing")
    # Include prior helper offlineRowsFingerprint if present right before
    fp = text.rfind("function offlineRowsFingerprint", max(0, start - 800), start)
    if fp >= 0:
        start = fp

    end = text.find("  function renderLive(d){", start)
    if end < 0:
        raise SystemExit("renderLive after offline missing")

    text = text[:start] + NEW_RENDER + "\n  " + text[end:]
    print("OK replaced Real visitors renderer")

    # Remove trailHold / anyOffline references that break — poll already numbers-only
    # Ensure loadAll still calls renderOffline(live)
    if "renderOffline(live)" not in text:
        raise SystemExit("loadAll must still call renderOffline")

    # HTML: add hint that Refresh exists (toolbar has button)
    old_h = '<h2>Real visitors — since reset</h2>'
    new_h = '<h2>Real visitors — since reset</h2>'
    # unchanged title

    if text != orig:
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print("OK compiled")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
