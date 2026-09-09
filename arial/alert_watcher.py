#!/usr/bin/env python3
"""Arm/disarm → WhatsApp alerts for every configured site (Hansekop, Voelklip), via the isolated Baileys worker.

Trigger = the keypad press (arial-api writes <site>_keypad_log.json the instant a button is hit) → instant message.
Arms/disarms made outside the keypad are picked up from the site's Olarm activity feed; the Olarm echo of a press we
already alerted is suppressed. Per-recipient scope: "all" = every arm/disarm at the site, "own" = only the ones that
recipient performed (e.g. Onguard). Every outbound message is appended to the shared admin log
/var/www/sailingsa/data/whatsapp_log.jsonl (the worker appends inbound POWER replies there too).
Read-only towards arial-api / Olarm / Tuya; no production code modified."""
import json, os, time, datetime, urllib.request, urllib.error, logging, signal

ROOT = "/opt/arial-whatsapp-poc"
STATE = f"{ROOT}/state"
CTRL = f"http://127.0.0.1:{os.getenv('WAPOC_PORT', '8009')}"
TOKEN = os.getenv("WAPOC_TOKEN", "")
SITES_PATH = f"{STATE}/sites.json"
SEEN_PATH = f"{STATE}/alerts_seen.json"
ADMIN_LOG = os.getenv("WA_ADMIN_LOG", "/var/www/sailingsa/data/whatsapp_log.jsonl")
POLL_S = float(os.getenv("WATCHER_POLL_S", "5"))
MAX_AGE_S = 10 * 60
MAX_PER_HOUR = 20
DEDUPE_S = 240
ALERT_STATES = {"ARMED", "DISARMED", "STAY ARMED", "SLEEP ARMED"}
KEYPAD_STATE = {"area-arm": "ARMED", "area-disarm": "DISARMED", "area-stay": "STAY ARMED", "area-sleep": "SLEEP ARMED"}
SAST = datetime.timezone(datetime.timedelta(hours=2))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("watcher")
running = True


def get(url, timeout=6):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"} if url.startswith(CTRL) else {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def post(url, body, timeout=40):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())


def load_json(path, default):
    try:
        return json.load(open(path))
    except Exception:  # noqa: BLE001
        return default


def save_seen(seen):
    tmp = SEEN_PATH + ".tmp"
    json.dump(sorted(seen)[-1000:], open(tmp, "w")); os.replace(tmp, SEEN_PATH); os.chmod(SEEN_PATH, 0o600)


def admin_log(rec):
    try:
        with open(ADMIN_LOG, "a") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError as e:
        log.warning("admin log write failed: %s", e)


def row_key(site, r):
    return f"{site}|{r.get('at')}|{r.get('title')}|{r.get('state')}"


def keypad_rows(site, cfg, seen, mtimes):
    path = cfg.get("keypad_log")
    if not path:
        return []
    try:
        mtime = os.stat(path).st_mtime
    except OSError:
        return []
    if mtimes.get(site) == mtime:
        return []
    mtimes[site] = mtime
    out = []
    for e in load_json(path, []) or []:
        state = KEYPAD_STATE.get(str(e.get("action") or ""))
        if not state:
            continue
        at_ms = int(float(e.get("at") or 0) * 1000)
        k = f"{site}|kp|{at_ms}|{e.get('area')}|{state}"
        if k in seen:
            continue
        who = str(e.get("label") or e.get("from") or "").strip()
        dt = datetime.datetime.fromtimestamp(at_ms / 1000, SAST)
        out.append({"tab": "areas", "title": e.get("area") or "", "state": state, "actor": who, "via": "Remote", "at": at_ms,
                    "date": dt.strftime("%d %b %Y"), "time": dt.strftime("%H:%M"), "_key": k,
                    "activity": " · ".join(x for x in (f"{e.get('area') or ''} {state}".strip(), who, "Remote") if x)})
    return out


