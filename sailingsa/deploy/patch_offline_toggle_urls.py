from pathlib import Path
import py_compile, shutil
from datetime import datetime, timezone

API = Path("/var/www/sailingsa/api/api.py")
stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
shutil.copy2(API, API.with_suffix(f".bak-off-toggle-{stamp}"))
text = API.read_text(encoding="utf-8")

old = '''    if(!rows.length){
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
    }'''

new = '''    if(!rows.length){
      box.innerHTML="<p class='note'>No completed real visits in the last 24h outside the live window.</p>";
    } else {
      var pages=0;
      rows.forEach(function(r){ pages += (r.pages_count!=null?r.pages_count:((r.page_trail||[]).length)); });
      var summary="<p class='note' style='font-weight:700;margin:0 0 8px'>"+rows.length+" visitor"+(rows.length===1?"":"s")+" · "+pages+" URL"+(pages===1?"":"s")+" — tap ▶ to show/hide each URL trail</p>";
      box.innerHTML=summary+renderOfflineRows(rows, "off");
    }'''

if old not in text:
    # try find auto-open block
    if "Auto-open each visitor trail" not in text and "tap ▶ to show/hide" in text:
        print("OK already")
    else:
        i = text.find("Auto-open each visitor trail")
        print("ctx", repr(text[i-100:i+500]) if i>=0 else "missing")
        raise SystemExit("block not found")
else:
    text = text.replace(old, new, 1)
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print("OK offline URL show/hide (no auto-open)")
