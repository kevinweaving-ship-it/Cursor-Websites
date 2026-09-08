#!/opt/cbi-sharing/venv/bin/python
"""Isolated Tuya device-sharing PoC (read-only).

Constants are copied verbatim from Home Assistant core (dev branch, fetched
2026-09-05) homeassistant/components/tuya/const.py and config_flow.py.
SDK: tuya-device-sharing-sdk==0.2.15 (HA manifest.json requirement).

No device commands are ever sent. Only GET/POST calls the SDK itself makes for
login, token refresh, enumeration and the MQTT access-config are used.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

from tuya_sharing import (
    CustomerDevice,
    LoginControl,
    Manager,
    SharingDeviceListener,
    SharingTokenListener,
)
from tuya_sharing.version import VERSION as SDK_VERSION

# --- verbatim from HA const.py -------------------------------------------------
TUYA_CLIENT_ID = "HA_3y9q4ak7g4ephrvke"
# CBI Home OEM schema. haauthorize + tuyaSmart--qrLogin makes CBI say
# "Logging in Home Assistant" / "use the designated APP".
TUYA_SCHEMA = "cbilvcbihome"
QR_FMT = "cbilvcbihome--qrLogin?token={token}"
# ------------------------------------------------------------------------------

ROOT = Path("/opt/cbi-sharing")
STATE = ROOT / "state"
PENDING = STATE / "pending.json"
SESSION = STATE / "session.json"
METER_ID = "bf90676b1341ecb34dse39"

STATE.mkdir(mode=0o700, exist_ok=True)


def _write_private(path: Path, data: Any) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as fh:
        json.dump(data, fh, indent=2, default=str)
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def _load(path: Path) -> dict:
    with open(path) as fh:
        return json.load(fh)


def _redact(tok: str) -> str:
    return f"{tok[:6]}…{tok[-4:]} (len {len(tok)})" if tok else ""



def cmd_status(_args: argparse.Namespace) -> int:
    """Report whether a CBI sharing session exists. Password on disk is not a login."""
    sess = SESSION.exists()
    print("session_file", sess, str(SESSION))
    if sess:
        d = _load(SESSION)
        tok = d.get("token_info") if isinstance(d.get("token_info"), dict) else {}
        print("username", d.get("username"))
        print("uid", tok.get("uid"))
        print("endpoint", d.get("endpoint"))
        print("authorized_at", d.get("authorized_at"))
        return 0
    print("NO_SESSION")
    print("have_env_user_code", bool((os.environ.get("CBI_USER_CODE") or "").strip()))
    print("have_env_password", bool((os.environ.get("CBI_LOGIN_PASSWORD") or "").strip()))
    print("note: tuya-device-sharing-sdk has QR login only (same as Smart Life). Email/password is not a session.")
    return 2

# ---------------------------------------------------------------- step 1: QR ---
def cmd_qr(args: argparse.Namespace) -> int:
    user_code = (args.user_code or os.environ.get("CBI_USER_CODE") or "").strip()
    if not user_code:
        print("CBI_USER_CODE missing (env /etc/cbi-sharing.env or argument)")
        return 2
    args.user_code = user_code
    lc = LoginControl()
    t0 = time.time()
    resp = lc.qr_code(TUYA_CLIENT_ID, TUYA_SCHEMA, args.user_code)
    dt = time.time() - t0
    print(f"qr_code() HTTP round-trip {dt:.2f}s")
    print("raw response:", json.dumps(resp, indent=2))
    if not resp.get("success"):
        return 2
    token = resp["result"]["qrcode"]
    _write_private(PENDING, {"user_code": args.user_code, "qr_token": token,
                             "issued_at": int(time.time()), "raw": resp})
    payload = QR_FMT.format(token=token)
    import qrcode  # type: ignore

    img = qrcode.make(payload, error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=8)
    img.save(STATE / "qr.png")
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, border=1)
    q.add_data(payload)
    q.print_ascii(invert=True)
    print(f"\nQR payload: {payload}\nPNG: {STATE / 'qr.png'}")
    return 0


# --------------------------------------------------------- step 2: poll scan ---
def cmd_poll(args: argparse.Namespace) -> int:
    pend = _load(PENDING)
    lc = LoginControl()
    deadline = time.time() + args.timeout
    n = 0
    while time.time() < deadline:
        n += 1
        ok, info = lc.login_result(pend["qr_token"], TUYA_CLIENT_ID, pend["user_code"])
        if ok:
            age = int(time.time()) - pend["issued_at"]
            sess = {
                "user_code": pend["user_code"],
                "token_info": {k: info[k] for k in ("t", "uid", "expire_time",
                                                   "access_token", "refresh_token")},
                "terminal_id": info["terminal_id"],
                "endpoint": info["endpoint"],
                "username": info.get("username"),
                "authorized_at": int(time.time()),
                "qr_age_at_scan_s": age,
                "raw_login_result_keys": sorted(info.keys()),
            }
            _write_private(SESSION, sess)
            print(f"AUTHORIZED after {n} polls, QR age {age}s")
            print(json.dumps({
                "username": sess["username"], "uid": info["uid"],
                "endpoint": info["endpoint"], "terminal_id": info["terminal_id"],
                "expire_time_s": info["expire_time"],
                "access_token": _redact(info["access_token"]),
                "refresh_token": _redact(info["refresh_token"]),
                "all_keys": sess["raw_login_result_keys"],
            }, indent=2))
            return 0
        code, msg = info.get("code"), info.get("msg")
        print(f"[{n}] not yet: code={code} msg={msg}")
        if code in (1110, 1111) or "expire" in str(msg).lower():  # token expired
            print("QR token expired — run `qr` again")
            return 3
        time.sleep(args.interval)
    print("timed out waiting for scan")
    return 4


# ----------------------------------------------------------- shared manager ---
class TokenPersist(SharingTokenListener):
    def __init__(self) -> None:
        self.refreshes: list[dict] = []

    def update_token(self, token_info: dict[str, Any]) -> None:
        sess = _load(SESSION)
        sess["token_info"] = token_info
        sess["last_refresh_at"] = int(time.time())
        _write_private(SESSION, sess)
        self.refreshes.append({"at": int(time.time()), "expire_time": token_info["expire_time"],
                               "access_token": _redact(token_info["access_token"])})
        print("TOKEN REFRESHED ->", self.refreshes[-1])


def manager_from_session(listener: TokenPersist | None = None) -> tuple[Manager, dict]:
    sess = _load(SESSION)
    mgr = Manager(TUYA_CLIENT_ID, sess["user_code"], sess["terminal_id"],
                  sess["endpoint"], sess["token_info"], listener or TokenPersist())
    return mgr, sess


def device_dump(d: CustomerDevice) -> dict:
    return {
        "id": d.id, "name": d.name, "category": d.category, "product_id": d.product_id,
        "product_name": getattr(d, "product_name", None), "online": d.online, "sub": d.sub,
        "uuid": getattr(d, "uuid", None), "ip": getattr(d, "ip", None),
        "time_zone": getattr(d, "time_zone", None), "set_up": getattr(d, "set_up", None),
        "support_local": getattr(d, "support_local", None),
        "active_time": getattr(d, "active_time", None), "update_time": getattr(d, "update_time", None),
        "status": d.status,
        "status_range": {k: vars(v) for k, v in d.status_range.items()},
        "function": {k: vars(v) for k, v in d.function.items()},
        "local_strategy": d.local_strategy,
    }


# --------------------------------------------------------- step 3: enumerate ---
def cmd_enum(args: argparse.Namespace) -> int:
    mgr, sess = manager_from_session()
    t0 = time.time()
    mgr.update_device_cache()
    dt = time.time() - t0
    out: dict[str, Any] = {
        "at": int(time.time()), "sdk": SDK_VERSION, "endpoint": sess["endpoint"],
        "update_device_cache_s": round(dt, 2),
        "homes": [{"id": h.id, "name": h.name} for h in mgr.user_homes],
        "devices": [device_dump(d) for d in mgr.device_map.values()],
    }
    print(f"update_device_cache: {dt:.2f}s, homes={len(out['homes'])}, devices={len(out['devices'])}")
    for h in out["homes"]:
        print(f"  home {h['id']}  {h['name']}")
    for d in out["devices"]:
        flag = " <== METER" if d["id"] == METER_ID else ""
        print(f"  {d['id']}  online={d['online']!s:5}  cat={d['category']:6}  local={d['support_local']!s:5}  {d['name']}{flag}")

    meter = mgr.device_map.get(METER_ID)
    out["meter_found"] = meter is not None
    if meter:
        api = mgr.customer_api
        raw = {}
        for label, path in (
            ("specifications", f"/v1.1/m/life/{METER_ID}/specifications"),
            ("dp_status_relation", f"/v1.0/m/life/devices/{METER_ID}/status"),
            ("dp_report_types", f"/v1.0/m/life/ha/{METER_ID}/dp-report-types"),
            ("custom_type", f"/v1.0/m/life/ha/{METER_ID}/code/custom-type"),
            ("detail", f"/v1.0/m/life/ha/devices/detail"),
        ):
            try:
                params = {"devIds": METER_ID} if label == "detail" else None
                raw[label] = api.get(path, params)
            except Exception as exc:  # noqa: BLE001
                raw[label] = {"error": repr(exc)}
        out["meter_raw_api"] = raw
        out["meter"] = device_dump(meter)
        print("\n=== METER", METER_ID, "===")
        print(json.dumps(out["meter"], indent=2, default=str))
        print("\n--- raw dp_status_relation (dpId -> code, valueConvert, format) ---")
        print(json.dumps(raw["dp_status_relation"], indent=2, default=str)[:6000])
    path = STATE / f"enum_{int(time.time())}.json"
    _write_private(path, out)
    print("\nsaved", path)
    return 0 if meter else 5


# ---------------------------------------------- step 4: token refresh / reuse ---
def cmd_refresh(args: argparse.Namespace) -> int:
    tl = TokenPersist()
    mgr, sess = manager_from_session(tl)
    api = mgr.customer_api
    before = dict(vars(api.token_info))
    print("session reuse: authorized_at", sess["authorized_at"],
          "expire_time(ms)", before["expire_time"],
          "-> expires in", round((before["expire_time"] / 1000 - time.time()) / 3600, 2), "h")
    homes = mgr.home_repository.query_homes()
    print(f"reuse OK without rescanning: {len(homes)} home(s) via stored access_token")
    if args.force:
        # Simulate expiry to exercise the SDK's own refresh path (GET /v1.0/m/token/<refresh_token>)
        api.token_info.expire_time = 0
        t0 = time.time()
        api.refresh_access_token_if_need()
        dt = time.time() - t0
        after = dict(vars(api.token_info))
        changed = after["access_token"] != before["access_token"]
        print(f"forced refresh: {dt:.2f}s, access_token changed={changed}, "
              f"refresh_token changed={after['refresh_token'] != before['refresh_token']}, "
              f"new expiry in {round((after['expire_time'] / 1000 - time.time()) / 3600, 2)} h")
        homes2 = mgr.home_repository.query_homes()
        print(f"post-refresh call OK: {len(homes2)} home(s)")
        return 0 if changed else 6
    return 0


# ------------------------------------------------ step 5: MQTT live listener ---
class Recorder(SharingDeviceListener):
    def __init__(self, log_path: Path, only: str | None) -> None:
        self.only = only
        self.fh = open(log_path, "a")
        self.events = 0
        self.lat: list[float] = []

    def _w(self, obj: dict) -> None:
        obj["wall"] = time.time()
        self.fh.write(json.dumps(obj, default=str) + "\n")
        self.fh.flush()

    def update_device(self, device: CustomerDevice, updated_status_properties=None, dp_timestamps=None) -> None:
        if self.only and device.id != self.only:
            return
        now_ms = int(time.time() * 1000)
        lat = None
        if dp_timestamps:
            lat = min(now_ms - t for t in dp_timestamps.values()) / 1000
            self.lat.append(lat)
        self.events += 1
        changed = {c: device.status.get(c) for c in (updated_status_properties or [])}
        print(f"{time.strftime('%H:%M:%S')} UPDATE {device.name} online={device.online} "
              f"changed={changed} latency={lat if lat is None else round(lat, 3)}s")
        self._w({"kind": "update", "dev": device.id, "online": device.online,
                 "changed": changed, "dp_timestamps": dp_timestamps, "latency_s": lat,
                 "status": dict(device.status)})

    def add_device(self, device: CustomerDevice) -> None:
        self._w({"kind": "add", "dev": device.id})

    def remove_device(self, device_id: str) -> None:
        self._w({"kind": "remove", "dev": device_id})


def cmd_listen(args: argparse.Namespace) -> int:
    log_path = STATE / f"mqtt_{int(time.time())}.log"
    # SDK logs MQTT connect/subscribe/reconnect at DEBUG; capture to file
    sdk_log = logging.getLogger("tuya_sharing")
    sdk_log.setLevel(logging.DEBUG)
    fh = logging.FileHandler(STATE / f"sdk_{int(time.time())}.log")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    sdk_log.addHandler(fh)

    mgr, sess = manager_from_session()
    mgr.update_device_cache()
    only = None if args.all else METER_ID
    # HA entity.py sets `device.set_up = True` when an entity is created; Manager.refresh_mq
    # only subscribes device topics for set_up devices. Mirror that for the devices we watch.
    for d in mgr.device_map.values():
        if args.all or d.id == METER_ID:
            d.set_up = True
    rec = Recorder(log_path, only)
    mgr.add_device_listener(rec)
    raw_count = {"n": 0}

    def raw_listener(msg: dict) -> None:
        raw_count["n"] += 1
        rec._w({"kind": "raw", "msg": msg})

    t0 = time.time()
    mgr.refresh_mq()
    # wait for connection
    for _ in range(100):
        if mgr.mq and mgr.mq.client and mgr.mq.client.is_connected():
            break
        time.sleep(0.1)
    conn_t = time.time() - t0
    mgr.mq.add_message_listener(raw_listener)
    cfg = mgr.mq.mq_config
    print(f"MQTT connected in {conn_t:.2f}s url={cfg.url} client_id={cfg.client_id} "
          f"cred_expire_s={cfg.expire_time}")
    print(f"owner topic tmpl={cfg.owner_topic}  dev topic tmpl={cfg.dev_topic}")
    subs = [d for d in mgr.device_map.values() if getattr(d, 'set_up', False)]
    print(f"subscribed devices (set_up=True): {len(subs)}/{len(mgr.device_map)}; "
          f"meter subscribed={any(d.id == METER_ID for d in subs)} "
          f"meter topic suffix={'/pen' if mgr.device_map[METER_ID].support_local else '/sta'}")
    rec._w({"kind": "connect", "conn_s": conn_t, "url": cfg.url, "expire_s": cfg.expire_time})
    print(f"listening {args.seconds}s (read-only) -> {log_path}")
    end = time.time() + args.seconds
    last = time.time()
    drop_at = time.time() + args.drop_after if args.drop_after else None
    while time.time() < end:
        time.sleep(1)
        if drop_at and time.time() >= drop_at:
            # Simulate a broker-side drop: force the paho socket closed and let the SDK's
            # own _on_disconnect -> _wakeup -> fresh /access/config reconnect path run.
            drop_at = None
            old_cid = mgr.mq.mq_config.client_id
            print(f"{time.strftime('%H:%M:%S')} SIMULATING DROP (closing socket of {old_cid})")
            t_drop = time.time()
            try:
                mgr.mq.client.socket().close()
            except Exception as exc:  # noqa: BLE001
                print("drop failed:", exc)
            for _ in range(600):
                time.sleep(0.1)
                c = mgr.mq.client
                if c and c.is_connected() and mgr.mq.mq_config.client_id != old_cid:
                    break
            print(f"{time.strftime('%H:%M:%S')} RECONNECTED in {time.time() - t_drop:.2f}s "
                  f"new client_id={mgr.mq.mq_config.client_id} (changed={mgr.mq.mq_config.client_id != old_cid})")
            rec._w({"kind": "reconnect", "seconds": time.time() - t_drop,
                    "old": old_cid, "new": mgr.mq.mq_config.client_id})
        if time.time() - last >= 30:
            last = time.time()
            c = mgr.mq.client
            print(f"{time.strftime('%H:%M:%S')} alive connected={bool(c and c.is_connected())} "
                  f"raw_msgs={raw_count['n']} meter_updates={rec.events}")
    mgr.mq.stop()
    lat = sorted(rec.lat)
    summary = {
        "seconds": args.seconds, "raw_msgs": raw_count["n"], "meter_updates": rec.events,
        "latency_min": lat[0] if lat else None,
        "latency_median": lat[len(lat) // 2] if lat else None,
        "latency_max": lat[-1] if lat else None,
    }
    rec._w({"kind": "summary", **summary})
    print("SUMMARY", json.dumps(summary))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s = sub.add_parser("qr")
    s.add_argument("user_code", nargs="?", default=os.environ.get("CBI_USER_CODE", ""))
    s = sub.add_parser("poll"); s.add_argument("--timeout", type=int, default=240); s.add_argument("--interval", type=float, default=3)
    sub.add_parser("enum")
    s = sub.add_parser("refresh"); s.add_argument("--force", action="store_true")
    s = sub.add_parser("listen"); s.add_argument("--seconds", type=int, default=300); s.add_argument("--all", action="store_true"); s.add_argument("--drop-after", type=int, default=0)
    args = p.parse_args()
    print(f"# tuya-device-sharing-sdk {SDK_VERSION}  client_id={TUYA_CLIENT_ID} schema={TUYA_SCHEMA}")
    return {"status": cmd_status, "qr": cmd_qr, "poll": cmd_poll, "enum": cmd_enum, "refresh": cmd_refresh, "listen": cmd_listen}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
