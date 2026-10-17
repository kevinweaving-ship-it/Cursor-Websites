#!/usr/bin/env python3
"""Wire Done/offline render + include hidden bots in offline list."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-offline-wire-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    # --- 1) Call renderOffline wherever renderLive is called ---
    replacements = [
        (
            'if(live.ok) renderLive(live); else $("liveBox").innerHTML="<p class=\'err\'>"+esc(live.error||"live failed")+"</p>";',
            'if(live.ok){ renderLive(live); try{renderOffline(live);}catch(eOff){ var ob=$("offlineBox"); if(ob) ob.innerHTML="<p class=\'err\'>Offline failed</p>"; } } else { $("liveBox").innerHTML="<p class=\'err\'>"+esc(live.error||"live failed")+"</p>"; var ob2=$("offlineBox"); if(ob2) ob2.innerHTML="<p class=\'note\'>Live failed — offline unavailable.</p>"; }',
        ),
    ]
    # setInterval path may use renderLive(live) alone
    old_interval = None
    # Find renderLive(live) occurrences
    count_before = text.count("renderLive(live)")
    # Broader: after renderLive(live) ensure offline
    if "renderOffline(live)" not in text:
        text = text.replace(
            "renderLive(live);",
            "renderLive(live); try{renderOffline(live);}catch(eOff){}",
        )
        # Fix double-call if first replacement also added it
        text = text.replace(
            "renderLive(live); try{renderOffline(live);}catch(eOff){ var ob=$(\"offlineBox\"); if(ob) ob.innerHTML=\"<p class='err'>Offline failed</p>\"; } }; try{renderOffline(live);}catch(eOff){}",
            "renderLive(live); try{renderOffline(live);}catch(eOff){ var ob=$(\"offlineBox\"); if(ob) ob.innerHTML=\"<p class='err'>Offline failed</p>\"; }",
        )

    for a, b in replacements:
        if a in text and "renderOffline(live)" not in a:
            # only if not already patched to include offline in that exact string
            if b.split("renderOffline")[0] not in text or "Offline failed" not in text:
                text = text.replace(a, b, 1)

    # Clean duplicate try{renderOffline(live);}catch(eOff){} after the long form
    while "try{renderOffline(live);}catch(eOff){} try{renderOffline(live);}catch(eOff){}" in text:
        text = text.replace(
            "try{renderOffline(live);}catch(eOff){} try{renderOffline(live);}catch(eOff){}",
            "try{renderOffline(live);}catch(eOff){}",
        )

    if "renderOffline(live)" not in text:
        raise SystemExit("failed to wire renderOffline(live)")

    # --- 2) Offline helper: also include quarantined bots past 60s grace even if still in live window ---
    old_sql = '''            WHERE last_activity IS NOT NULL
              AND last_activity <= NOW() - make_interval(mins => %s)
              AND last_activity > NOW() - make_interval(hours => %s)
'''
    new_sql = '''            WHERE last_activity IS NOT NULL
              AND last_activity > NOW() - make_interval(hours => %s)
              AND (
                    last_activity <= NOW() - make_interval(mins => %s)
                 OR (
                      ip_address IN (
                        SELECT ip_address FROM public.traffic_quarantine_ips
                        WHERE COALESCE(active, true) = true
                          AND COALESCE(first_seen_at, last_seen_at) <= NOW() - INTERVAL '60 seconds'
                      )
                    )
                  )
'''
    # Parameter order changes: was (live_minutes, lookback_hours) now need (lookback_hours, live_minutes)
    if old_sql not in text:
        raise SystemExit("offline SQL where not found")
    text = text.replace(old_sql, new_sql, 1)

    old_params = "(int(live_minutes), int(lookback_hours))"
    # Only in offline helper - find unique context
    offline_fn = text.find("def _lean_traffic_offline_sessions")
    if offline_fn < 0:
        raise SystemExit("offline fn missing")
    # find params after offline fn start within 3500 chars
    region = text[offline_fn : offline_fn + 4500]
    if "(int(live_minutes), int(lookback_hours))" in region:
        region2 = region.replace(
            "(int(live_minutes), int(lookback_hours))",
            "(int(lookback_hours), int(live_minutes))",
            1,
        )
        text = text[:offline_fn] + region2 + text[offline_fn + 4500 :]
    else:
        print("WARN: offline params not updated")

    # Don't skip agent junk already; keep staff filter. Include bots in offline (for audit).
    # Ensure agent still skipped - already there.

    # --- 3) Hide server self-IP and /lean-traffic from Live paths ---
    # Add to agent junk or path filter in live rows
    if "/lean-traffic" not in text[text.find("def _lean_is_agent_junk_path") : text.find("def _lean_is_agent_junk_path") + 800]:
        old_junk = '''    if low in ("/workspace", "/cursor", "/agent"):
        return True
'''
        new_junk = '''    if low in ("/workspace", "/cursor", "/agent"):
        return True
    if low.startswith("/lean-traffic") or low.startswith("/traffic/api"):
        return True
'''
        if old_junk in text:
            text = text.replace(old_junk, new_junk, 1)

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK offline wire (+{len(text) - len(orig)} bytes) renderOffline calls={text.count('renderOffline(live)')}")


if __name__ == "__main__":
    main()
