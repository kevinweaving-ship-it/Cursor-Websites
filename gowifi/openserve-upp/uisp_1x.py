#!/usr/bin/env python3
"""UISP console + the 192.168.1.x IPs it serves.

Live source is GET /dash/api/devices?withInterfaces=true (UISP NMS proxy).
Rates are interface rxrate/txrate in bits/s — not destination websites.
UniFi (0.x / Site Manager) is a different product. Do not use it here.
"""
from __future__ import annotations

from typing import Any


CONSOLE_LAN = "192.168.1.1"
CONSOLE_LAN_CIDR = "192.168.1.1/24"
LAN_PREFIX = "192.168.1."
NC12_PREFIX = "192.168.12."
NC12_LAN = "192.168.12.0/24"
NC12_UDM = "192.168.12.56"
NC12_TP = "192.168.12.200"
NC12_INVENTORY = [
    {"ip": "192.168.12.2", "hardware": "MikroTik", "name": "", "note": "model unknown"},
    {"ip": "192.168.12.13", "hardware": "Ubiquiti NanoBeam 5AC", "name": ""},
    {"ip": "192.168.12.39", "hardware": "Ubiquiti LiteBeam 5AC", "name": ""},
    {"ip": "192.168.12.41", "hardware": "Cambium", "name": "Phillipa_MP", "note": "model unknown"},
    {"ip": "192.168.12.56", "hardware": "UniFi Dream Machine Pro", "name": "1 Dream Machine Pro Hermanus", "role": "udm"},
    {"ip": "192.168.12.66", "hardware": "Cambium", "name": "Phillipa_MP", "note": "model unknown"},
    {"ip": "192.168.12.68", "hardware": "", "name": "", "note": "web timeout"},
    {"ip": "192.168.12.101", "hardware": "Cambium", "name": "Mntp - Firestation", "note": "model unknown"},
    {"ip": "192.168.12.102", "hardware": "Cambium", "name": "Firestation-mntp", "note": "model unknown"},
    {"ip": "192.168.12.103", "hardware": "Cambium", "name": "Firestation_Lookout", "note": "model unknown"},
    {"ip": "192.168.12.104", "hardware": "Cambium", "name": "Lookout to Firestation", "note": "model unknown"},
    {"ip": "192.168.12.105", "hardware": "Ubiquiti GigaBeam LR", "name": "GigaBeam Walter Huis"},
    {"ip": "192.168.12.106", "hardware": "Ubiquiti GigaBeam LR", "name": "GigaBeam Lookout"},
    {"ip": "192.168.12.200", "hardware": "TP-Link", "name": "", "note": "router · model unknown", "role": "router"},
]