def power_line(cfg, act_power):
    ac_ok = (act_power or {}).get("acOk")
    mains = "Power OK" if ac_ok is not False else "A/C FAILURE (alarm on battery)"
    meter = cfg.get("meter")
    if not meter:
        return f"Alarm mains: {mains}"
    try:
        p = get(f"{cfg['api']}/api/arial/tuya/probe?device_id={meter}")
    except Exception as e:  # noqa: BLE001
        return f"Power: meter unavailable ({e.__class__.__name__}) · alarm mains: {mains}"
    if not p.get("deviceOk"):
        return f"Power: meter NO LINK ({p.get('tuyaMsg') or 'no fresh reading'}) · alarm mains: {mains}"
    m = {r["code"]: r["value"] for r in (p.get("status") or []) if isinstance(r, dict) and "code" in r}
    parts = []
    if isinstance(m.get("cur_voltage"), (int, float)): parts.append(f"{m['cur_voltage'] / 100:.0f}V")
    if isinstance(m.get("cur_current"), (int, float)): parts.append(f"{m['cur_current'] / 1000:.2f}A")
    if isinstance(m.get("cur_power"), (int, float)): parts.append(f"{m['cur_power'] / 100:.0f} W")
    return (" / ".join(parts) + f" · {mains}") if parts else f"Power: no reading · alarm mains: {mains}"


LINK_PATH = f"{STATE}/link_watch.json"
LINK_POLL_S = 20
LINK_CONFIRM = 3
LINK_NAG_S = 30 * 60


def admin_targets(cfg):
    """Hansekop admins only: recipients with scope 'all' (Kevin, Pingoa). Never scope 'own'."""
    out = []
    for rcp in cfg.get("recipients") or []:
        if str(rcp.get("scope") or "all").lower() != "all":
            continue
        num = str(rcp.get("number") or "").replace(" ", "")
        if num:
            out.append((rcp.get("name") or num, num))
    return out


def meter_reading(p):
    m = {r["code"]: r["value"] for r in ((p or {}).get("status") or []) if isinstance(r, dict) and "code" in r}
    parts = []
    if isinstance(m.get("cur_voltage"), (int, float)):
        parts.append(f"{m['cur_voltage'] / 100:.1f} V")
    if isinstance(m.get("cur_current"), (int, float)):
        parts.append(f"{m['cur_current'] / 1000:.2f} A")
    if isinstance(m.get("cur_power"), (int, float)):
        parts.append(f"{m['cur_power'] / 100:.0f} W")
    return " / ".join(parts)


def last_report_hhmm(p, now=None):
    sh = (p or {}).get("sharing") or {}
    at = sh.get("meterLastReadingAt") or (p or {}).get("readingTs")
    if isinstance(at, (int, float)) and at > 1e9:
        if at > 1e12:
            at = at / 1000.0
        return datetime.datetime.fromtimestamp(float(at), SAST).strftime("%H:%M")
    age = sh.get("meterLastReportAgeS")
    if not isinstance(age, (int, float)) or age < 0:
        return ""
    now = now or datetime.datetime.now(SAST)
    return (now - datetime.timedelta(seconds=float(age))).strftime("%H:%M")


def last_reading_unix(p):
    sh = (p or {}).get("sharing") or {}
    at = sh.get("meterLastReadingAt") or (p or {}).get("readingTs")
    if isinstance(at, (int, float)) and at > 1e9:
        return float(at) / 1000.0 if at > 1e12 else float(at)
    return 0.0


def elapsed_label(seconds):
    s = max(0, int(seconds))
    h, rem = divmod(s, 3600)
    m = rem // 60
    if h and m:
        return f"{h}h{m:02d}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def compose_link(cfg, kind, reading, last, ac_ok, elapsed_s=None):
    now = datetime.datetime.now(SAST)
    when = now.strftime("%d %b %y · %H:%M")
    ac = "Last Alarm AC ="
    if kind == "up":
        lines = [f"{cfg.get('label')} {when}", "Link restored", ac]
        if reading:
            lines.append(reading)
    else:
        el = elapsed_label(elapsed_s or 0)
        loss = f"Link Loss : {last} > {el}" if last else f"Link Loss : {el}"
        lines = [f"{cfg.get('label')} {when}", loss, ac]
        if reading:
            lines.append(reading)
    if cfg.get("url"):
        lines.append(cfg["url"])
    return "\n".join(lines)


