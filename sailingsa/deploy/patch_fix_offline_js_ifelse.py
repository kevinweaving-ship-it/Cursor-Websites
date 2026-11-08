#!/usr/bin/env python3
"""Fix broken if(live.ok) ... else after offline wire."""
from pathlib import Path
import py_compile
import shutil
from datetime import datetime, timezone

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-offline-jsfix-{stamp}"))
    text = API.read_text(encoding="utf-8")
    bad = 'if(live.ok) renderLive(live); try{renderOffline(live);}catch(eOff){} else $("liveBox").innerHTML="<p class=\'err\'>"+esc(live.error||"live failed")+"</p>";'
    good = 'if(live.ok){ renderLive(live); try{renderOffline(live);}catch(eOff){ var ob=$("offlineBox"); if(ob) ob.innerHTML="<p class=\'note\'>No offline data.</p>"; } } else { $("liveBox").innerHTML="<p class=\'err\'>"+esc(live.error||"live failed")+"</p>"; var ob2=$("offlineBox"); if(ob2) ob2.innerHTML="<p class=\'note\'>—</p>"; }'
    n = text.count(bad)
    if n == 0:
        # try alternate quote styles
        bad2 = 'if(live.ok) renderLive(live); try{renderOffline(live);}catch(eOff){} else'
        if bad2 in text:
            text = text.replace(
                'if(live.ok) renderLive(live); try{renderOffline(live);}catch(eOff){} else $("liveBox").innerHTML="<p class=\'err\'>"+esc(live.error||"live failed")+"</p>";',
                good,
            )
            n = 1 if good in text else 0
        if n == 0 and "renderOffline(live)" in text:
            # show context
            i = text.find("renderOffline(live)")
            print("CTX", repr(text[i - 80 : i + 200]))
            raise SystemExit("bad pattern not found")
    text = text.replace(bad, good)
    if good not in text:
        raise SystemExit("fix not applied")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK fixed live/offline if/else x{text.count(good)}")


if __name__ == "__main__":
    main()
