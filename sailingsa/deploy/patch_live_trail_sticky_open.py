#!/usr/bin/env python3
"""Keep Live session trail expanded across poll refreshes; still allow show/hide."""
from __future__ import annotations

import pathlib
import sys
import py_compile

API = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/var/www/sailingsa/api/api.py")
text = API.read_text(encoding="utf-8")

idx = text.find("  function renderLive(d){")
if idx < 0:
    raise SystemExit("renderLive not found")
idx2 = text.find("  function mediaSrc(u){", idx)
if idx2 < 0:
    raise SystemExit("mediaSrc not found")

new_block = r'''  var LIVE_TRAIL_OPEN = window.__liveTrailOpen || (window.__liveTrailOpen = {});
  function liveTrailKey(r){
    if(r.visitor_id) return "v:"+String(r.visitor_id);
    if(r.session_id) return "s:"+String(r.session_id);
    if(r.ip) return "ip:"+String(r.ip);
    if(r.sas_id) return "sas:"+String(r.sas_id);
    return "who:"+String(r.kind||"")+"|"+String(r.who||"");
  }
  function renderLive(d){
    var rows=d.rows||[];
    if(!rows.length){$("liveBox").innerHTML="<p class='note'>Nobody active in the last "+(d.live_minutes||15)+" minutes.</p>"; return;}
    var html="<table><thead><tr><th>Who</th><th>Page</th><th>When</th></tr></thead><tbody>";
    rows.slice(0,30).forEach(function(r){
      var badge=r.kind==="signed"?"signed":(r.kind==="bot"?"bot":(r.guessed?"guess":"anon"));
      var badgeLabel=r.kind==="signed"?"signed":(r.kind==="bot"?"bot":(r.guessed?"guess":"guest"));
      var path=r.path||"—";
      var link=r.href?("<a href='"+esc(r.href)+"'>"+esc(path)+"</a>"):esc(path);
      var when=(r.last_activity||"").replace("T"," ").slice(0,19);
      var who=esc(r.who||"");
      if(r.who_href){ who="<a href='"+esc(r.who_href)+"' title='Guessed from IP sailor page visits'>"+who+"</a>"; }
      var meta="";
      if(r.sas_id) meta+=" · "+esc(r.sas_id);
      if(r.guessed && r.likely_hits) meta+=" · "+r.likely_hits+" sailor hits";
      var trail=Array.isArray(r.page_trail)?r.page_trail:[];
      var nPages=r.pages_count!=null?r.pages_count:trail.length;
      if(nPages>1) meta+=" · "+nPages+" pages";
      var key=liveTrailKey(r);
      var keyAttr=esc(key);
      var isOpen=!!LIVE_TRAIL_OPEN[key];
      var arrow=trail.length
        ? ("<button type='button' class='live-exp' data-trail='"+keyAttr+"' aria-expanded='"+(isOpen?"true":"false")+"' aria-label='Show session pages'>"+(isOpen?"▼":"▶")+"</button> ")
        : "";
      html+="<tr class='live-main' data-trail='"+keyAttr+"'><td>"+arrow+"<span class='badge "+badge+"'>"+badgeLabel+"</span> "+who+meta+"</td><td>"+link+"</td><td>"+esc(when)+"</td></tr>";
      if(trail.length){
        var metaBits=[];
        if(r.ip) metaBits.push("IP "+esc(r.ip));
        if(r.device_type) metaBits.push(esc(r.device_type));
        if(r.browser) metaBits.push(esc(r.browser));
        if(r.kind==="signed" && r.sas_id) metaBits.push("sas "+esc(r.sas_id));
        var thtml="<div class='trail-meta'>"+(metaBits.join(" · ")||"Session pages")+"</div>";
        thtml+="<table class='trail'><thead><tr><th>URL</th><th>Arrived</th><th>Dwell</th></tr></thead><tbody>";
        trail.forEach(function(pt){
          var p=pt.path||"/";
          var href=p.indexOf("/")===0?p:"";
          var pl=href?("<a href='"+esc(href)+"'>"+esc(p)+"</a>"):esc(p);
          var arr=(pt.occurred_at||"").replace("T"," ").slice(0,19);
          var dw=esc(pt.dwell_label||"—");
          thtml+="<tr><td>"+pl+"</td><td>"+esc(arr)+"</td><td class='dwell'>"+dw+"</td></tr>";
        });
        thtml+="</tbody></table>";
        html+="<tr class='live-trail' data-trail='"+keyAttr+"'"+(isOpen?"":" hidden")+"><td colspan='3'>"+thtml+"</td></tr>";
      } else if(LIVE_TRAIL_OPEN[key]){
        // session gone / no trail yet — drop sticky open
        delete LIVE_TRAIL_OPEN[key];
      }
    });
    html+="</tbody></table>";
    $("liveBox").innerHTML="<div class=\"table-scroll\">"+html+"</div>";
    $("liveBox").querySelectorAll(".live-exp").forEach(function(btn){
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
  }
'''

text = text[:idx] + new_block + text[idx2:]
API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print(f"OK (+{len(new_block)} renderLive replace)")
