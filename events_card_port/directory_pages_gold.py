"""Gold-header /regattas and /sailors directory pages — card list + fuzzy search (landing-style)."""

# Insert these functions into api.py (after _directory_page_html, before route handlers).


def _directory_gold_page_response(title: str, inner: str, extra_head: str):
    """Return HTMLResponse with gold header when available."""
    gold_fn = globals().get("_html_with_gold_header")
    if gold_fn:
        return gold_fn(title, inner, extra_head)
    return HTMLResponse(
        "<!DOCTYPE html><html lang=\"en-US\"><head><meta charset=\"UTF-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\">"
        f"<title>{html_module.escape(title)}</title>{extra_head}</head><body>{inner}</body></html>"
    )


_DIRECTORY_PAGE_ABOUT_CSS = """
.page-about-block{margin:0 0 1rem 0;padding:0.85rem 1rem;border:1px solid #dbe5ef;border-radius:8px;background:#f8fbff;color:#1e293b;line-height:1.45;font-size:0.95rem;}
.directory-results-label{margin:0 0 0.75rem 0;font-size:1.1rem;font-weight:700;color:#001f3f;}
.directory-show-more{margin-top:0.75rem;}
.directory-show-more button{padding:0.5rem 1rem;font-size:0.95rem;background:#f1f5f9;border:2px solid #001f3f;border-radius:6px;cursor:pointer;color:#001f3f;font-weight:600;min-height:44px;}
.directory-show-more button:hover{background:#e2e8f0;}
.directory-show-more button.hidden{display:none;}
#regattas-dashboard,#sailors-dashboard{padding-top:1rem;box-sizing:border-box;}
@media (min-width:640px){#regattas-dashboard,#sailors-dashboard{padding-top:1.25rem;}}
.sailor-directory-results{margin-top:0.5rem;display:flex;flex-direction:column;gap:0.75rem;padding-bottom:2rem;}
.sailor-directory-results .ssa-dev1-inject{margin:0;max-width:100%;}
.sailor-directory-results .profile-card{margin:0;}
.sailor-directory-hint{color:#64748b;font-size:0.95rem;margin:0.5rem 0 0;}
"""


