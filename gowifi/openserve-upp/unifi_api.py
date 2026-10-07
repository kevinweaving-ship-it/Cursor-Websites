#!/usr/bin/env python3
"""Read-only UniFi Site Manager summary for /dash/unifi.html.

Key stays in /root/secrets/unifi.env. Browser never sees it. No cron.
Does not invent status — connected/disconnected comes from /v1/hosts.
"""
from __future__ import annotations

import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ENV_PATH = Path(os.environ.get("UNIFI_ENV", "/root/secrets/unifi.env"))
LISTEN = os.environ.get("UNIFI_API_LISTEN", "127.0.0.1:8801")
BASE = "https://api.ui.com"


def _load_env(path: Path = ENV_PATH) -> dict[str, str]:
    data: dict[str, str] = {}
    if path.exists():
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            data[key.strip()] = val.strip().strip("'").strip('"')
    return data


def _host_key(host_id: str) -> str:
    return (host_id or "").split(":", 1)[0]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def _get(path: str, key: str) -> dict:
    req = urllib.request.Request(
        BASE + path,
        headers={"X-API-KEY": key, "Accept": "application/json"},
    )
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        return json.loads(resp.read().decode())


def _apps(rs: dict) -> list[str]:
    out = []
    for c in rs.get("controllers") or []:
        if not isinstance(c, dict):
            continue
        if c.get("isInstalled") and c.get("isRunning"):
            name = str(c.get("name") or "").strip()
            if name:
                out.append(name)
    return out


def _match_site(host: dict, sites: list[dict]) -> dict:
    hid = _host_key(host.get("id") or "")
    hits = [s for s in sites if _host_key(s.get("hostId") or "") == hid]
    if not hits:
        return {}
    hits.sort(key=lambda s: ((s.get("statistics") or {}).get("counts") or {}).get("totalDevice") or 0)
    return hits[-1]


def _match_devices(name: str, state: str, groups: list[dict]) -> dict:
    want = (name or "").strip().lower()
    hits = [g for g in groups if (g.get("hostName") or "").strip().lower() == want]
    if not hits:
        return {"devices": 0, "online": 0, "offline": 0}
    expect = "online" if state == "connected" else "offline" if state == "disconnected" else ""

    def score(g: dict) -> tuple:
        devices = g.get("devices") or []
        consoles = [d for d in devices if d.get("isConsole")]
        cstate = (consoles[0].get("status") if consoles else "") or ""
        return (1 if expect and cstate == expect else 0, len(devices))

    hits.sort(key=score)
    g = hits[-1]
    devices = g.get("devices") or []
    return {
        "devices": len(devices),
        "online": sum(1 for d in devices if (d.get("status") or "") == "online"),
        "offline": sum(1 for d in devices if (d.get("status") or "") == "offline"),
        "rows": [
            {
                "name": (d.get("name") or "").strip(),
                "model": (d.get("model") or "").strip(),
                "status": (d.get("status") or "").strip(),
                "version": (d.get("version") or "").strip(),
                "ip": (d.get("ip") or "").strip(),
                "is_console": bool(d.get("isConsole")),
            }
            for d in devices
        ],
    }


def _wans(site: dict) -> list[dict]:
    st = site.get("statistics") or {}
    raw = st.get("wans") or {}
    if not isinstance(raw, dict):
        return []
    rows = []
    for name, wan in raw.items():
        if not isinstance(wan, dict):
            continue
        isp = wan.get("ispInfo") if isinstance(wan.get("ispInfo"), dict) else {}
        rows.append(
            {
                "name": name,
                "isp": (isp.get("name") or "").strip(),
                "uptime": wan.get("wanUptime"),
                "port_up": wan.get("portUp"),
                "external_ip": (wan.get("externalIp") or "").strip(),
            }
        )
    return rows