def send_admin(cfg, text, sent_times, site, kind):
    ok_any = False
    for name, number in admin_targets(cfg):
        sent_times[:] = [t for t in sent_times if time.time() - t < 3600]
        if len(sent_times) >= MAX_PER_HOUR:
            log.warning("rate cap hit; not sending link %s to %s", kind, name)
            break
        res = post(f"{CTRL}/send", {"number": number, "text": text})
        sent_times.append(time.time())
        admin_log({"t": time.time(), "dir": "out", "kind": "link-" + kind, "site": site, "to": name,
                   "ok": bool(res.get("ok")), "id": res.get("id"), "error": res.get("error"),
                   "text": text})
        log.info("link %s %s -> %s ok=%s", kind, site, name, res.get("ok"))
        ok_any = ok_any or bool(res.get("ok"))
    return ok_any


def check_meter_link(site, cfg, watch, sent_times, act):
    if not cfg.get("meter"):
        return
    st = dict(watch.get(site) or {})
    ac_ok = ((act or {}).get("power") or {}).get("acOk")
    p = None
    try:
        p = get(f"{cfg['api']}/api/arial/tuya/probe?device_id={cfg['meter']}")
        linked = bool(p.get("deviceOk") and p.get("tokenOk"))
    except Exception as e:  # noqa: BLE001
        linked = False
        log.warning("%s meter probe: %s", site, e.__class__.__name__)
    reading = meter_reading(p) or st.get("last_reading") or ""
    last = last_report_hhmm(p) or st.get("last_hhmm") or ""
    loss_at = last_reading_unix(p) or float(st.get("loss_at") or 0)
    if reading:
        st["last_reading"] = reading
    if last:
        st["last_hhmm"] = last
    if loss_at:
        st["loss_at"] = loss_at
    now = time.time()
    elapsed_s = now - loss_at if loss_at else 0
    if linked:
        if st.get("down"):
            if not send_admin(cfg, compose_link(cfg, "up", reading, last, ac_ok, elapsed_s), sent_times, site, "up"):
                watch[site] = st
                return
        st["down"] = False
        st["streak"] = 0
        st["alerted"] = False
        st["last_alert"] = 0
        st["down_since"] = 0
        st["loss_at"] = 0
        watch[site] = st
        return
    streak = int(st.get("streak") or 0) + 1
    st["streak"] = streak
    if streak < LINK_CONFIRM:
        watch[site] = st
        return
    if not st.get("down"):
        st["down"] = True
        st["down_since"] = loss_at or now
    last_alert = float(st.get("last_alert") or 0)
    if not st.get("alerted"):
        if send_admin(cfg, compose_link(cfg, "down", reading, last, ac_ok, elapsed_s), sent_times, site, "down"):
            st["alerted"] = True
            st["last_alert"] = now
    elif now - last_alert >= LINK_NAG_S:
        if send_admin(cfg, compose_link(cfg, "nag", reading, last, ac_ok, elapsed_s), sent_times, site, "nag"):
            st["last_alert"] = now
    watch[site] = st


ALARM_BURST_S = 90          # zones tripping together after the first ALARM row are one event, not N messages
AFTER_ALARM_S = 15 * 60     # a DISARM within this window is reported as "after alarm"


def is_alarm_row(r):
    st = str(r.get("state") or "").upper()
    return "ALARM" in st or "PANIC" in st or "FIRE" in st or "EMERGENCY" in st


