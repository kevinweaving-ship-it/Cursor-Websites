from pathlib import Path
import py_compile, shutil
from datetime import datetime, timezone
API = Path("/var/www/sailingsa/api/api.py")
stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
shutil.copy2(API, API.with_suffix(f".bak-noclear-{stamp}"))
text = API.read_text(encoding="utf-8")
old = '''      // Default hide: clear sticky open for offline guests so trails start collapsed
      Object.keys(LIVE_TRAIL_OPEN).forEach(function(k){ if(k.indexOf("off:")===0) delete LIVE_TRAIL_OPEN[k]; });
      var summary="<p class='note' style='font-weight:700;margin:0 0 8px'>"+rows.length+" visitor"+(rows.length===1?"":"s")+" · "+pages+" URL"+(pages===1?"":"s")+" — tap ▶ to show/hide URLs</p>";
'''
new = '''      var summary="<p class='note' style='font-weight:700;margin:0 0 8px'>"+rows.length+" visitor"+(rows.length===1?"":"s")+" · "+pages+" URL"+(pages===1?"":"s")+" — tap ▶ to show/hide URLs</p>";
'''
if old in text:
    text = text.replace(old, new, 1)
old2 = '''    Object.keys(LIVE_TRAIL_OPEN).forEach(function(k){ if(k.indexOf("offbot:")===0) delete LIVE_TRAIL_OPEN[k]; });
    box.innerHTML=renderOfflineRows(rows, "offbot");
'''
new2 = '''    box.innerHTML=renderOfflineRows(rows, "offbot");
'''
if old2 in text:
    text = text.replace(old2, new2, 1)
# One-time clear of leftover auto-open keys at page load
if "OFF_TRAIL_DEFAULT_HIDE" not in text:
    text = text.replace(
        "var LIVE_TRAIL_OPEN = window.__liveTrailOpen || (window.__liveTrailOpen = {});",
        "var LIVE_TRAIL_OPEN = window.__liveTrailOpen || (window.__liveTrailOpen = {});\n"
        "  /* OFF_TRAIL_DEFAULT_HIDE — collapse offline trails once per page load */\n"
        "  if(!window.__offTrailHideInit){ window.__offTrailHideInit=true;\n"
        "    Object.keys(LIVE_TRAIL_OPEN).forEach(function(k){ if(k.indexOf(\"off:\")===0||k.indexOf(\"offbot:\")===0) delete LIVE_TRAIL_OPEN[k]; }); }",
        1,
    )
API.write_text(text, encoding="utf-8")
py_compile.compile(str(API), doraise=True)
print("OK")
