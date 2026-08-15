#!/usr/bin/env python3
"""Lazy trail expand: don't bake 200+ page tables into hidden rows; build on tap."""
from __future__ import annotations

import py_compile
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    text = API.read_text(encoding="utf-8", errors="replace")
    orig = text

    # Replace trailSetOpen to lazy-render from window.__trailData
    old = """  function trailSetOpen(k, wantOpen){
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
"""
    new = """  window.__trailData = window.__trailData || {};
  function buildTrailHtml(meta, trail){
    var metaBits=[];
    if(meta.ip) metaBits.push("IP "+esc(meta.ip));
    if(meta.device_type) metaBits.push(esc(meta.device_type));
    if(meta.browser) metaBits.push(esc(meta.browser));
    if(meta.quarantined) metaBits.push("quarantined");
    var thtml="<div class='trail-meta'>"+(metaBits.join(" · ")||"Session pages")+"</div>";
    thtml+="<table class='trail'><thead><tr><th>URL</th><th>Arrived</th><th>Dwell</th></tr></thead><tbody>";
    (trail||[]).forEach(function(pt){
      var p=pt.path||"/";
      var pLab=(p==="/"||p==="/index.html")?"home":p;
      var href=p.indexOf("/")===0?p:"";
      var pl=href?("<a href='"+esc(href)+"'>"+esc(pLab)+"</a>"):esc(pLab);
      var eg=(pt.engagement_label||"");
      if(eg) pl+="<div class='trail-engage'>"+esc(eg)+"</div>";
      var arr=(pt.occurred_at||"").replace("T"," ").slice(0,19);
      var dw=esc(pt.dwell_label||"—");
      thtml+="<tr><td>"+pl+"</td><td>"+esc(arr)+"</td><td class='dwell'>"+dw+"</td></tr>";
    });
    thtml+="</tbody></table>";
    return thtml;
  }
  function trailSetOpen(k, wantOpen){
    if(!k) return;
    wantOpen=!!wantOpen;
    document.querySelectorAll("tr.live-trail").forEach(function(tr){
      if(tr.getAttribute("data-trail")!==k) return;
      if(wantOpen){
        var pack=window.__trailData[k];
        if(pack && !tr.getAttribute("data-filled")){
          tr.innerHTML="<td colspan='3'>"+buildTrailHtml(pack.meta||{}, pack.trail||[])+"</td>";
          tr.setAttribute("data-filled","1");
        }
        tr.style.display="table-row";
        tr.classList.add("is-open");
      } else {
        tr.style.display="none";
        tr.classList.remove("is-open");
      }
    });
    document.querySelectorAll("button.live-exp").forEach(function(btn){
      if(btn.getAttribute("data-trail")!==k) return;
      btn.setAttribute("aria-expanded", wantOpen ? "true" : "false");
      btn.textContent = wantOpen ? "▼" : "▶";
      btn.style.background = wantOpen ? "#ccfbf1" : "transparent";
    });
    if(wantOpen) LIVE_TRAIL_OPEN[k]=true; else delete LIVE_TRAIL_OPEN[k];
    window.__liveTrailOpen = LIVE_TRAIL_OPEN;
  }
"""
    if "window.__trailData = window.__trailData" in text and "data-filled" in text:
        print("SKIP lazy trailSetOpen already")
    elif old not in text:
        raise SystemExit("trailSetOpen block missing")
    else:
        text = text.replace(old, new, 1)
        print("OK lazy trailSetOpen")

    # Replace renderOfflineRows trail embedding with store + empty placeholder
    old_rows_trail = """      if(trail.length){
        var metaBits=[];
        if(r.ip) metaBits.push("IP "+esc(r.ip));
        if(r.device_type) metaBits.push(esc(r.device_type));
        if(r.browser) metaBits.push(esc(r.browser));
        if(r.quarantined) metaBits.push("quarantined");
        var thtml="<div class='trail-meta'>"+(metaBits.join(" · ")||"Session pages")+"</div>";
        thtml+="<table class='trail'><thead><tr><th>URL</th><th>Arrived</th><th>Dwell</th></tr></thead><tbody>";
        trail.forEach(function(pt){
          var p=pt.path||"/";
          var pLab=(p==="/"||p==="/index.html")?"home":p;
          var href=p.indexOf("/")===0?p:"";
          var pl=href?("<a href='"+esc(href)+"'>"+esc(pLab)+"</a>"):esc(pLab);
          var eg=(pt.engagement_label||"");
          if(eg) pl+="<div class='trail-engage'>"+esc(eg)+"</div>";
          var arr=(pt.occurred_at||"").replace("T"," ").slice(0,19);
          var dw=esc(pt.dwell_label||"—");
          thtml+="<tr><td>"+pl+"</td><td>"+esc(arr)+"</td><td class='dwell'>"+dw+"</td></tr>";
        });
        thtml+="</tbody></table>";
        html+="<tr class='live-trail"+(isOpen?" is-open":"")+"' data-trail='"+esc(key)+"' style='display:"+(isOpen?"table-row":"none")+"'><td colspan='3'>"+thtml+"</td></tr>";
      }
"""
    new_rows_trail = """      if(trail.length){
        window.__trailData[key]={meta:{ip:r.ip,device_type:r.device_type,browser:r.browser,quarantined:r.quarantined},trail:trail};
        html+="<tr class='live-trail"+(isOpen?" is-open":"")+"' data-trail='"+esc(key)+"' style='display:"+(isOpen?"table-row":"none")+"'><td colspan='3' class='note'>…</td></tr>";
        if(isOpen){
          /* fill immediately when sticky-open */
        }
      }
"""
    if "window.__trailData[key]={meta:" in text and "renderOfflineRows" in text:
        # check if already in offline rows
        offline_fn = text.split("function renderOfflineRows", 1)[-1][:3500]
        if "window.__trailData[key]={meta:" in offline_fn:
            print("SKIP offline lazy rows")
        elif old_rows_trail in text:
            text = text.replace(old_rows_trail, new_rows_trail, 1)
            print("OK offline lazy rows")
        else:
            raise SystemExit("offline trail embed block missing")
    elif old_rows_trail in text:
        text = text.replace(old_rows_trail, new_rows_trail, 1)
        print("OK offline lazy rows")
    else:
        raise SystemExit("offline trail embed block missing")

    # After renderOfflineRows table built, if any isOpen keys, fill them
    # Better: in trail placeholder, call fill on bind — do in renderOffline after bind:
    old_after = """      box.innerHTML=summary+renderOfflineRows(rows, "off");
      bindTrailToggleButtons(box);
"""
    new_after = """      box.innerHTML=summary+renderOfflineRows(rows, "off");
      bindTrailToggleButtons(box);
      Object.keys(LIVE_TRAIL_OPEN).forEach(function(k){ if(LIVE_TRAIL_OPEN[k] && k.indexOf("off:")===0) trailSetOpen(k, true); });
"""
    if "Object.keys(LIVE_TRAIL_OPEN).forEach(function(k){ if(LIVE_TRAIL_OPEN[k] && k.indexOf(\"off:\")===0) trailSetOpen" in text:
        print("SKIP offline refill")
    elif old_after in text:
        text = text.replace(old_after, new_after, 1)
        print("OK offline refill sticky opens")
    else:
        print("WARN offline after-render missing")

    # Live renderLive trail embed — same lazy pattern (first occurrence in renderLive)
    # Find live version with keyAttr
    old_live_trail = """      if(trail.length){
        var metaBits=[];
        if(r.ip) metaBits.push("IP "+esc(r.ip));
        if(r.device_type) metaBits.push(esc(r.device_type));
        if(r.browser) metaBits.push(esc(r.browser));
        if(r.quarantined) metaBits.push("quarantined");
        var thtml="<div class='trail-meta'>"+(metaBits.join(" · ")||"Session pages")+"</div>";
        thtml+="<table class='trail'><thead><tr><th>URL</th><th>Arrived</th><th>Dwell</th></tr></thead><tbody>";
        trail.forEach(function(pt){
          var p=pt.path||"/";
          var pLab=(p==="/"||p==="/index.html")?"home":p;
          var href=p.indexOf("/")===0?p:"";
          var pl=href?("<a href='"+esc(href)+"'>"+esc(pLab)+"</a>"):esc(pLab);
          var eg=(pt.engagement_label||"");
          if(eg) pl+="<div class='trail-engage'>"+esc(eg)+"</div>";
          var arr=(pt.occurred_at||"").replace("T"," ").slice(0,19);
          var dw=esc(pt.dwell_label||"—");
          thtml+="<tr><td>"+pl+"</td><td>"+esc(arr)+"</td><td class='dwell'>"+dw+"</td></tr>";
        });
        thtml+="</tbody></table>";
        html+="<tr class='live-trail"+(isOpen?" is-open":"")+"' data-trail='"+keyAttr+"' style='display:"+(isOpen?"table-row":"none")+"'><td colspan='3'>"+thtml+"</td></tr>";
      }
"""
    new_live_trail = """      if(trail.length){
        window.__trailData[key]={meta:{ip:r.ip,device_type:r.device_type,browser:r.browser,quarantined:r.quarantined},trail:trail};
        html+="<tr class='live-trail"+(isOpen?" is-open":"")+"' data-trail='"+keyAttr+"' style='display:"+(isOpen?"table-row":"none")+"'><td colspan='3' class='note'>…</td></tr>";
      }
"""
    if old_live_trail in text:
        text = text.replace(old_live_trail, new_live_trail, 1)
        print("OK live lazy rows")
    else:
        print("WARN live trail embed missing (may already lazy)")

    # Also show arrow when pages_count>0 even if trail array empty (still tappable message)
    old_arrow_cond = """      var arrow=trail.length
        ? ("<button type='button' class='live-exp' data-trail='"+esc(key)+"' aria-expanded='"+(isOpen?"true":"false")+"' "
          +"onclick=\\"return window.__ssaTrailToggle(this.getAttribute('data-trail'))\\">"+(isOpen?"▼":"▶")+"</button> ")
        : "";
"""
    # keep as trail.length — data must exist

    # Event delegation backup on offlineBox/liveBox in case onclick stripped
    if "window.__ssaTrailDelegationV2" not in text:
        inject_after = "  window.__ssaTrailToggle = trailToggle;\n"
        delegation = """  window.__ssaTrailToggle = trailToggle;
  if(!window.__ssaTrailDelegationV2){
    window.__ssaTrailDelegationV2=true;
    document.addEventListener("click", function(ev){
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
  }
"""
        if inject_after in text:
            text = text.replace(inject_after, delegation, 1)
            print("OK bubble delegation v2 backup")
        else:
            print("WARN inject point for delegation missing")

    if text != orig:
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print("OK compiled")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
