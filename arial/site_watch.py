#!/usr/bin/env python3
"""Cloud-side heartbeat watch: Olarm Offline + Tuya reporting fail.

If mains is down and the panel battery is dead, Olarm cannot send an AC-loss event.
The communicator just stops — that must be reported as "Olarm Offline" (SMS + WhatsApp).

Tuya meter ingest must never go silent. A stale/stopped sharing worker is reported as
"Tuya reporting fail" so it can be investigated.

Read-only towards arial-api. Sends via the isolated WhatsApp PoC and optional SMS HTTP.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import signal
import time
import urllib.error
import urllib.request

ROOT = os.getenv("WAPOC_ROOT", "/opt/arial-whatsapp-poc")
STATE = f"{ROOT}/state"
CTRL = f"http://127.0.0.1:{os.getenv('WAPOC_PORT', '8009')}"
TOKEN = os.getenv("WAPOC_TOKEN", "")
SITES_PATH = os.getenv("ARIAL_SITES_PATH", f"{STATE}/sites.json")
WATCH_PATH = f"{STATE}/site_watch.json"
ADMIN_LOG = os.getenv("WA_ADMIN_LOG", "/var/www/sailingsa/data/whatsapp_log.jsonl")
POLL_S = float(os.getenv("SITE_WATCH_POLL_S", "20"))
CONFIRM = int(os.getenv("SITE_WATCH_CONFIRM", "3"))
NAG_S = float(os.getenv("SITE_WATCH_NAG_S", str(2 * 60 * 60)))
OLARM_GRACE_S = float(os.getenv("SITE_WATCH_OLARM_GRACE_S", str(3 * 60)))
TUYA_STALE_S = float(os.getenv("TUYA_SHARING_STALE_S") or os.getenv("SITE_WATCH_TUYA_STALE_S") or "180")
SMS_URL = os.getenv("ARIAL_SMS_URL", "").strip()
SMS_TOKEN = os.getenv("ARIAL_SMS_TOKEN", "").strip()
SMS_FROM = os.getenv("ARIAL_SMS_FROM", "Arial").strip()
SAST = datetime.timezone(datetime.timedelta(hours=2))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("site-watch")
running = True


def _now_sast() -> datetime.datetime:
    return datetime.datetime.now(SAST)


def fmt_when(ts: float | None = None) -> str:
    dt = datetime.datetime.fromtimestamp(ts, SAST) if ts else _now_sast()
    return dt.strftime("%d %b %y · %H:%M")


def fmt_when_long(ts: float | None) -> str:
    if not ts:
        return "unknown"
    return datetime.datetime.fromtimestamp(float(ts), SAST).strftime("%d %b %y · %H:%M")


def unix_ts(value) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return 0.0
    if n > 1e12:
        n /= 1000.0
    return n if n > 1e9 else 0.0


def load_json(path, default):
    try:
        return json.load(open(path))
    except Exception:  # noqa: BLE001
        return default


def save_json(path, data) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(data, fh)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def admin_log(rec: dict) -> None:
    try:
        with open(ADMIN_LOG, "a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError as e:
        log.warning("admin log write failed: %s", e)


def get(url: str, timeout: float = 8):
    headers = {}
    if url.startswith(CTRL) and TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def post(url: str, body: dict, timeout: float = 40, headers: dict | None = None):
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read() or b"{}")
        except Exception:  # noqa: BLE001
            return {"ok": False, "error": f"http {e.code}"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e.__class__.__name__)}


def admin_targets(cfg: dict) -> list[tuple[str, str]]:
    out = []
    for rcp in cfg.get("recipients") or []:
        if str(rcp.get("scope") or "all").lower() != "all":
            continue
        num = str(rcp.get("number") or "").replace(" ", "")
        if num:
            out.append((str(rcp.get("name") or num), num))
    return out


def compose_olarm(cfg: dict, kind: str, last_seen: float | None) -> str:
    label = cfg.get("label") or "Site"
    if kind == "up":
        lines = [f"{label} {fmt_when()}", "Olarm Online", "Heartbeat restored"]
        if last_seen:
            lines.append(f"Back since {fmt_when_long(last_seen)}")
    else:
        lines = [
            f"{label} {fmt_when()}",
            "Olarm Offline",
            "Heartbeat fail — AC loss will not send if the panel is dead",
            f"Last seen {fmt_when_long(last_seen)}",
        ]
    if cfg.get("url"):
        lines.append(cfg["url"])
    return "\n".join(lines)


def compose_tuya(cfg: dict, kind: str, last_reading: float | None, detail: str = "") -> str:
    label = cfg.get("label") or "Site"
    if kind == "up":
        lines = [f"{label} {fmt_when()}", "Tuya reporting restored"]
        if last_reading:
            lines.append(f"Reading {fmt_when_long(last_reading)}")
    else:
        lines = [
            f"{label} {fmt_when()}",
            "Tuya reporting fail",
            f"Last power reading {fmt_when_long(last_reading)}",
        ]
        if detail:
            lines.append(detail)
    if cfg.get("url"):
        lines.append(cfg["url"])
    return "\n".join(lines)


def olarm_offline(panel: dict | None) -> bool:
    if not panel:
        return True
    device = panel.get("device") if isinstance(panel.get("device"), dict) else panel
    status = str(device.get("deviceStatus") or panel.get("deviceStatus") or "").strip().lower()
    if status:
        return status != "online"
    return True


def olarm_down(panel: dict | None, last_seen: float, now: float, grace_s: float = OLARM_GRACE_S) -> bool:
    """True only for an explicit Olarm offline, or a heartbeat older than grace.

    A refused/restarted local API is not a dead panel — that is what sent
    Voelklip Offline at 12:59 while the communicator was up (last seen 12:58).
    """
    if panel:
        device = panel.get("device") if isinstance(panel.get("device"), dict) else panel
        status = str(device.get("deviceStatus") or panel.get("deviceStatus") or "").strip().lower()
        if status == "online":
            return False
        if status:
            return True
    if not last_seen:
        return False
    return (now - float(last_seen)) > grace_s


def olarm_last_seen(panel: dict | None) -> float:
    if not panel:
        return 0.0
    device = panel.get("device") if isinstance(panel.get("device"), dict) else panel
    return unix_ts(device.get("deviceTimestamp") or panel.get("deviceTimestamp"))


def tuya_last_reading(probe: dict | None) -> float:
    if not probe:
        return 0.0
    last = probe.get("lastReading") if isinstance(probe.get("lastReading"), dict) else {}
    sharing = probe.get("sharing") if isinstance(probe.get("sharing"), dict) else {}
    return unix_ts(
        last.get("ts")
        or sharing.get("meterLastReadingAt")
        or probe.get("readingTs")
        or probe.get("lastReadingTs")
    )


def tuya_fail(probe: dict | None, now: float, stale_s: float = TUYA_STALE_S) -> tuple[bool, str]:
    if not probe:
        return True, "meter probe unavailable"
    last = tuya_last_reading(probe)
    age = (now - last) if last else None
    if probe.get("deviceOk") and probe.get("tokenOk") and age is not None and age <= stale_s:
        return False, ""
    if age is None:
        return True, str(probe.get("tuyaMsg") or "no fresh reading")
    if age > stale_s:
        hint = str(probe.get("tuyaMsg") or "sharing link stale")
        return True, hint
    return True, str(probe.get("tuyaMsg") or "meter NO LINK")


def send_sms(number: str, text: str) -> dict:
    if not SMS_URL:
        return {"ok": False, "error": "sms not configured"}
    headers = {}
    if SMS_TOKEN:
        headers["Authorization"] = f"Bearer {SMS_TOKEN}"
    return post(SMS_URL, {"to": number, "text": text, "from": SMS_FROM}, timeout=20, headers=headers)


def send_whatsapp(number: str, text: str) -> dict:
    headers = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
    return post(f"{CTRL}/send", {"number": number, "text": text}, headers=headers)


def deliver(cfg: dict, site: str, kind: str, text: str) -> bool:
    """SMS first (site can be dead), WhatsApp second. One success is enough."""
    ok_any = False
    for name, number in admin_targets(cfg):
        sms = send_sms(number, text)
        wa = send_whatsapp(number, text)
        ok = bool(sms.get("ok") or wa.get("ok"))
        ok_any = ok_any or ok
        admin_log({
            "t": time.time(),
            "dir": "out",
            "kind": kind,
            "site": site,
            "to": name,
            "ok": ok,
            "sms_ok": bool(sms.get("ok")),
            "sms_error": sms.get("error"),
            "wa_ok": bool(wa.get("ok")),
            "wa_error": wa.get("error"),
            "wa_id": wa.get("id"),
            "text": text,
        })
        log.info("%s %s -> %s sms=%s wa=%s", kind, site, name, sms.get("ok"), wa.get("ok"))
    return ok_any


def _edge(st: dict, down: bool, now: float) -> str | None:
    """Confirm down/up, then fire once (and nag). Returns 'down', 'up', 'nag', or None."""
    if down:
        streak = int(st.get("streak") or 0) + 1
        st["streak"] = streak
        if streak < CONFIRM:
            return None
        if not st.get("down"):
            st["down"] = True
            st["down_since"] = now
            st["alerted"] = False
        last_alert = float(st.get("last_alert") or 0)
        if not st.get("alerted"):
            return "down"
        if now - last_alert >= NAG_S:
            return "nag"
        return None
    if st.get("down"):
        st["down"] = False
        st["streak"] = 0
        st["alerted"] = False
        st["last_alert"] = 0
        st["down_since"] = 0
        return "up"
    st["streak"] = 0
    return None


def mark_sent(st: dict, now: float) -> None:
    st["alerted"] = True
    st["last_alert"] = now


def check_olarm(site: str, cfg: dict, watch: dict) -> None:
    st = dict((watch.get("olarm") or {}).get(site) or {})
    panel = None
    try:
        panel = get(f"{cfg['api']}/api/arial/panel")
    except Exception as e:  # noqa: BLE001
        log.warning("%s panel poll: %s", site, e.__class__.__name__)
    last_seen = olarm_last_seen(panel) or float(st.get("last_seen") or 0)
    if last_seen:
        st["last_seen"] = last_seen
    now = time.time()
    edge = _edge(st, olarm_down(panel, last_seen, now), now)
    if edge == "down" or edge == "nag":
        if deliver(cfg, site, "olarm-offline", compose_olarm(cfg, "down", last_seen)):
            mark_sent(st, now)
    elif edge == "up":
        if deliver(cfg, site, "olarm-online", compose_olarm(cfg, "up", time.time())):
            mark_sent(st, now)
    watch.setdefault("olarm", {})[site] = st


def check_tuya(site: str, cfg: dict, watch: dict) -> None:
    if not cfg.get("meter"):
        return
    st = dict((watch.get("tuya") or {}).get(site) or {})
    probe = None
    try:
        probe = get(f"{cfg['api']}/api/arial/tuya/probe?device_id={cfg['meter']}")
    except Exception as e:  # noqa: BLE001
        log.warning("%s tuya probe: %s", site, e.__class__.__name__)
    last = tuya_last_reading(probe) or float(st.get("last_reading") or 0)
    if last:
        st["last_reading"] = last
    fail, detail = tuya_fail(probe, time.time())
    now = time.time()
    edge = _edge(st, fail, now)
    if edge == "down" or edge == "nag":
        if deliver(cfg, site, "tuya-fail", compose_tuya(cfg, "down", last, detail)):
            mark_sent(st, now)
    elif edge == "up":
        if deliver(cfg, site, "tuya-up", compose_tuya(cfg, "up", last)):
            mark_sent(st, now)
    watch.setdefault("tuya", {})[site] = st


def main() -> None:
    watch = load_json(WATCH_PATH, {}) or {}
    log.info("site-watch up sms=%s wa=%s", bool(SMS_URL), bool(TOKEN))
    while running:
        sites = load_json(SITES_PATH, {}) or {}
        for site, cfg in sites.items():
            if not isinstance(cfg, dict) or not cfg.get("api"):
                continue
            try:
                check_olarm(site, cfg, watch)
            except Exception as e:  # noqa: BLE001
                log.warning("%s olarm watch: %s", site, e)
            try:
                check_tuya(site, cfg, watch)
            except Exception as e:  # noqa: BLE001
                log.warning("%s tuya watch: %s", site, e)
        save_json(WATCH_PATH, watch)
        for _ in range(int(max(1, POLL_S))):
            if not running:
                break
            time.sleep(1)


def stop(*_):
    global running
    running = False


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    main()
