#!/usr/bin/env python3
"""LIVE NOW card counted staff page-hits; Live list hid staff → empty list while card=1."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = API.with_suffix(f".py.bak_live_staff_{ts}")
    shutil.copy2(API, bak)
    text = API.read_text(encoding="utf-8", errors="replace")
    orig = text

    old_signed = '''                WHERE us.last_activity > NOW() - make_interval(mins => %s)
                  AND COALESCE(us.is_active, true) = true
                  AND (us.sas_id IS NULL OR us.sas_id::text NOT IN """ + _LEAN_TRAFFIC_STAFF_SAS_SQL + """)
                ORDER BY COALESCE(NULLIF(us.sas_id::text,''), us.session_id::text), us.last_activity DESC
                LIMIT 40
                """,
                (_LEAN_TRAFFIC_LIVE_MINUTES,),
            )
            for r in cur.fetchall() or []:
                d = r if isinstance(r, dict) else {
                    "who": r[1], "sas_id": r[2], "path": r[3], "last_activity": r[4],
                    "device": r[5], "session_id": r[6], "ip_address": r[7],
                }
'''
    new_signed = '''                WHERE us.last_activity > NOW() - make_interval(mins => %s)
                  AND COALESCE(us.is_active, true) = true
                  -- Include staff: LIVE NOW counts their hits; hiding them left an empty Live list
                ORDER BY COALESCE(NULLIF(us.sas_id::text,''), us.session_id::text), us.last_activity DESC
                LIMIT 40
                """,
                (_LEAN_TRAFFIC_LIVE_MINUTES,),
            )
            for r in cur.fetchall() or []:
                d = r if isinstance(r, dict) else {
                    "who": r[1], "sas_id": r[2], "path": r[3], "last_activity": r[4],
                    "device": r[5], "session_id": r[6], "ip_address": r[7],
                }
'''
    # Only patch inside lean_traffic_api_live — first occurrence after that def
    idx = text.find("def lean_traffic_api_live")
    if idx < 0:
        raise SystemExit("no lean_traffic_api_live")
    # window of signed query
    chunk = text[idx : idx + 8000]
    if "Include staff: LIVE NOW counts their hits" in chunk:
        print("SKIP live staff already included")
    else:
        if old_signed not in chunk:
            raise SystemExit("signed filter block not found in live api")
        chunk2 = chunk.replace(old_signed, new_signed, 1)
        text = text[:idx] + chunk2 + text[idx + 8000 :]
        print("OK live list includes staff signed-in")

    # Mark staff kind when sas is super_admin
    old_append = '''                rows.append({
                    "kind": "signed",
                    "who": d.get("who") or "Signed-in",
'''
    new_append = '''                is_staff_row = False
                try:
                    cur.execute(
                        "SELECT 1 FROM public.user_accounts WHERE role = 'super_admin' AND sas_id::text = %s LIMIT 1",
                        (str(d.get("sas_id") or ""),),
                    )
                    is_staff_row = bool(cur.fetchone())
                except Exception:
                    is_staff_row = False
                rows.append({
                    "kind": "signed",
                    "who": d.get("who") or ("Staff" if is_staff_row else "Signed-in"),
'''
    idx2 = text.find("def lean_traffic_api_live")
    chunk = text[idx2 : idx2 + 12000]
    if '"who": d.get("who") or ("Staff" if is_staff_row else "Signed-in")' in chunk:
        print("SKIP staff who label already")
    else:
        if old_append not in chunk:
            print("WARN signed append not exact — staff still shown as signed")
        else:
            chunk2 = chunk.replace(old_append, new_append, 1)
            text = text[:idx2] + chunk2 + text[idx2 + 12000 :]
            print("OK staff who label")

    # UI: LIVE NOW card prefers human_live from /live so it matches the list
    old_ui = '''    fetchJson("/traffic/api/live").then(function(live){
      if(live.ok){ renderLive(live); try{renderOffline(live);}catch(eOff){ var ob=$("offlineBox"); if(ob) ob.innerHTML="<p class='note'>No offline data.</p>"; } } else { $("liveBox").innerHTML="<p class='err'>"+esc(live.error||"live failed")+"</p>"; var ob2=$("offlineBox"); if(ob2) ob2.innerHTML="<p class='note'>—</p>"; }
    }).catch(function(e){ $("liveBox").innerHTML="<p class='err'>"+esc(e.message||e)+"</p>"; });
'''
    new_ui = '''    fetchJson("/traffic/api/live").then(function(live){
      if(live.ok){
        renderLive(live);
        try{renderOffline(live);}catch(eOff){ var ob=$("offlineBox"); if(ob) ob.innerHTML="<p class='note'>No offline data.</p>"; }
        // Card must match Live list (not a separate unified count that can show 1 with empty list)
        if(RANGE==="live" && live.human_live!=null){
          $("kLive").textContent=String(live.human_live);
        }
      } else { $("liveBox").innerHTML="<p class='err'>"+esc(live.error||"live failed")+"</p>"; var ob2=$("offlineBox"); if(ob2) ob2.innerHTML="<p class='note'>—</p>"; }
    }).catch(function(e){ $("liveBox").innerHTML="<p class='err'>"+esc(e.message||e)+"</p>"; });
'''
    if "Card must match Live list" not in text:
        if old_ui not in text:
            raise SystemExit("live fetch UI block not found")
        text = text.replace(old_ui, new_ui, 1)
        print("OK LIVE NOW card uses human_live")
    else:
        print("SKIP UI already patched")

    # Don't let series overwrite the card with mismatched live_now after live loaded
    old_series = '''        if(RANGE==="live" && s.live_now!=null) $("kLive").textContent=String(s.live_now);
'''
    new_series = '''        // Do not overwrite LIVE NOW from series — /live human_live is source of truth for the card
'''
    if old_series in text:
        text = text.replace(old_series, new_series, 1)
        print("OK stop series overwriting LIVE NOW")
    else:
        print("SKIP series overwrite already gone")

    if text != orig:
        API.write_text(text, encoding="utf-8")
        py_compile.compile(str(API), doraise=True)
        print(f"OK compiled bak={bak}")
    else:
        print("unchanged")


if __name__ == "__main__":
    main()
