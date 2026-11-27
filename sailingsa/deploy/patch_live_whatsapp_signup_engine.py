#!/usr/bin/env python3
"""Stabilize live WhatsApp box so Home signup Request Code can send.

Run on the box:
  python3 sailingsa/deploy/patch_live_whatsapp_signup_engine.py
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path

POC = Path("/opt/arial-whatsapp-poc/poc.js")
API = Path("/var/www/sailingsa/api/api.py")
TS = datetime.now().strftime("%Y%m%d_%H%M%S")


def backup(path: Path, tag: str) -> Path:
    dest = Path("/root/backups") / f"{path.name}.{TS}.{tag}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(path.read_text())
    return dest


def must_replace(text: str, old: str, new: str, name: str) -> str:
    if old not in text:
        raise SystemExit(f"missing {name}")
    return text.replace(old, new, 1)


def patch_poc() -> None:
    t = POC.read_text()
    backup(POC, "stabilize")
    t = must_replace(
        t,
        "    shouldSyncHistoryMessage: () => true, // on-demand Midmar history (full sync still off)",
        "    shouldSyncHistoryMessage: () => false, // keep signup/send stable; no history hammer",
        "history-sync",
    )
    t = must_replace(
        t,
        "let sock = null;\nlet stopping = false;",
        "let sock = null;\nlet stopping = false;\nlet reconnectTimer = 0;",
        "reconnect-var",
    )
    t = must_replace(
        t,
        "async function connect() {\n  if (stopping) return;\n  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);\n",
        "async function connect() {\n  if (stopping) return;\n  if (reconnectTimer) { clearTimeout(reconnectTimer); reconnectTimer = 0; }\n"
        "  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);\n",
        "connect-head",
    )
    t = must_replace(
        t,
        "      setState('DOWN', { reason });\n"
        "      st.reconnects += 1;\n"
        "      const delay = Math.min(60000, 2000 * Math.pow(2, Math.min(5, st.reconnects - 1)));\n"
        "      event('reconnect-scheduled', { inMs: delay, attempt: st.reconnects });\n"
        "      setTimeout(connect, delay);\n",
        "      if (stopping) return;\n"
        "      setState('DOWN', { reason });\n"
        "      st.reconnects += 1;\n"
        "      const delay = Math.min(60000, 2000 * Math.pow(2, Math.min(5, st.reconnects - 1)));\n"
        "      event('reconnect-scheduled', { inMs: delay, attempt: st.reconnects });\n"
        "      if (reconnectTimer) clearTimeout(reconnectTimer);\n"
        "      reconnectTimer = setTimeout(() => { reconnectTimer = 0; connect(); }, delay);\n",
        "reconnect-timer",
    )
    t = must_replace(
        t,
        "      setState('UP', { me: st.me });",
        "      st.reconnects = 0;\n      setState('UP', { me: st.me });",
        "reset-reconnects",
    )
    POC.write_text(t)
    print("patched", POC)


def patch_api() -> None:
    t = API.read_text()
    old = '''    try:
        r = httpx.post(send_url, json=payload, headers=headers, timeout=25.0)
        if r.status_code < 400:
            try:
                j = r.json()
                if isinstance(j, dict) and j.get("ok") is False:
                    return False, str(j.get("error") or "WhatsApp send failed")[:180]
            except Exception:
                pass
            return True, "sent"
        return False, f"WhatsApp engine HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)[:180]
'''
    new = '''    def _post(u, body):
        r = httpx.post(u, json=body, headers=headers, timeout=25.0)
        if r.status_code >= 400:
            return False, f"WhatsApp engine HTTP {r.status_code}"
        try:
            j = r.json()
        except Exception:
            j = None
        if isinstance(j, dict) and j.get("ok") is False:
            return False, str(j.get("error") or "WhatsApp send failed")[:180]
        return True, "sent"

    text_url = url
    if text_url.rstrip("/").endswith("/send-image"):
        text_url = text_url[: text_url.rstrip("/").rfind("/")] + "/send"
    text_payload = {"number": phone_intl, "text": text, "to": phone_intl, "phone": phone_intl, "message": text}
    last = "WhatsApp send failed"
    for attempt in range(2):
        try:
            ok, last = _post(send_url, payload)
            if ok:
                return True, "sent"
            if send_url != text_url:
                ok, last = _post(text_url, text_payload)
                if ok:
                    return True, "sent"
        except Exception as e:
            last = str(e)[:180]
        if attempt == 0 and "not UP" in last:
            time.sleep(8)
            continue
        break
    return False, last
'''
    if old not in t:
        raise SystemExit("api engine block missing")
    backup(API, "wa-retry")
    subprocess.check_call(["chattr", "-i", str(API)])
    API.write_text(t.replace(old, new, 1))
    os.system("chown www-data:www-data " + str(API))
    subprocess.check_call(["chattr", "+i", str(API)])
    print("patched", API)


if __name__ == "__main__":
    patch_poc()
    patch_api()
    print("ok")
