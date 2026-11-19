"""Auto-expand human Done/offline trails; show visitor/page totals."""
from pathlib import Path
import py_compile, shutil
from datetime import datetime, timezone

API = Path("/var/www/sailingsa/api/api.py")
stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
shutil.copy2(API, API.with_suffix(f".bak-offline-expand-{stamp}"))
text = API.read_text(encoding="utf-8")

old = '''  function renderOffline(d){
    var box=$("offlineBox");
    if(!box) return;
    var rows=(d.offline||[]).filter(function(r){ return r && r.kind!=="bot"; });
    if(!rows.length){ box.innerHTML="<p class='note'>No completed real visits in the last 24h outside the live window.</p>"; }
    else box.innerHTML=renderOfflineRows(rows, "off");
    try{renderOfflineBots(d);}catch(eB){}
  }'''

# tolerate whitespace variants
if old not in text:
    # try without leading spaces differences
    i = text.find("function renderOffline(d){")
    j = text.find("try{renderOfflineBots(d);}catch(eB){}", i)
    if i < 0 or j < 0:
        raise SystemExit("renderOffline body not found")
    j = text.find("\n  }", j)
    old = text[i : j + 4]

new = '''  function renderOffline(d){
    var box=$("offlineBox");
    if(!box) return;
    var rows=(d.offline||[]).filter(function(r){ return r && r.kind!=="bot"; });
    if(!rows.length){
      box.innerHTML="<p class='note'>No completed real visits in the last 24h outside the live window.</p>";
    } else {
      // Auto-open each visitor trail so IPs + URLs are visible without extra taps
      rows.forEach(function(r){
        var key="off:"+(r.ip||r.visitor_id||r.who||"");
        LIVE_TRAIL_OPEN[key]=true;
      });
      var pages=0;
      rows.forEach(function(r){ pages += (r.pages_count!=null?r.pages_count:((r.page_trail||[]).length)); });
      var summary="<p class='note' style='font-weight:700;margin:0 0 8px'>"+rows.length+" visitor"+(rows.length===1?"":"s")+" · "+pages+" URL"+(pages===1?"":"s")+"</p>";
      box.innerHTML=summary+renderOfflineRows(rows, "off");
    }
    try{renderOfflineBots(d);}catch(eB){}
  }'''

if "Auto-open each visitor trail" not in text:
    text = text.replace(old, new, 1)
    if "Auto-open each visitor trail" not in text:
        raise SystemExit("replace failed")

API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print("OK expand offline humans")