def _regattas_directory_page_html():
    about = (
        "Explore South African sailing regattas with full race results, rankings, and performance history. "
        "Search by event name, host club, class, or year — same card list as the home page."
    )
    extra_head = (
        '<link rel="canonical" href="https://sailingsa.co.za/regattas">'
        '<link rel="stylesheet" href="/css/gold-list-tables.css?v=20260723m5">'
        "<style>"
        + _SECTION_HEADING_ROW_UNIFIED_CSS
        + _EVENTS_TOOLBAR_SEARCH_CSS
        + _EVENTS_SA_HOME_REGATTA_CSS
        + _DIRECTORY_PAGE_ABOUT_CSS
        + """
.sa-home-regatta-event-logo-link{grid-area:logo;display:flex;align-items:center;justify-content:flex-start;text-decoration:none;line-height:0;}
.sa-home-regatta-children{margin:0;border:1px solid #dbe3ef;border-radius:4px;background:#fff;overflow:hidden;}
.sa-home-regatta-children-head{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;padding:8px 12px;background:#eff5ff;}
.sa-home-regatta-children-note{color:#334155;font-size:11px;font-weight:700;white-space:nowrap;}
.sa-home-regatta-children-chips{display:inline-flex;flex-wrap:wrap;gap:4px 6px;}
.sa-home-regatta-children-chip{display:inline-flex;align-items:center;gap:3px;padding:2px 4px;text-decoration:none;color:#334155;font-size:11px;font-weight:800;}
</style>
"""
    )
    inner = (
        '<div class="container" id="regattas-dashboard">'
        '<div class="card stats-section">'
        + _events_section_heading_row_html("Regattas")
        + f'<div class="page-about-block">{html_module.escape(about)}</div>'
        + '<h2 class="directory-results-label" id="regattas-results-label">Loading regattas…</h2>'
        + '<div class="events-cards sa-home-regatta-list" id="regattas-card-list"></div>'
        + '<div class="directory-show-more" id="regattas-show-more"><button type="button" id="btn-regattas-more">Show More</button></div>'
        + "</div></div>"
        + _seo_discovery_block_html()
        + """
<footer class="site-footer-about" style="text-align:center;padding:2rem 1rem;font-size:0.9rem;color:#666;border-top:1px solid #e0e0e0;margin-top:2rem;">SailingSA – South African Sailing Results Database © <span id="year"></span></footer>
<script>document.getElementById("year").textContent=new Date().getFullYear();</script>
<script>
(function(){
  var INITIAL=20, STEP=20, allParents=[], shown=0, cache=null;
  function esc(s){var d=document.createElement("div");d.textContent=s||"";return d.innerHTML;}
  function dateShort(s){
    s=(s||"").toString().slice(0,10);
    if(!/^\\d{4}-\\d{2}-\\d{2}$/.test(s)) return s||"";
    var m=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
    var p=s.split("-"); return parseInt(p[2],10)+" "+m[parseInt(p[1],10)-1]+" "+p[0];
  }
  function formatDate(r){
    var sd=(r.start_date||"").slice(0,10), ed=(r.end_date||"").slice(0,10);
    if(sd&&ed&&sd!==ed) return dateShort(sd)+" → "+dateShort(ed);
    return dateShort(ed||sd);
  }
  function nestRegattaParents(list){
    var items=(list||[]).map(function(r){var c=Object.assign({},r);c._children=Array.isArray(r.children)?r.children.slice():[];return c;});
    var childIds={};
    items.forEach(function(r){
      var rid=String(r.regatta_id||"");
      var parent=null;
      items.forEach(function(p){
        var pid=String(p.regatta_id||"");
        if(pid&&rid!==pid&&rid.indexOf(pid+"-")===0){
          if(!parent||pid.length>String(parent.regatta_id||"").length) parent=p;
        }
      });
      if(parent){parent._children=parent._children||[];parent._children.push(r);childIds[rid]=true;}
    });
    return items.filter(function(r){return !childIds[String(r.regatta_id||"")];});
  }
  function filterList(list,q){
    q=(q||"").trim().toLowerCase();
    if(!q) return list.slice();
    var terms=q.split(/\\s+/).filter(Boolean);
    return list.filter(function(r){
      var hay=[r.search_label,r.event_name,r.regatta_id,r.host_club_name,r.host_club_code,r.host_club_abbrev,r.start_date,r.end_date].join(" ").toLowerCase();
      return terms.every(function(t){return hay.indexOf(t)!==-1;});
    });
  }
  function regattaSortDay(r){
    var keys=["end_date","start_date","as_at_time"];
    for(var i=0;i<keys.length;i++){
      var v=r[keys[i]];
      if(v==null) continue;
      var s=String(v).slice(0,10);
      if(/^\\d{4}-\\d{2}-\\d{2}$/.test(s)) return s;
    }
    return "0000-00-00";
  }
  function sortRegattasNewestFirst(list){
    return (list||[]).slice().sort(function(a,b){
      var da=regattaSortDay(a), db=regattaSortDay(b);
      if(da!==db) return db.localeCompare(da);
      var na=String(a.regatta_number||""), nb=String(b.regatta_number||"");
      if(na!==nb) return nb.localeCompare(na,undefined,{numeric:true});
      return String(a.event_name||"").toLowerCase().localeCompare(String(b.event_name||"").toLowerCase());
    });
  }
  function icoCal(){return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>';}
  function icoPeople(){return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>';}
  function renderCard(r){
    var rid=String(r.regatta_id||"");
    var title=(r.search_label||r.event_name||"Regatta");
    var regHref="/regatta/"+encodeURIComponent(rid);
    var logoSrc=(r.logo_url||"").trim();
    var logoHtml=logoSrc?'<a class="sa-home-regatta-event-logo-link" href="'+esc(regHref)+'"><img class="sa-home-regatta-event-logo" src="'+esc(logoSrc)+'" alt="" loading="lazy" decoding="async" onerror="this.parentElement.style.display=\\'none\\'"></a>':"";
    var ent=parseInt(r.entries_count,10)||0;
    var meta='<div class="sa-home-regatta-meta"><span class="sa-home-regatta-meta-pill">'+icoCal()+'<span>'+esc(formatDate(r))+'</span></span>';
    if(ent>0) meta+='<span class="sa-home-regatta-meta-pill">'+icoPeople()+'<span>'+ent+' entries</span></span>';
    meta+='</div>';
    var hostCode=(r.host_club_code||r.host_club_abbrev||"").trim();
    var hostName=(r.host_club_fullname||r.host_club_name||"").trim();
    var hostSlug=(r.host_club_slug||"").trim().toLowerCase();
    var hostLogo=(r.host_logo_url||"").trim()||(hostCode?("/api/club-logo/"+encodeURIComponent(hostCode)):"");
    var hostInner="";
    if(hostLogo) hostInner+='<img class="sa-home-regatta-host-logo" src="'+esc(hostLogo)+'" alt="" loading="lazy" onerror="this.hidden=true">';
    hostInner+='<div class="sa-home-regatta-host-text"><div class="sa-home-regatta-host-code">'+esc(hostCode||"—")+'</div>';
    if(hostName) hostInner+='<div class="sa-home-regatta-host-name">'+esc(hostName)+'</div>';
    hostInner+='</div>';
    var hostHtml=hostSlug?('<a class="sa-home-regatta-host" href="/club/'+esc(hostSlug)+'">'+hostInner+'</a>'):('<div class="sa-home-regatta-host">'+hostInner+'</div>');
    var actions='<div class="sa-home-regatta-actions"><a class="sa-home-regatta-btn" href="'+esc(regHref)+'">Full Results</a></div>';
    var kids=Array.isArray(r._children)?r._children:[];
    var chips="";
    if(kids.length>1){
      chips='<div class="sa-home-regatta-children"><div class="sa-home-regatta-children-head"><span class="sa-home-regatta-children-note">Or view by class/fleet:</span><div class="sa-home-regatta-children-chips">';
      kids.forEach(function(ch){
        var cid=String(ch.regatta_id||"");
        if(!cid) return;
        var lbl=(ch.search_label||ch.event_name||ch.fleet_label||"Fleet").replace(new RegExp("^"+title.replace(/[.*+?^${}()|[\\]\\\\]/g,"\\\\$&")+"\\\\s*","i"),"").trim()||"Fleet";
        chips+='<a class="sa-home-regatta-children-chip" href="/regatta/'+esc(cid)+'">'+esc(lbl)+'</a>';
      });
      chips+='</div></div></div>';
    }
    return '<article class="sa-home-regatta-card sa-home-regatta-card--has-results"><div class="sa-home-regatta-top">'+logoHtml
      +'<div class="sa-home-regatta-top-main"><a href="'+esc(regHref)+'" class="sa-home-regatta-title">'+esc(title)+'</a>'+meta+'</div>'
      +hostHtml+actions+'</div>'+chips+'</article>';
  }
  function updateLabel(q,n){
    var el=document.getElementById("regattas-results-label");
    if(!el) return;
    if(q) el.innerHTML='Regatta search for "<span style="color:#c00;font-weight:700;">'+esc(q)+'</span>" — '+n+' result'+(n===1?"":"s");
    else el.textContent="All regattas — newest first ("+n+")";
  }
  function paint(){
    var list=document.getElementById("regattas-card-list");
    var btn=document.getElementById("btn-regattas-more");
    var wrap=document.getElementById("regattas-show-more");
    if(!list) return;
    list.innerHTML="";
    var end=Math.min(shown,allParents.length);
    for(var i=0;i<end;i++) list.insertAdjacentHTML("beforeend",renderCard(allParents[i]));
    if(wrap&&btn) wrap.classList.toggle("hidden",end>=allParents.length);
  }
  function applyFilter(){
    var inp=document.getElementById("events-dashboard-search");
    var q=inp?inp.value.trim():"";
    var src=cache?nestRegattaParents(cache):[];
    allParents=sortRegattasNewestFirst(filterList(src,q));
    shown=INITIAL;
    updateLabel(q,allParents.length);
    paint();
  }
  function loadAll(){
    return fetch("/api/regattas/with-counts?limit=500",{credentials:"same-origin"})
      .then(function(r){return r.json();})
      .then(function(data){
        cache=Array.isArray(data)?data:[];
        applyFilter();
      })
      .catch(function(){
        var el=document.getElementById("regattas-results-label");
        if(el) el.textContent="Unable to load regattas. Try again.";
      });
  }
  var deb=null;
  var inp=document.getElementById("events-dashboard-search");
  if(inp){
    inp.setAttribute("placeholder","Search regattas…");
    inp.setAttribute("aria-label","Search regattas");
    inp.addEventListener("input",function(){
      clearTimeout(deb);
      deb=setTimeout(applyFilter,220);
    });
  }
  var btn=document.getElementById("btn-regattas-more");
  if(btn) btn.onclick=function(){shown+=STEP;paint();};
  loadAll();
})();
</script>"""
    )
    return (extra_head, inner)


