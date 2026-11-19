from pathlib import Path
import py_compile
import shutil
from datetime import datetime, timezone

API = Path("/var/www/sailingsa/api/api.py")
stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
shutil.copy2(API, API.with_suffix(f".bak-js-garbage-{stamp}"))
text = API.read_text(encoding="utf-8")
bad = """  }innerHTML=html;
  }
  function renderLive(d){"""
good = """  }
  function renderLive(d){"""
if bad not in text:
    # show context
    i = text.find("innerHTML=html")
    print("ctx", repr(text[i-80:i+80]) if i>=0 else "no")
    if good in text and "function renderOfflineBots" in text:
        print("already clean?")
    else:
        raise SystemExit("garbage not found")
else:
    text = text.replace(bad, good, 1)
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print("OK cleaned garbage")