def compose(cfg, row, act_power):
    d = str(row.get("date") or "")
    try:
        d = datetime.datetime.strptime(d, "%d %b %Y").strftime("%d %b %y")
    except ValueError:
        pass
    when = f"{d} · {row.get('time') or ''}".strip(" ·")
    act_line = row.get("activity") or ""
    if is_alarm_row(row):
        act_line = "\U0001F6A8 " + act_line
    elif row.get("_after_alarm"):
        act_line += f"  (after ALARM at {row['_after_alarm']})"
    links = cfg.get("url") or ""
    if cfg.get("clip_page") and row.get("at"):
        from urllib.parse import quote
        ac = (act_power or {}).get("acOk")
        ev_url = (f"{cfg['clip_page']}?t={int(float(row['at']) // 1000)}&ev={quote(str(row.get('activity') or ''))}"
                  f"&s={quote(str(row.get('state') or '').upper())}&p={'ok' if ac is True else 'fail' if ac is False else ''}")
        links = f"\u25B6 Replay: {ev_url}\nLIVE: {ev_url}&live=1"
    return f"{cfg.get('label')} {when}\n{act_line}\n{power_line(cfg, act_power)}\n{links}".rstrip()


def event_card(cfg, row, act_power, text):
    """JPEG card (header + 4 stills + LIVE bar) for sites that have cameras; None when not available."""
    if not cfg.get("snaps"):
        return None
    try:
        import base64
        import card
        d = str(row.get("date") or "")
        try:
            d = datetime.datetime.strptime(d, "%d %b %Y").strftime("%d %b %y")
        except ValueError:
            pass
        st = str(row.get("state") or "").upper()
        ac = (act_power or {}).get("acOk")
        snaps = card.fetch_snaps(cfg["snaps"])
        via = str(row.get("via") or "").strip() or ("Remote" if row.get("actor") else "")
        main = card.render_main(cfg.get("label") or "", d, str(row.get("time") or ""), str(row.get("title") or ""), "ALARM" if is_alarm_row(row) else st,
                                str(row.get("actor") or "").strip(), via, ac if isinstance(ac, bool) else None, snaps)
        live = card.render_live(cfg.get("label") or "")
        b64 = lambda b: base64.b64encode(b).decode()  # noqa: E731
        return {"main": b64(main), "main_thumb": b64(card.thumb(main)), "live": b64(live), "live_thumb": b64(card.thumb(live)),
                "cams": sorted(snaps), "power": "ok" if ac is True else "fail" if ac is False else ""}
    except Exception as e:  # noqa: BLE001
        log.warning("card render failed: %s", e)
        return None


