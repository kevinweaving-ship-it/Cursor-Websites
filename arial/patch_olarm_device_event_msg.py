#!/usr/bin/env python3
"""Patch live arial_api.format_olarm_event to quote Olarm device eventMsg + SERVER."""
from __future__ import annotations

import time
from pathlib import Path

p = Path("/opt/aerialnet-arial/arial_api.py")
text = p.read_text(encoding="utf-8")
if "Use Olarm's eventMsg verbatim" in text:
    print("already_patched", p)
    raise SystemExit(0)

bak = p.with_suffix(p.suffix + ".bak_olarm_msg_" + time.strftime("%Y%m%dT%H%M%SZ"))
bak.write_text(text, encoding="utf-8")

old = """    state_lab = _event_state_label(str(event.get("eventState") or ""))
    if action.lower() in DEVICE_EVENT_ACTIONS:
        label = "Olarm Offline" if str(event.get("eventState") or "").lower() == "offline" else "Olarm Online"
    elif tab == "power" and msg:
        label = msg
    time_s, date_s = _sa_stamp(event.get("eventTime"))
    actor = _arial_event_actor(tab, event, device)
    via = _activity_via(actor)
    if not actor and tab == "areas" and str(event.get("eventState") or "").lower() in {"arm", "disarm", "stay", "sleep"}:
        # No keypad user matched: it came from the Olarm app / panel. Show the source, never the Olarm account name.
        if str(event.get("userFullname") or "").strip():
            via = "App"
        elif str(event.get("eventState") or "").lower() in {"arm", "stay", "sleep"}:
            via = "Auto"      # no user at all: the panel's own auto-arm schedule
        else:
            via = "Panel"     # disarmed at the physical panel keypad
    activity = _activity_line(label, state_lab, actor, via)
"""

new = """    state_lab = _event_state_label(str(event.get("eventState") or ""))
    if action.lower() in DEVICE_EVENT_ACTIONS:
        # Use Olarm's eventMsg verbatim (e.g. "OFFLINE - Arial - Hansekop"). Do not invent titles.
        label = msg or state_lab or action
        state_lab = ""  # already present in eventMsg
    elif tab == "power" and msg:
        label = msg
    time_s, date_s = _sa_stamp(event.get("eventTime"))
    actor = _arial_event_actor(tab, event, device)
    via = _activity_via(actor)
    if action.lower() in DEVICE_EVENT_ACTIONS and not str(event.get("userFullname") or "").strip():
        # Olarm App shows these as "by SERVER" when there is no user on the device event.
        via = "SERVER"
    elif not actor and tab == "areas" and str(event.get("eventState") or "").lower() in {"arm", "disarm", "stay", "sleep"}:
        # No keypad user matched: it came from the Olarm app / panel. Show the source, never the Olarm account name.
        if str(event.get("userFullname") or "").strip():
            via = "App"
        elif str(event.get("eventState") or "").lower() in {"arm", "stay", "sleep"}:
            via = "Auto"      # no user at all: the panel's own auto-arm schedule
        else:
            via = "Panel"     # disarmed at the physical panel keypad
    if action.lower() in DEVICE_EVENT_ACTIONS and via:
        activity = f"{label} · by {via}" if not str(via).lower().startswith("by ") else f"{label} · {via}"
    else:
        activity = _activity_line(label, state_lab, actor, via)
"""

if old not in text:
    raise SystemExit("format_olarm_event block not found on live")
p.write_text(text.replace(old, new, 1), encoding="utf-8")
print("patched", p, "backup", bak)