def _card(host: dict, sites: list[dict], groups: list[dict]) -> dict:
    rs = host.get("reportedState") or {}
    hw = rs.get("hardware") if isinstance(rs.get("hardware"), dict) else {}
    name = (rs.get("name") or "").strip()
    state = (rs.get("state") or "").strip()
    site = _match_site(host, sites)
    st = site.get("statistics") or {}
    counts = st.get("counts") or {}
    isp = (st.get("ispInfo") or {}).get("name") or ""
    wan_uptime = (st.get("percentages") or {}).get("wanUptime")
    return {
        "id": host.get("id") or "",
        "slug": _slug(name),
        "name": name,
        "state": state,
        "device_state": (rs.get("deviceState") or "").strip(),
        "hardware": (hw.get("name") or "").strip(),
        "shortname": (hw.get("shortname") or "").strip(),
        "firmware": (hw.get("firmwareVersion") or rs.get("version") or "").strip(),
        "timezone": (rs.get("timezone") or "").strip(),
        "apps": _apps(rs),
        "isp": isp,
        "wan_uptime": wan_uptime,
        "wifi_clients": counts.get("wifiClient"),
        "wired_clients": counts.get("wiredClient"),
        "devices": _match_devices(name, state, groups),
        "wans": _wans(site),
    }


def _find_host(want: str, hosts: list[dict]) -> dict:
    want = (want or "").strip()
    if not want:
        return {}
    slug = _slug(want)
    for host in hosts:
        rs = host.get("reportedState") or {}
        name = (rs.get("name") or "").strip()
        hid = host.get("id") or ""
        if want == hid or want == _host_key(hid) or slug == _slug(name) or want.casefold() == name.casefold():
            return host
    return {}


