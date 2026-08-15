#!/usr/bin/env python3
"""Done/offline: humans only — no bots."""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-offline-humans-{stamp}"))
    text = API.read_text(encoding="utf-8")
    orig = text

    # Revert quarantine-bot inclusion in offline SQL — only sessions past live window
    old_sql = '''            WHERE last_activity IS NOT NULL
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
    new_sql = '''            WHERE last_activity IS NOT NULL
              AND last_activity <= NOW() - make_interval(mins => %s)
              AND last_activity > NOW() - make_interval(hours => %s)
'''
    if old_sql in text:
        text = text.replace(old_sql, new_sql, 1)
        # fix params back to (live_minutes, lookback_hours)
        offline_fn = text.find("def _lean_traffic_offline_sessions")
        region = text[offline_fn : offline_fn + 5000]
        if "(int(lookback_hours), int(live_minutes))" in region:
            region2 = region.replace(
                "(int(lookback_hours), int(live_minutes))",
                "(int(live_minutes), int(lookback_hours))",
                1,
            )
            text = text[:offline_fn] + region2 + text[offline_fn + 5000 :]
    else:
        print("WARN: bot-inclusive SQL not found (may already be window-only)")

    # After building each offline row (or before append), skip bots / quarantined
    old_append = '''            out.append(
                {
                    "kind": "bot" if is_bot else "anon",
                    "who": (f"Bot {ip}" if is_bot else f"Guest {ip}") if ip else ("Bot" if is_bot else "Guest"),
                    "ip": ip,
                    "visitor_id": vid,
                    "path": path,
                    "href": path if str(path).startswith("/") else "",
                    "last_activity": la.isoformat() if hasattr(la, "isoformat") else str(la or ""),
                    "first_seen": first_seen.isoformat() if hasattr(first_seen, "isoformat") else str(first_seen or ""),
                    "device_type": device_type or (_traffic_ua_meta(ua)[0] if ua else ""),
                    "browser": browser or (_traffic_ua_meta(ua)[1] if ua else ""),
                    "page_trail": trail,
                    "pages_count": len(trail),
                    "session_seconds": _lean_session_total_seconds(
                        trail, first_seen=first_seen, last_activity=la
                    ),
                    "session_dwell_label": _lean_fmt_dwell_seconds(
                        _lean_session_total_seconds(
                            trail, first_seen=first_seen, last_activity=la
                        )
                    ),
                    "done": True,
                }'''
    # Simpler: skip before append when is_bot
    # Find is_bot block in offline helper
    marker = "def _lean_traffic_offline_sessions"
    start = text.find(marker)
    if start < 0:
        raise SystemExit("offline helper missing")
    end = text.find("\ndef lean_traffic_api_live", start)
    if end < 0:
        end = text.find("\ndef ", start + 10)
    chunk = text[start:end]

    # Replace is_bot decision to skip bots entirely
    if "if is_bot:\n                continue" not in chunk:
        # After is_bot is computed, skip
        needle = '''            is_bot = False
            try:
                if _is_sailor_sas_id_path(path) or _lean_behavior_confident_bot(trail, path, ip):
                    is_bot = True
                elif _lean_same_page_swarm_bot(cur, ip=ip or "", path=path, page_trail=trail, window_minutes=30):
                    is_bot = True
                    if ip:
                        try:
                            _lean_quarantine_ip(cur, ip, "same_page_swarm_no_engage")
                        except Exception:
                            pass
                elif ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
            except Exception:
                pass
            out.append('''
        repl = '''            is_bot = False
            try:
                if ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
                elif _is_sailor_sas_id_path(path) or _lean_behavior_confident_bot(trail, path, ip):
                    is_bot = True
                elif _lean_same_page_swarm_bot(cur, ip=ip or "", path=path, page_trail=trail, window_minutes=30):
                    is_bot = True
            except Exception:
                pass
            # Done/offline = valid humans only (no bots)
            if is_bot:
                continue
            out.append('''
        if needle not in chunk:
            # try shorter original without swarm
            needle2 = '''            is_bot = False
            try:
                if _is_sailor_sas_id_path(path) or _lean_behavior_confident_bot(trail, path, ip):
                    is_bot = True
                elif ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
            except Exception:
                pass
            out.append('''
            repl2 = '''            is_bot = False
            try:
                if ip and _lean_ip_is_quarantined(cur, ip):
                    is_bot = True
                elif _is_sailor_sas_id_path(path) or _lean_behavior_confident_bot(trail, path, ip):
                    is_bot = True
                elif _lean_same_page_swarm_bot(cur, ip=ip or "", path=path, page_trail=trail, window_minutes=30):
                    is_bot = True
            except Exception:
                pass
            if is_bot:
                continue
            out.append('''
            if needle2 in chunk:
                chunk = chunk.replace(needle2, repl2, 1)
            else:
                print("CHUNK START", chunk[chunk.find("is_bot") : chunk.find("is_bot") + 800])
                raise SystemExit("is_bot block not found in offline")
        else:
            chunk = chunk.replace(needle, repl, 1)

    # Also force kind anon only in append who line
    chunk = chunk.replace(
        '"kind": "bot" if is_bot else "anon",\n                    "who": (f"Bot {ip}" if is_bot else f"Guest {ip}") if ip else ("Bot" if is_bot else "Guest"),',
        '"kind": "anon",\n                    "who": f"Guest {ip}" if ip else "Guest",',
        1,
    )

    text = text[:start] + chunk + text[end:]

    # Update offline section note in HTML
    old_note = "Outside the live window. ▶ show/hide URL trail. Session total = first page → last action (not 15m timeout). Staff/agent hidden."
    new_note = "Completed real visits only (no bots). ▶ show/hide URL trail. Session total = first page → last action."
    if old_note in text:
        text = text.replace(old_note, new_note, 1)
    else:
        for n in (
            "Outside the live window. ▶ show/hide URL trail to audit. Bots included for review; staff/agent hidden.",
            "Outside the live window. ▶ show/hide URL trail. Session total = first page → last action (not 15m timeout). Staff/agent hidden.",
        ):
            if n in text:
                text = text.replace(n, new_note, 1)
                break

    # Client: also filter bots from offline render
    old_js = "var rows=d.offline||[];\n    if(!rows.length){ box.innerHTML=\"<p class='note'>No completed sessions in the last 24h outside the live window.</p>\"; return; }"
    new_js = "var rows=(d.offline||[]).filter(function(r){ return r && r.kind!==\"bot\"; });\n    if(!rows.length){ box.innerHTML=\"<p class='note'>No completed real visits in the last 24h outside the live window.</p>\"; return; }"
    if old_js in text:
        text = text.replace(old_js, new_js, 1)
    elif 'var rows=d.offline||[];' in text[text.find("function renderOffline") : text.find("function renderOffline") + 400]:
        frag = text[text.find("function renderOffline") : text.find("function renderOffline") + 500]
        frag2 = frag.replace(
            "var rows=d.offline||[];",
            'var rows=(d.offline||[]).filter(function(r){ return r && r.kind!=="bot"; });',
            1,
        )
        text = text.replace(frag, frag2, 1)

    if text == orig:
        raise SystemExit("no changes")
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK offline humans only (+{len(text) - len(orig)} bytes)")


if __name__ == "__main__":
    main()