def prebuild_clips(cfg, at_ms):
    """Ask the warm keeper to cut the -5/+15 clips for all four cameras once the window is complete (t+21s),
    so tapping the card later plays instantly instead of waiting for the encode."""
    import ssl
    import threading

    def run():
        t = int(at_ms // 1000)
        time.sleep(max(0, (t + 21) - time.time()))
        base = cfg["snaps"].rsplit("/", 1)[0]
        for cam in ("garage", "workshop", "pool", "driveway"):
            try:
                req = urllib.request.Request(f"{base}/clip?cam={cam}&t={t}&pre=5&post=15", headers={"Range": "bytes=0-0"})
                with urllib.request.urlopen(req, timeout=60, context=ssl.create_default_context()) as r:
                    r.read(1)
            except Exception as e:  # noqa: BLE001
                log.info("prebuild %s t=%s: %s", cam, t, e)
    threading.Thread(target=run, daemon=True).start()


def event_urls(cfg, row, power):
    from urllib.parse import quote
    base = (f"{cfg['clip_page']}?t={int(float(row['at']) // 1000)}&ev={quote(str(row.get('activity') or ''))}"
            f"&s={quote(str(row.get('state') or '').upper())}&p={power}")
    return base, base + "&live=1"


def targets(cfg, row):
    """Recipients for this row: scope 'all' always; scope 'own' only when the row's actor is that recipient."""
    actor = str(row.get("actor") or row.get("olarmUser") or "").strip().lower()
    out = []
    if is_alarm_row(row):
        return [(r.get("name") or str(r.get("number") or ""), str(r.get("number") or "").replace(" ", ""))
                for r in (cfg.get("recipients") or []) if r.get("number") and str(r.get("scope") or "all").lower() == "all"]
    for rcp in cfg.get("recipients") or []:
        num = str(rcp.get("number") or "").replace(" ", "")
        if not num:
            continue
        scope = str(rcp.get("scope") or "all").lower()
        names = {str(n).strip().lower() for n in ([rcp.get("name")] + list(rcp.get("aliases") or [])) if n}
        if scope == "all" or (scope == "own" and actor and actor in names):
            out.append((rcp.get("name") or num, num))
    return out


def main():
    seen = set(load_json(SEEN_PATH, []) or [])
    sites = load_json(SITES_PATH, {})
    sent_times, mtimes, acts, last_poll, last_alarm, last_link = [], {}, {}, {}, {}, {}
    link_watch = load_json(LINK_PATH, {}) or {}
    # recent presses (site, area, state) -> at_ms, persisted so a restart cannot turn the Olarm echo into a 2nd alert;
    # also seeded from every site's keypad log on start for the same reason.
    RECENT_PATH = f"{STATE}/alerts_recent.json"
    recent = {tuple(k.split("|", 2)): v for k, v in (load_json(RECENT_PATH, {}) or {}).items()}
    for site, cfg in sites.items():
        for e in load_json(cfg.get("keypad_log") or "", []) or []:
            state = KEYPAD_STATE.get(str(e.get("action") or ""))
            if state and time.time() - float(e.get("at") or 0) < 2 * DEDUPE_S:
                sig0 = (site, str(e.get("area") or ""), state)
                recent[sig0] = max(recent.get(sig0, 0), float(e.get("at") or 0) * 1000)
    def save_recent():
        try:
            json.dump({"|".join(k): v for k, v in recent.items() if time.time() * 1000 - v < 3600 * 1000}, open(RECENT_PATH, "w"))
        except OSError as e:
            log.warning("recent save failed: %s", e)
    first = True
    log.info("watcher up; sites=%s", {s: [r.get("name") + ":" + str(r.get("scope", "all")) for r in c.get("recipients", [])] for s, c in sites.items()})
    while running:
        try:
            sites = load_json(SITES_PATH, sites)
            now_ms = time.time() * 1000
            for site, cfg in sites.items():
                if time.time() - last_poll.get(site, 0) >= POLL_S:
                    try:
                        acts[site] = get(f"{cfg['api']}/api/arial/activity")
                    except Exception as e:  # noqa: BLE001
                        log.warning("%s activity poll error: %s", site, e)
                    last_poll[site] = time.time()
                if cfg.get("meter") and time.time() - last_link.get(site, 0) >= LINK_POLL_S:
                    try:
                        check_meter_link(site, cfg, link_watch, sent_times, acts.get(site) or {})
                        tmp = LINK_PATH + ".tmp"
                        json.dump(link_watch, open(tmp, "w"))
                        os.replace(tmp, LINK_PATH)
                        os.chmod(LINK_PATH, 0o600)
                    except Exception as e:  # noqa: BLE001
                        log.warning("%s link watch: %s", site, e)
                    last_link[site] = time.time()
                act = acts.get(site) or {}
                olarm_rows = [r for r in (act.get("events") or []) if isinstance(r, dict)
                              and ((str(r.get("tab")) == "areas" and str(r.get("state") or "").upper() in ALERT_STATES)
                                   or is_alarm_row(r))]
                if first:
                    seen |= {row_key(site, r) for r in olarm_rows}
                    seen |= {r["_key"] for r in keypad_rows(site, cfg, set(), mtimes)}
                    continue
                rows = keypad_rows(site, cfg, seen, mtimes) + sorted(olarm_rows, key=lambda x: x.get("at") or 0)
                for r in rows:
                    k = r.get("_key") or row_key(site, r)
                    if k in seen:
                        continue
                    seen.add(k); save_seen(seen)
                    age = (now_ms - float(r.get("at") or 0)) / 1000
                    if age > MAX_AGE_S:
                        log.info("skip old %s age=%.0fs", k, age); continue
                    sig = (site, str(r.get("title") or ""), str(r.get("state") or "").upper())
                    is_press = "|kp|" in k
                    if not is_press and abs(float(r.get("at") or 0) - recent.get(sig, 0)) < DEDUPE_S * 1000:
                        log.info("dedupe %s (Olarm echo of an alerted press)", k); continue
                    if is_press:
                        recent[sig] = float(r.get("at") or 0); save_recent()
                    at_ms = float(r.get("at") or 0)
                    if is_alarm_row(r):
                        if at_ms - last_alarm.get(site, 0) < ALARM_BURST_S * 1000:
                            last_alarm[site] = max(last_alarm[site], at_ms)
                            log.info("alarm burst %s (within %ss of first)", k, ALARM_BURST_S); continue
                        last_alarm[site] = at_ms
                    elif str(r.get("state") or "").upper() == "DISARMED" and 0 < at_ms - last_alarm.get(site, 0) < AFTER_ALARM_S * 1000:
                        r["_after_alarm"] = datetime.datetime.fromtimestamp(last_alarm[site] / 1000, SAST).strftime("%H:%M")
                    text = compose(cfg, r, act.get("power"))
                    card_img = event_card(cfg, r, act.get("power"), text)
                    if cfg.get("snaps") and r.get("at"):
                        prebuild_clips(cfg, float(r["at"]))
                    for name, number in targets(cfg, r):
                        sent_times[:] = [t for t in sent_times if time.time() - t < 3600]
                        if len(sent_times) >= MAX_PER_HOUR:
                            log.warning("rate cap hit; not sending %s to %s", k, name); break
                        res, live_res = {}, None
                        if card_img and cfg.get("clip_page"):
                            replay_url, live_url = event_urls(cfg, r, card_img["power"])
                            title = f"{cfg.get('label')} \u00b7 {r.get('title') or ''} {str(r.get('state') or '').upper()}".strip()
                            # ONE message: the card is the clickable preview (tap -> REPLAY); the two action links sit under it.
                            res = post(f"{CTRL}/send-link-card", {"number": number, "url": replay_url, "title": title,
                                       "description": f"{r.get('date') or ''} {r.get('time') or ''} \u00b7 tap to replay",
                                       "image": card_img["main"], "thumb": card_img["main_thumb"],
                                       "text": replay_url})
                            if not res.get("ok"):
                                log.warning("link card failed (%s); falling back to image+caption", res.get("error"))
                                res = post(f"{CTRL}/send-image", {"number": number, "caption": text, "image": card_img["main"]})
                        if not res.get("ok"):
                            res = post(f"{CTRL}/send", {"number": number, "text": text})
                        sent_times.append(time.time())
                        acks = [x.get("name") for x in (res.get("acks") or [])]
                        admin_log({"t": time.time(), "dir": "out", "kind": "alert", "site": site, "to": name, "number": number,
                                   "ok": bool(res.get("ok")), "id": res.get("id"), "acks": acks, "error": res.get("error"),
                                   "trigger": "keypad" if is_press else "olarm", "text": text,
                                   "card": bool(res.get("card") or res.get("image")), "cams": card_img["cams"] if card_img else [],
                                   "live_card": {"ok": bool(live_res.get("ok")), "id": live_res.get("id"),
                                                 "acks": [x.get("name") for x in (live_res.get("acks") or [])]} if live_res else None})
                        log.info("alert %s -> %s ok=%s acks=%s", k, name, res.get("ok"), acks)
            if first:
                first = False; save_seen(seen); log.info("seeded %d existing rows as seen", len(seen))
        except Exception as e:  # noqa: BLE001
            log.warning("loop error: %s", e)
        time.sleep(1.0)


def stop(*_):
    global running
    running = False


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    main()
