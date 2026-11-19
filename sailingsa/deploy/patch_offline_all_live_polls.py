#!/usr/bin/env python3
from pathlib import Path
import py_compile
import shutil
from datetime import datetime, timezone

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-offline-poll-{stamp}"))
    text = API.read_text(encoding="utf-8")
    old = 'fetchJson("/traffic/api/live").then(function(d){ if(d.ok) renderLive(d); }).catch(function(){});'
    new = 'fetchJson("/traffic/api/live").then(function(d){ if(d.ok){ renderLive(d); try{renderOffline(d);}catch(eOff){} } }).catch(function(){});'
    if old not in text:
        raise SystemExit("poll live-only path not found")
    text = text.replace(old, new, 1)
    # brace the interval Promise.all line for clarity
    old2 = "if(live && live.ok) renderLive(live); try{renderOffline(live);}catch(eOff){}"
    new2 = "if(live && live.ok){ renderLive(live); try{renderOffline(live);}catch(eOff){} }"
    if old2 in text:
        text = text.replace(old2, new2, 1)
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print("OK offline on all live polls")


if __name__ == "__main__":
    main()