def _connector(key: str, host_id: str) -> dict:
    """Optional local Network API via cloud connector. Omit if the console cannot answer."""
    if not host_id:
        return {"ok": False, "error": "no host id"}
    path = f"/v1/connector/consoles/{urllib.parse.quote(host_id, safe='')}/proxy/network/integration/v1/info"
    try:
        info = _get(path, key)
    except urllib.error.HTTPError as exc:
        return {"ok": False, "error": f"connector HTTP {exc.code}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}
    data = info.get("data") if isinstance(info.get("data"), dict) else info
    return {
        "ok": True,
        "application_version": data.get("applicationVersion") if isinstance(data, dict) else None,
    }


def _parse_cap(name: str) -> tuple[int | None, int | None]:
    match = re.search(r"(\d+)\s*/\s*(\d+)\s*Mbps", name or "", re.I)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def _bps_from_bytes_r(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value) * 8.0
    except (TypeError, ValueError):
        return None


def _mbps(bps: float | None) -> float | None:
    if bps is None:
        return None
    return round(bps / 1_000_000.0, 2)


def _pct(used_mbps: float | None, cap_mbps: int | None) -> float | None:
    if used_mbps is None or not cap_mbps:
        return None
    return round(min(100.0, max(0.0, used_mbps / cap_mbps * 100.0)), 1)


def _classic(key: str, host_id: str, tail: str) -> dict:
    path = f"/v1/connector/consoles/{urllib.parse.quote(host_id, safe='')}/proxy/network{tail}"
    return _get(path, key)


def _iface_rates(block: dict) -> dict:
    down = _bps_from_bytes_r(block.get("rx_bytes-r"))
    up = _bps_from_bytes_r(block.get("tx_bytes-r"))
    if down is None and block.get("rx_rate") is not None:
        try:
            down = float(block.get("rx_rate"))
        except (TypeError, ValueError):
            down = None
    if up is None and block.get("tx_rate") is not None:
        try:
            up = float(block.get("tx_rate"))
        except (TypeError, ValueError):
            up = None
    return {"down_bps": down, "up_bps": up, "down_mbps": _mbps(down), "up_mbps": _mbps(up)}


def _wan_gauges(key: str, host_id: str) -> list[dict]:
    """Two fibres + LTE from this console. Names and rates from UniFi only."""
    if not host_id:
        return []
    names: dict[str, str] = {}
    try:
        info = _classic(key, host_id, "/integration/v1/sites")
        site_id = ((info.get("data") or [{}])[0] or {}).get("id")
        if site_id:
            wans = _classic(key, host_id, f"/integration/v1/sites/{site_id}/wans")
            for row in wans.get("data") or []:
                label = (row.get("name") or "").strip()
                low = label.lower()
                if "lte" in low:
                    names["lte"] = label
                elif label.startswith("1>") or "web connect" in low or "500/250" in low:
                    names["wan"] = label
                elif label.startswith("2>") or "office connect" in low or "300/150" in low:
                    names["wan2"] = label
    except Exception:
        names = {}
    names.setdefault("wan", "WAN")
    names.setdefault("wan2", "WAN2")
    names.setdefault("lte", "LTE Failover WAN")

    gw = {}
    health_wan = {}
    try:
        devices = _classic(key, host_id, "/api/s/default/stat/device")
        for dev in devices.get("data") or []:
            if (dev.get("type") or "") in {"udm", "ugw"} or "Dream Machine" in (dev.get("name") or ""):
                gw = dev
                break
    except Exception:
        gw = {}
    try:
        health = _classic(key, host_id, "/api/s/default/stat/health")
        health_wan = next((r for r in (health.get("data") or []) if r.get("subsystem") == "wan"), {}) or {}
    except Exception:
        health_wan = {}

    status_map = gw.get("last_wan_status") if isinstance(gw.get("last_wan_status"), dict) else {}
    uptime_stats = health_wan.get("uptime_stats") if isinstance(health_wan.get("uptime_stats"), dict) else {}
    specs = [
        ("wan", "WAN", "wan1", names["wan"], "fibre"),
        ("wan2", "WAN2", "wan2", names["wan2"], "fibre"),
        ("lte", "WAN_LTE_FAILOVER", "wan3", names["lte"], "lte"),
    ]
    gauges = []
    for key_id, status_key, block_key, label, kind in specs:
        block = gw.get(block_key) if isinstance(gw.get(block_key), dict) else {}
        rates = _iface_rates(block)
        cap_down, cap_up = _parse_cap(label)
        raw_status = (status_map.get(status_key) or "").strip()
        if not raw_status:
            raw_status = "online" if block.get("up") or block.get("alive") else ("offline" if block else "")
        stats = uptime_stats.get(status_key) if isinstance(uptime_stats.get(status_key), dict) else {}
        down_mbps = rates["down_mbps"]
        up_mbps = rates["up_mbps"]
        gauges.append(
            {
                "id": key_id,
                "kind": kind,
                "name": label,
                "status": raw_status,
                "capacity_down_mbps": cap_down,
                "capacity_up_mbps": cap_up,
                "used_down_mbps": down_mbps,
                "used_up_mbps": up_mbps,
                "used_down_pct": _pct(down_mbps, cap_down),
                "used_up_pct": _pct(up_mbps, cap_up),
                "latency_ms": block.get("latency") if block.get("latency") is not None else (stats.get("latency_average")),
                "availability": block.get("availability") if block.get("availability") is not None else stats.get("availability"),
                "ip": (block.get("ip") or "").strip(),
                "up": bool(block.get("up")) if block else raw_status == "online",
            }
        )
    return gauges


def summary() -> dict:
    env = _load_env()
    key = env.get("UNIFI_API_KEY") or ""
    if not key:
        return {"ok": False, "live": False, "error": "no UNIFI_API_KEY in /root/secrets/unifi.env", "hosts": []}
    try:
        hosts = _get("/v1/hosts", key).get("data") or []
        sites = _get("/v1/sites", key).get("data") or []
        groups = _get("/v1/devices", key).get("data") or []
    except urllib.error.HTTPError as exc:
        return {"ok": False, "live": False, "error": f"UniFi HTTP {exc.code}", "hosts": []}
    except Exception as exc:
        return {"ok": False, "live": False, "error": str(exc)[:200], "hosts": []}

    cards = [_card(host, sites, groups) for host in hosts]
    cards.sort(key=lambda c: c.get("name") or "")
    return {
        "ok": True,
        "live": True,
        "as_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hosts": cards,
        "online": sum(1 for c in cards if c.get("state") == "connected"),
        "offline": sum(1 for c in cards if c.get("state") == "disconnected"),
    }


def host_detail(want: str) -> dict:
    env = _load_env()
    key = env.get("UNIFI_API_KEY") or ""
    if not key:
        return {"ok": False, "live": False, "error": "no UNIFI_API_KEY in /root/secrets/unifi.env"}
    try:
        hosts = _get("/v1/hosts", key).get("data") or []
        sites = _get("/v1/sites", key).get("data") or []
        groups = _get("/v1/devices", key).get("data") or []
    except urllib.error.HTTPError as exc:
        return {"ok": False, "live": False, "error": f"UniFi HTTP {exc.code}"}
    except Exception as exc:
        return {"ok": False, "live": False, "error": str(exc)[:200]}
    host = _find_host(want, hosts)
    if not host:
        return {"ok": False, "live": True, "error": "host not found", "want": want}
    card = _card(host, sites, groups)
    connector = _connector(key, host.get("id") or "")
    gauges = []
    try:
        gauges = _wan_gauges(key, host.get("id") or "")
    except Exception as exc:
        gauges = []
        connector = {**(connector or {}), "gauges_error": str(exc)[:200]}
    card["gauges"] = gauges
    return {
        "ok": True,
        "live": True,
        "as_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "host": card,
        "connector": connector,
        "child": "/dash/unifi.html?h=" + urllib.parse.quote(card.get("slug") or card.get("id") or ""),
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("unifi-api: " + fmt % args + "\n")

    def _send(self, code: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query)
        want = (qs.get("h") or qs.get("host") or [""])[0]
        if path in {"/", "/summary", "/dash/api/unifi", "/host"}:
            pack = host_detail(want) if want else summary()
            self._send(200 if pack.get("ok") else 404 if pack.get("error") == "host not found" else 503, pack)
            return
        self._send(404, {"ok": False, "error": "not found"})


def serve() -> None:
    host, port = LISTEN.split(":")
    httpd = ThreadingHTTPServer((host, int(port)), Handler)
    print(f"unifi-api on {LISTEN}", flush=True)
    httpd.serve_forever()


def self_test() -> int:
    failed = 0
    empty = summary()
    if empty.get("live"):
        print("FAIL empty-env-live")
        failed += 1
    else:
        print("OK empty-env-not-live")
    host = {"id": "ABC:1"}
    sites = [
        {"hostId": "ABC:9", "statistics": {"counts": {"totalDevice": 2}, "ispInfo": {"name": "Telkom"}}},
        {"hostId": "ABC:2", "statistics": {"counts": {"totalDevice": 8}, "ispInfo": {"name": "Telkom Internet"}}},
    ]
    site = _match_site(host, sites)
    if (site.get("statistics") or {}).get("counts", {}).get("totalDevice") != 8:
        print("FAIL site-match")
        failed += 1
    else:
        print("OK site-match")
    if _slug("1 Dream Machine Pro Hermanus") != "1-dream-machine-pro-hermanus":
        print("FAIL slug")
        failed += 1
    else:
        print("OK slug")
    found = _find_host(
        "1-dream-machine-pro-hermanus",
        [{"id": "ABC:1", "reportedState": {"name": "1 Dream Machine Pro Hermanus"}}],
    )
    if not found:
        print("FAIL find-host")
        failed += 1
    else:
        print("OK find-host")
    if _parse_cap("1> Web Connect 500/250 Mbps") != (500, 250):
        print("FAIL parse-cap")
        failed += 1
    elif _parse_cap("LTE Failover WAN") != (None, None):
        print("FAIL parse-cap-lte")
        failed += 1
    elif _pct(13.2, 500) != 2.6:
        print("FAIL pct")
        failed += 1
    else:
        print("OK cap-pct")
    rates = _iface_rates({"rx_bytes-r": 1_650_000, "tx_bytes-r": 95_000})
    if rates["down_mbps"] != 13.2 or rates["up_mbps"] != 0.76:
        print("FAIL iface-rates")
        failed += 1
    else:
        print("OK iface-rates")
    return failed


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] == "self-test":
        return self_test()
    if args[0] == "summary":
        print(json.dumps(summary(), indent=2))
        return 0
    if args[0] == "host":
        print(json.dumps(host_detail(args[1] if len(args) > 1 else ""), indent=2))
        return 0
    if args[0] == "serve":
        serve()
        return 0
    print("usage: unifi_api.py self-test|summary|host <slug>|serve")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
