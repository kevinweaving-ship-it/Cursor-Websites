#!/usr/bin/env python3
"""Add Hansekop Avg/pd (this month kWh ÷ SAST calendar days so far) after since restore.

Live paths: /var/www/sailingsa/api/arial_api.py, /var/www/sailingsa/arial/{index.html,app.js}
Does not overwrite live api.py. Restart arial-api after applying.
"""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/arial_api.py")
HTML = Path("/var/www/sailingsa/arial/index.html")
JS = Path("/var/www/sailingsa/arial/app.js")

MONTH_FN = '''
_month_pd_cache: dict[str, Any] = {"at": 0.0, "device": "", "data": None}


def _month_avg_pd_from_bins(device: str) -> dict[str, Any] | None:
    """Calendar-month kWh from on-disk hourly bins (not the 7-day in-memory window) ÷ SAST day-of-month."""
    now = time.time()
    cached = _month_pd_cache
    if (
        cached.get("device") == device
        and now - float(cached.get("at") or 0) < 30
        and isinstance(cached.get("data"), dict)
    ):
        return cached["data"]
    local = datetime.fromtimestamp(now, tz=timezone.utc).astimezone(_SAST)
    prefix = local.strftime("%Y%m")
    hours: dict[str, float] = {}
    try:
        path = _energy_store_path()
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
            disk = (raw.get("bins") or {}) if isinstance(raw, dict) else {}
            mine = disk.get(device) if isinstance(disk, dict) else None
            if isinstance(mine, dict):
                for k, v in mine.items():
                    if str(k).startswith(prefix) and isinstance(v, (int, float)):
                        hours[str(k)] = float(v)
    except (OSError, ValueError, TypeError):
        pass
    try:
        with _energy_lock:
            mine = _energy_bins.get(device) or {}
            for k, v in mine.items():
                if str(k).startswith(prefix) and isinstance(v, (int, float)):
                    hours[str(k)] = max(hours.get(str(k), 0.0), float(v))
    except Exception:
        pass
    if not hours:
        _month_pd_cache.update({"at": now, "device": device, "data": None})
        return None
    month_kwh = sum(hours.values())
    days = max(1, int(local.day))
    data = {
        "month_kwh": round(month_kwh, 3),
        "month_days": days,
        "month_avg_pd_kwh": round(month_kwh / days, 3),
        "month_label": f"{_MONTHS[local.month - 1]} so far: {month_kwh:.0f} kWh / {days} days",
    }
    _month_pd_cache.update({"at": now, "device": device, "data": data})
    return data

'''

OLD_STORE = '''def _energy_store_path() -> Path:
    for path in _energy_log_candidates():
        if path.is_file():
            return path
    return _energy_log_candidates()[0]


def _energy_merge_disk(data: Any) -> None:
'''

NEW_STORE = '''def _energy_store_path() -> Path:
    for path in _energy_log_candidates():
        if path.is_file():
            return path
    return _energy_log_candidates()[0]
''' + MONTH_FN + '''
def _energy_merge_disk(data: Any) -> None:
'''

OLD_ROWS_TAIL = '''        offset = refs.get("eskomOffsetKwh")
        if isinstance(offset, (int, float)):
            rows.append({"code": "eskom_kwh", "value": round(lifetime + float(offset), 1)})
    return rows
'''

NEW_ROWS_TAIL = '''        offset = refs.get("eskomOffsetKwh")
        if isinstance(offset, (int, float)):
            rows.append({"code": "eskom_kwh", "value": round(lifetime + float(offset), 1)})
    stats = _month_avg_pd_from_bins(TUYA_MAINS_METER_ID)
    if stats:
        rows.append({"code": "month_kwh", "value": stats["month_kwh"]})
        rows.append({"code": "month_days", "value": stats["month_days"]})
        rows.append({"code": "month_avg_pd_kwh", "value": stats["month_avg_pd_kwh"]})
        rows.append({"code": "month_label", "value": stats["month_label"]})
    return rows
'''

OLD_HTML = '''                    <span class="breaker-meter" id="breaker-restore" title="kWh since mains power was restored" hidden>—</span>
'''

NEW_HTML = '''                    <span class="breaker-meter" id="breaker-restore" title="kWh since mains power was restored" hidden>—</span>
                    <span class="breaker-meter" id="breaker-avg-pd" title="This month: kWh ÷ calendar days so far (SAST)" hidden>—</span>
'''

OLD_SEG = '''    function setBreakerMeterSeg(id, label, kwh, suffix) {
        var el = document.getElementById(id);
        if (!el) return;
        if (kwh == null || !isFinite(kwh)) { el.hidden = true; return; }
        var txt = kwh >= 1000 ? kwh.toFixed(1) : (kwh >= 100 ? kwh.toFixed(2) : kwh.toFixed(3));
        el.textContent = "";
        if (label) { var l = document.createElement("i"); l.textContent = label + " "; el.appendChild(l); }
        el.appendChild(document.createTextNode(txt + (suffix || " kWh")));
        el.hidden = false;
    }
'''