def _sailors_directory_page_html():
    about = (
        "Search all South African sailors with complete regatta results, rankings, and performance history. "
        "SailingSA is the most comprehensive South African sailing results database for sailors."
    )
    extra_head = (
        '<link rel="canonical" href="https://sailingsa.co.za/sailors">'
        "<style>"
        + _SECTION_HEADING_ROW_UNIFIED_CSS
        + _EVENTS_TOOLBAR_SEARCH_CSS
        + _DIRECTORY_PAGE_ABOUT_CSS
        + """
.sailor-directory-results .ssa-dev1-inject main,.sailor-directory-results .ssa-dev1-inject .container{max-width:100%!important;padding:0!important;margin:0!important;}
</style>
"""
    )
    inner = (
        '<div class="container" id="sailors-dashboard">'
        '<div class="card stats-section">'
        + _events_section_heading_row_html("Sailors")
        + f'<div class="page-about-block">{html_module.escape(about)}</div>'
        + '<p class="sailor-directory-hint" id="sailors-hint">Type at least 2 characters to search sailors by name, SA ID, club, or class.</p>'
        + '<div class="sailor-directory-results" id="sailor-directory-results" role="list"></div>'
        + "</div></div>"
        + _seo_discovery_block_html()
        + """
<footer class="site-footer-about" style="text-align:center;padding:2rem 1rem;font-size:0.9rem;color:#666;border-top:1px solid #e0e0e0;margin-top:2rem;">SailingSA – South African Sailing Results Database © <span id="year"></span></footer>
<script>document.getElementById("year").textContent=new Date().getFullYear();</script>
<script>
(function(){
  var gen=0, deb=null;
  function esc(s){var d=document.createElement("div");d.textContent=s||"";return d.innerHTML;}
  function mountDev1Card(wrap, html){
    var box=document.createElement("div");
    box.innerHTML=html;
    var codes=[];
    box.querySelectorAll("script").forEach(function(sc){
      if(!sc.src) codes.push(sc.textContent||"");
      if(sc.parentNode) sc.parentNode.removeChild(sc);
    });
    wrap.innerHTML="";
    while(box.firstChild) wrap.appendChild(box.firstChild);
    codes.forEach(function(code){
      if(!code||!String(code).trim()) return;
      try{(new Function("document","window",code))(document,window);}catch(e){}
    });
  }
  function fetchCard(item){
    if(!item||!item.sid||item.loaded) return Promise.resolve();
    item.loaded=true;
    window.__ssaDev1CardCache=window.__ssaDev1CardCache||{};
    if(window.__ssaDev1CardCache[item.sid]){
      mountDev1Card(item.wrap,window.__ssaDev1CardCache[item.sid]);
      return Promise.resolve();
    }
    return fetch("/dev-1?embed=1&sas_id="+encodeURIComponent(item.sid),{credentials:"same-origin"})
      .then(function(r){return r.text();})
      .then(function(html){
        if(item.gen!==gen) return;
        window.__ssaDev1CardCache[item.sid]=html;
        mountDev1Card(item.wrap,html);
      })
      .catch(function(){
        if(item.gen!==gen) return;
        item.wrap.innerHTML='<div class="profile-card" style="cursor:default;">Could not load card.</div>';
      });
  }
  function renderList(list){
    var box=document.getElementById("sailor-directory-results");
    var hint=document.getElementById("sailors-hint");
    if(!box) return;
    box.innerHTML="";
    if(!list.length){
      box.innerHTML='<div class="profile-card" style="cursor:default;">No sailors found.</div>';
      return;
    }
    if(hint) hint.style.display="none";
    var items=[];
    list.forEach(function(row){
      var sid=row.sa_sailing_id!=null?String(row.sa_sailing_id):String(row.sas_id||row.sa_id||"");
      var wrap=document.createElement("div");
      wrap.className="ssa-dev1-inject";
      wrap.setAttribute("role","listitem");
      wrap.innerHTML='<div class="profile-card" style="cursor:default;">Loading…</div>';
      box.appendChild(wrap);
      items.push({wrap:wrap,sid:sid,loaded:false,gen:gen});
    });
    var n=Math.min(3,items.length), i=0;
    function pump(){
      if(i>=items.length||gen!==items[0].gen) return;
      var batch=0;
      while(i<items.length&&batch<2){
        fetchCard(items[i++]);
        batch++;
      }
      if(i<items.length) setTimeout(pump,0);
    }
    for(var j=0;j<n;j++) fetchCard(items[j]);
    if(items.length>n) setTimeout(pump,0);
    if(typeof IntersectionObserver==="function"&&items.length>n){
      var io=new IntersectionObserver(function(entries){
        entries.forEach(function(en){
          if(!en.isIntersecting) return;
          io.unobserve(en.target);
          for(var k=n;k<items.length;k++){
            if(items[k].wrap===en.target){fetchCard(items[k]);break;}
          }
        });
      },{rootMargin:"400px 0px"});
      for(var s=n;s<items.length;s++) io.observe(items[s].wrap);
    }
  }
  function runSearch(){
    var inp=document.getElementById("events-dashboard-search");
    var q=inp?(inp.value||"").trim():"";
    var box=document.getElementById("sailor-directory-results");
    var hint=document.getElementById("sailors-hint");
    if(!q){
      if(box) box.innerHTML="";
      if(hint){hint.style.display="";hint.textContent="Type at least 2 characters to search sailors by name, SA ID, club, or class.";}
      return;
    }
    if(q.length<2){
      if(box) box.innerHTML='<div class="profile-card" style="cursor:default;">Type at least 2 characters to search.</div>';
      if(hint) hint.style.display="none";
      return;
    }
    gen++;
    if(box) box.innerHTML='<div class="profile-card" style="cursor:default;">Searching…</div>';
    if(hint) hint.style.display="none";
    var myGen=gen;
    fetch("/api/search?hub=1&limit=200&q="+encodeURIComponent(q),{credentials:"same-origin"})
      .then(function(r){return r.json();})
      .then(function(list){
        if(myGen!==gen) return;
        renderList(Array.isArray(list)?list:[]);
      })
      .catch(function(){
        if(myGen!==gen) return;
        if(box) box.innerHTML='<div class="profile-card" style="cursor:default;color:#c00;">Search failed. Try again.</div>';
      });
  }
  var inp=document.getElementById("events-dashboard-search");
  if(inp){
    inp.setAttribute("placeholder","Search sailors…");
    inp.setAttribute("aria-label","Search sailors");
    inp.addEventListener("input",function(){
      clearTimeout(deb);
      deb=setTimeout(runSearch,280);
    });
  }
})();
</script>"""
    )
    return (extra_head, inner)
