#!/usr/bin/env python3
"""Look for MAC Media on the live WhatsApp box and bind it when found."""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

GROUPS = Path("/opt/sailingsa-whatsapp-poc/state/event-whatsapp/groups.json")
HEALTH = Path("/opt/sailingsa-whatsapp-poc/state/health.json")
ENV = Path("/etc/sailingsa-whatsapp-poc.env")
RID = "2026-10-17-mac-tsl-wc-team-sailing"
LOOK_URL = "http://127.0.0.1:8012/refresh-groups"
SAILING_BOX = "27683934779"


def env_token() -> str:
    token = ""
    if ENV.is_file():
        for line in ENV.read_text().splitlines():
            if line.startswith("WAPOC_TOKEN="):
                token = line.split("=", 1)[1].strip().strip("'").strip('"')
    return token


def wa_up() -> bool:
    try:
        return json.loads(HEALTH.read_text()).get("state") == "UP"
    except Exception:
        return False


def refresh(token: str) -> dict:
    req = urllib.request.Request(
        LOOK_URL,
        data=b"{}",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def groups() -> list:
    try:
        data = json.loads(GROUPS.read_text())
    except Exception:
        return []
    return data.get("groups") or []


def is_mac_media(name: str) -> bool:
    s = (name or "").lower()
    if "mac" in s and "media" in s:
        return True
    if "ssl" in s and "mac" in s:
        return True
    if "tsl" in s and "media" in s:
        return True
    if "team sailing" in s and "media" in s:
        return True
    return False


def bind(jid: str, subject: str) -> None:
    jid = jid.replace("'", "")
    subject = subject.replace("'", "''")
    sql = (
        "UPDATE event_whatsapp_groups SET group_jid = '%s', group_name = COALESCE(NULLIF('%s',''), group_name), "
        "monitor_number = COALESCE(NULLIF(monitor_number,''), '" + SAILING_BOX + "'), "
        "display_number = COALESCE(NULLIF(display_number,''), '" + SAILING_BOX + "') "
        "WHERE regatta_id = '%s' AND (group_jid IS NULL OR btrim(group_jid) = '');"
    ) % (jid, subject, RID)
    subprocess.check_call(["sudo", "-u", "postgres", "psql", "-d", "sailors_master", "-c", sql])


def main() -> int:
    token = env_token()
    if not wa_up():
        print("WA not UP — skip look")
        return 0
    if token:
        try:
            out = refresh(token)
            print("refresh", json.dumps(out))
        except Exception as e:
            print("refresh failed", e)
            time.sleep(0)
    found = None
    print("groups:")
    for g in groups():
        name = g.get("subject") or ""
        jid = g.get("jid") or ""
        print(" ", name, jid)
        if is_mac_media(name) and jid:
            found = (jid, name)
    if not found:
        print("MAC Media not in participating groups")
        return 0
    print("BIND", found)
    bind(found[0], found[1])
    print("bound")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