NEW_SEG = '''    function setBreakerMeterSeg(id, label, kwh, suffix, digits) {
        var el = document.getElementById(id);
        if (!el) return;
        if (kwh == null || !isFinite(kwh)) { el.hidden = true; return; }
        var txt = typeof digits === "number"
            ? kwh.toFixed(digits)
            : (kwh >= 1000 ? kwh.toFixed(1) : (kwh >= 100 ? kwh.toFixed(2) : kwh.toFixed(3)));
        el.textContent = "";
        if (label) { var l = document.createElement("i"); l.textContent = label + " "; el.appendChild(l); }
        el.appendChild(document.createTextNode(txt + (suffix || " kWh")));
        el.hidden = false;
    }
'''

OLD_RENDER = '''        setBreakerMeterSeg("breaker-eskom", "Eskom", b.eskom != null ? b.eskom + add : null);
        setBreakerMeterSeg("breaker-meter", "Meter", b.life != null ? b.life + add : null);
        setBreakerMeterSeg("breaker-restore", "", b.since != null ? b.since + add : null, " since restore");
'''

NEW_RENDER = '''        setBreakerMeterSeg("breaker-eskom", "Eskom", b.eskom != null ? b.eskom + add : null);
        setBreakerMeterSeg("breaker-meter", "Meter", b.life != null ? b.life + add : null);
        setBreakerMeterSeg("breaker-restore", "", b.since != null ? b.since + add : null, " since restore");
        var avgPd = (b.monthKwh != null && b.monthDays > 0) ? (b.monthKwh + add) / b.monthDays : null;
        setBreakerMeterSeg("breaker-avg-pd", "Avg/pd", avgPd, " kWh", 1);
        var avgEl = document.getElementById("breaker-avg-pd");
        if (avgEl && b.monthLabel) avgEl.title = b.monthLabel;
'''

OLD_SET = '''        var life = typeof map.meter_kwh === "number" ? map.meter_kwh : null;
        var since = typeof map.meter_since_restore_kwh === "number" ? map.meter_since_restore_kwh : null;
        var eskom = typeof map.eskom_kwh === "number" ? map.eskom_kwh : null;
        var b = breakerMeterBase;
        if (!b || b.life !== life || b.since !== since || b.eskom !== eskom) {
            breakerMeterBase = { life: life, since: since, eskom: eskom, at: Date.now() };
        }
'''

NEW_SET = '''        var life = typeof map.meter_kwh === "number" ? map.meter_kwh : null;
        var since = typeof map.meter_since_restore_kwh === "number" ? map.meter_since_restore_kwh : null;
        var eskom = typeof map.eskom_kwh === "number" ? map.eskom_kwh : null;
        var monthKwh = typeof map.month_kwh === "number" ? map.month_kwh : null;
        var monthDays = typeof map.month_days === "number" ? map.month_days : 0;
        var monthLabel = typeof map.month_label === "string" ? map.month_label : "";
        var b = breakerMeterBase;
        if (!b || b.life !== life || b.since !== since || b.eskom !== eskom || b.monthKwh !== monthKwh || b.monthDays !== monthDays) {
            breakerMeterBase = { life: life, since: since, eskom: eskom, monthKwh: monthKwh, monthDays: monthDays, monthLabel: monthLabel, at: Date.now() };
        }
'''


def _patch(path: Path, old: str, new: str, already: str) -> str:
    text = path.read_text(encoding="utf-8")
    if already in text and old not in text:
        return "already"
    if old not in text:
        raise SystemExit(f"block not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return "patched"


def main() -> None:
    for p in (API, HTML, JS):
        if not p.is_file():
            raise SystemExit(f"missing {p}")
        bak = p.with_name(p.name + ".bak-avg-pd")
        if not bak.exists():
            bak.write_bytes(p.read_bytes())

    print("api-fn", _patch(API, OLD_STORE, NEW_STORE, "def _month_avg_pd_from_bins"))
    print("api", _patch(API, OLD_ROWS_TAIL, NEW_ROWS_TAIL, "month_avg_pd_kwh"))
    print("html", _patch(HTML, OLD_HTML, NEW_HTML, 'id="breaker-avg-pd"'))
    print("js-seg", _patch(JS, OLD_SEG, NEW_SEG, "function setBreakerMeterSeg(id, label, kwh, suffix, digits)"))
    print("js-render", _patch(JS, OLD_RENDER, NEW_RENDER, 'setBreakerMeterSeg("breaker-avg-pd"'))
    print("js-set", _patch(JS, OLD_SET, NEW_SET, "var monthKwh = typeof map.month_kwh"))


if __name__ == "__main__":
    main()