def devices_list(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [d for d in payload if isinstance(d, dict)]
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    if isinstance(data, dict):
        for key in ("items", "devices"):
            rows = data.get(key)
            if isinstance(rows, list):
                return [d for d in rows if isinstance(d, dict)]
    for key in ("items", "devices"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return [d for d in rows if isinstance(d, dict)]
    return []


def _ident(device: dict) -> dict:
    row = device.get("identification")
    return row if isinstance(row, dict) else {}


def _ov(device: dict) -> dict:
    row = device.get("overview")
    return row if isinstance(row, dict) else {}


def _plain_ip(cidr: Any) -> str:
    return str(cidr or "").split("/", 1)[0].strip()


def primary_ip(device: dict) -> str:
    return _plain_ip(device.get("ipAddress"))


def is_1x(ip: str) -> bool:
    return bool(ip) and ip.startswith(LAN_PREFIX)


def is_12x(ip: str) -> bool:
    return bool(ip) and ip.startswith(NC12_PREFIX)


def nc12_view() -> dict:
    return {
        "name": "NC Lightstruck Fibre",
        "isp": "RSA Web",
        "speed": "1 Gigabit",
        "role": "backup",
        "wan": "WAN3",
        "udm_ip": NC12_UDM,
        "router_ip": NC12_TP,
        "lan": NC12_LAN,
    }


def is_console(device: dict) -> bool:
    iden = _ident(device)
    name = str(iden.get("name") or "").lower()
    if "uisp-console" in name or name.endswith("uisp console"):
        return True
    return str(iden.get("role") or "") == "gateway" and str(iden.get("type") or "") == "uispr"


def iface_rates(iface: dict) -> tuple[float, float]:
    stats = iface.get("statistics") if isinstance(iface, dict) else None
    if not isinstance(stats, dict):
        return 0.0, 0.0
    try:
        rx = float(stats.get("rxrate") or 0)
    except (TypeError, ValueError):
        rx = 0.0
    try:
        tx = float(stats.get("txrate") or 0)
    except (TypeError, ValueError):
        tx = 0.0
    return rx, tx


def max_rates(device: dict) -> tuple[float, float]:
    rx = tx = 0.0
    for iface in device.get("interfaces") or []:
        if not isinstance(iface, dict):
            continue
        r, t = iface_rates(iface)
        if r > rx:
            rx = r
        if t > tx:
            tx = t
    return rx, tx


def _iface_name(iface: dict) -> str:
    idn = iface.get("identification") if isinstance(iface, dict) else None
    if isinstance(idn, dict):
        return str(idn.get("name") or "")
    return ""


def _iface_view(iface: dict | None) -> dict | None:
    if not isinstance(iface, dict):
        return None
    idn = iface.get("identification") if isinstance(iface.get("identification"), dict) else {}
    status = iface.get("status") if isinstance(iface.get("status"), dict) else {}
    addrs = []
    for addr in iface.get("addresses") or []:
        if isinstance(addr, dict) and addr.get("cidr"):
            addrs.append(str(addr["cidr"]))
    rx, tx = iface_rates(iface)
    return {
        "name": str(idn.get("name") or ""),
        "display": str(idn.get("displayName") or idn.get("name") or ""),
        "rx": rx,
        "tx": tx,
        "addrs": addrs,
        "plugged": status.get("plugged"),
        "speed": status.get("currentSpeed"),
    }


def _find_iface(device: dict, name: str) -> dict | None:
    for iface in device.get("interfaces") or []:
        if isinstance(iface, dict) and _iface_name(iface) == name:
            return iface
    return None


def _lan_addr(device: dict) -> str:
    br0 = _find_iface(device, "br0")
    if not br0:
        return ""
    for addr in br0.get("addresses") or []:
        if not isinstance(addr, dict):
            continue
        cidr = str(addr.get("cidr") or "")
        ip = _plain_ip(cidr)
        if is_1x(ip):
            return cidr
    return ""


def console_view(device: dict) -> dict:
    iden = _ident(device)
    ov = _ov(device)
    lan = _lan_addr(device) or CONSOLE_LAN_CIDR
    return {
        "id": iden.get("id"),
        "name": iden.get("name") or "UISP Console",
        "role": iden.get("role") or "gateway",
        "model": iden.get("modelName") or iden.get("model") or "UISP Console",
        "mgmt_ip": primary_ip(device),
        "lan": lan,
        "lan_ip": _plain_ip(lan) or CONSOLE_LAN,
        "status": ov.get("status") or iden.get("status"),
        "cpu": ov.get("cpu"),
        "ram": ov.get("ram"),
        "uptime": ov.get("uptime"),
        "br0": _iface_view(_find_iface(device, "br0")),
        "uplink": _iface_view(_find_iface(device, "9")),
        "lan_port": _iface_view(_find_iface(device, "8")),
        "switch": _iface_view(_find_iface(device, "switch0")),
    }


def served_row(device: dict) -> dict:
    iden = _ident(device)
    site = iden.get("site") if isinstance(iden.get("site"), dict) else {}
    rx, tx = max_rates(device)
    return {
        "ip": primary_ip(device),
        "name": iden.get("name") or "",
        "role": iden.get("role") or "",
        "model": iden.get("modelName") or iden.get("model") or "",
        "status": _ov(device).get("status") or iden.get("status") or "",
        "site": site.get("name") or "",
        "rx": rx,
        "tx": tx,
    }


def _ip_sort(ip: str) -> tuple:
    parts = []
    for bit in str(ip or "").split("."):
        try:
            parts.append(int(bit))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def merge_12x(devices: list[dict]) -> list[dict]:
    live = {
        primary_ip(d): served_row(d)
        for d in devices
        if is_12x(primary_ip(d))
    }
    rows: list[dict] = []
    seen: set[str] = set()
    for inv in NC12_INVENTORY:
        ip = inv["ip"]
        seen.add(ip)
        live_row = live.get(ip)
        rows.append(
            {
                "ip": ip,
                "name": (live_row or {}).get("name") or inv.get("name") or "",
                "hardware": (live_row or {}).get("model") or inv.get("hardware") or "",
                "role": (live_row or {}).get("role") or inv.get("role") or "",
                "status": (live_row or {}).get("status") or "",
                "site": (live_row or {}).get("site") or "",
                "rx": live_row["rx"] if live_row else None,
                "tx": live_row["tx"] if live_row else None,
                "live": bool(live_row),
                "note": inv.get("note") or "",
            }
        )
    for ip, live_row in live.items():
        if ip in seen:
            continue
        rows.append(
            {
                "ip": ip,
                "name": live_row.get("name") or "",
                "hardware": live_row.get("model") or "",
                "role": live_row.get("role") or "",
                "status": live_row.get("status") or "",
                "site": live_row.get("site") or "",
                "rx": live_row.get("rx"),
                "tx": live_row.get("tx"),
                "live": True,
                "note": "",
            }
        )
    rows.sort(key=lambda r: (-(float(r["rx"] or 0) + float(r["tx"] or 0)), _ip_sort(r["ip"])))
    return rows


def build(payload: Any) -> dict:
    devices = devices_list(payload)
    console = next((d for d in devices if is_console(d)), None)
    rows = [
        served_row(d)
        for d in devices
        if not is_console(d) and is_1x(primary_ip(d))
    ]
    rows.sort(key=lambda r: (-(r["rx"] + r["tx"]), r["ip"]))
    served_12x = merge_12x(devices)
    return {
        "console": console_view(console) if console else None,
        "served": rows,
        "count": len(rows),
        "nc12": nc12_view(),
        "served_12x": served_12x,
        "count_12x": len(served_12x),
    }


def self_test() -> int:
    failed = 0
    console = {
        "ipAddress": "192.168.0.147/24",
        "identification": {
            "id": "776557ef-cbab-480d-9bee-8e6de7b4ffb6",
            "name": "VK UISP-Console",
            "role": "gateway",
            "type": "uispr",
            "modelName": "UISP Console",
        },
        "overview": {"status": "active", "cpu": 26, "ram": 76},
        "interfaces": [
            {
                "identification": {"name": "br0", "displayName": "Bridge"},
                "addresses": [{"cidr": "192.168.1.1/24"}],
                "status": {"plugged": True},
                "statistics": {"rxrate": 52144, "txrate": 40824},
            },
            {
                "identification": {"name": "9", "displayName": "9"},
                "addresses": [{"cidr": "192.168.0.147/24"}],
                "status": {"plugged": True, "currentSpeed": "1000-full"},
                "statistics": {"rxrate": 56520, "txrate": 28464},
            },
            {
                "identification": {"name": "8", "displayName": "8"},
                "status": {"plugged": True, "currentSpeed": "1000-full"},
                "statistics": {"rxrate": 198440, "txrate": 6550328},
            },
            {
                "identification": {"name": "switch0", "displayName": "Switch"},
                "statistics": {"rxrate": 202080, "txrate": 6553808},
            },
        ],
    }
    bing = {
        "ipAddress": "192.168.1.41/24",
        "identification": {
            "name": "Bing",
            "role": "station",
            "modelName": "LiteBeam 5AC",
            "site": {"name": "Bing"},
        },
        "overview": {"status": "active"},
        "interfaces": [
            {"identification": {"name": "br0"}, "statistics": {"rxrate": 2848, "txrate": 2608}},
            {"identification": {"name": "eth0"}, "statistics": {"rxrate": 71168, "txrate": 3903192}},
            {"identification": {"name": "main"}, "statistics": {"rxrate": 3972536, "txrate": 121808}},
        ],
    }
    other = {
        "ipAddress": "192.168.12.105/24",
        "identification": {"name": "GigaBeam Walter Huis", "role": "station"},
        "overview": {"status": "active"},
        "interfaces": [
            {"identification": {"name": "main"}, "statistics": {"rxrate": 100, "txrate": 100}},
        ],
    }
    out = build([console, bing, other])
    if not out["console"] or out["console"]["mgmt_ip"] != "192.168.0.147":
        print("FAIL console-mgmt-not-0x")
        failed += 1
    elif out["console"]["lan_ip"] != "192.168.1.1":
        print("FAIL console-lan-not-1x")
        failed += 1
    elif (out["console"].get("uplink") or {}).get("addrs") != ["192.168.0.147/24"]:
        print("FAIL console-uplink-not-port9")
        failed += 1
    else:
        print("OK console-on-0x-serves-1x")
    if out["count"] != 1 or out["served"][0]["ip"] != "192.168.1.41":
        print("FAIL served-only-1x", out["count"], [r["ip"] for r in out["served"]])
        failed += 1
    elif out["served"][0]["rx"] != 3972536 or out["served"][0]["tx"] != 3903192:
        print("FAIL served-max-iface-rates", out["served"][0])
        failed += 1
    else:
        print("OK served-1x-max-rates")
    if is_console(other) or is_1x(primary_ip(other)):
        print("FAIL 12x-treated-as-console-or-1x")
        failed += 1
    else:
        print("OK skip-non-1x")
    if out["nc12"]["role"] != "backup" or out["nc12"]["udm_ip"] != NC12_UDM:
        print("FAIL nc12-backup-udm", out["nc12"])
        failed += 1
    elif out["nc12"]["router_ip"] != NC12_TP:
        print("FAIL nc12-tp-router")
        failed += 1
    else:
        print("OK nc12-backup-wan3")
    ips12 = [r["ip"] for r in out["served_12x"]]
    walter = next((r for r in out["served_12x"] if r["ip"] == "192.168.12.105"), None)
    udm = next((r for r in out["served_12x"] if r["ip"] == NC12_UDM), None)
    if "192.168.12.105" not in ips12 or not walter or walter["rx"] != 100:
        print("FAIL 12x-live-merge", walter)
        failed += 1
    elif not udm or udm["live"] or udm["name"] != "1 Dream Machine Pro Hermanus":
        print("FAIL 12x-udm-inventory", udm)
        failed += 1
    elif out["count_12x"] < len(NC12_INVENTORY):
        print("FAIL 12x-inventory-short", out["count_12x"])
        failed += 1
    else:
        print("OK 12x-inventory-plus-live")
    return failed


if __name__ == "__main__":
    raise SystemExit(self_test())
