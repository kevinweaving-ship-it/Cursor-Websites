#!/usr/bin/env python3
"""Avg/pd from exact restore time/reading vs exact now time/reading."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/arial_api.py")
JS = Path("/var/www/sailingsa/arial/app.js")
HTML = Path("/var/www/sailingsa/arial/index.html")

OLD_FN = '''def _avg_pd_since_restore(lifetime: float, refs: dict[str, Any]) -> dict[str, Any] | None:
    """(register now - restore) / calendar days from first full day after restore to today.

    Restore 01 Sep 18:57 -> first full day 02 Sep. 02 Sep to 15 Sep = 13 days (not day-of-month 15).
    """
    restore_ts = refs.get("restoreAt")
    if not isinstance(restore_ts, (int, float)) or float(restore_ts) <= 0:
        return None
    anchor = refs.get("meterKwhAtRestore")
    if not isinstance(anchor, (int, float)):
        anchor = 0.0
    since = max(0.0, float(lifetime) - float(anchor))
    restore_local = datetime.fromtimestamp(float(restore_ts), tz=timezone.utc).astimezone(_SAST)
    start = restore_local.date()
    if restore_local.hour >= 6:
        start = start + timedelta(days=1)
    today = datetime.now(_SAST).date()
    days = (today - start).days
    if days < 1:
        days = 1
    return {
        "month_kwh": round(since, 3),
        "month_days": days,
        "month_avg_pd_kwh": round(since / days, 3),
        "month_label": f"Since restore: {since:.0f} kWh / {days} days ({start.day}-{today.day} {_MONTHS[today.month - 1]})",
    }
'''

NEW_FN = '''def _avg_pd_since_restore(lifetime: float, refs: dict[str, Any], now_ts: float | None = None) -> dict[str, Any] | None:
    """(register now - restore reading) / exact elapsed days between those two timestamps."""
    restore_ts = refs.get("restoreAt")
    if not isinstance(restore_ts, (int, float)) or float(restore_ts) <= 0:
        return None
    anchor = refs.get("meterKwhAtRestore")
    if not isinstance(anchor, (int, float)):
        anchor = 0.0
    since = max(0.0, float(lifetime) - float(anchor))
    t1 = float(now_ts if now_ts is not None else time.time())
    days = max(1.0 / 86_400.0, (t1 - float(restore_ts)) / 86_400.0)
    t0 = datetime.fromtimestamp(float(restore_ts), tz=timezone.utc).astimezone(_SAST)
    tnow = datetime.fromtimestamp(t1, tz=timezone.utc).astimezone(_SAST)
    return {
        "month_kwh": round(since, 3),
        "month_days": round(days, 6),
        "month_avg_pd_kwh": round(since / days, 4),
        "restore_at": float(restore_ts),
        "month_label": (
            f"{since:.3f} kWh from {t0.strftime('%d %b %H:%M')} "
            f"to {tnow.strftime('%d %b %H:%M')} ({days:.4f} d)"
        ),
    }
'''

OLD_CALL = "        stats = _avg_pd_since_restore(lifetime, refs)\n"
NEW_CALL = "        stats = _avg_pd_since_restore(lifetime, refs, float(latest.get(\"ts\") or time.time()))\n"

OLD_STATS_AT = '''            rows.append({"code": "month_label", "value": stats["month_label"]})
'''
NEW_STATS_AT = '''            rows.append({"code": "month_label", "value": stats["month_label"]})
            rows.append({"code": "restore_at", "value": stats["restore_at"]})
'''

OLD_RENDER = '''        var avgPd = (b.since != null && b.monthDays > 0) ? (b.since + add) / b.monthDays : null;
        setBreakerMeterSeg("breaker-avg-pd", "Avg/pd", avgPd, " kWh", 1);
        var avgEl = document.getElementById("breaker-avg-pd");
        if (avgEl && b.monthLabel) avgEl.title = b.monthLabel;
'''

NEW_RENDER = '''        var days = (b.restoreAt && isFinite(b.restoreAt))
            ? Math.max(1 / 86400, (Date.now() / 1000 - b.restoreAt) / 86400)
            : b.monthDays;
        var avgPd = (b.since != null && days > 0) ? (b.since + add) / days : null;
        setBreakerMeterSeg("breaker-avg-pd", "Avg/pd", avgPd, " kWh", 2);
        var avgEl = document.getElementById("breaker-avg-pd");
        if (avgEl) {
            avgEl.title = b.monthLabel || ("kWh since restore / elapsed days (" + (days ? days.toFixed(4) : "") + " d)");
        }
'''

OLD_SET = '''        var monthKwh = typeof map.month_kwh === "number" ? map.month_kwh : null;
        var monthDays = typeof map.month_days === "number" ? map.month_days : 0;
        var monthLabel = typeof map.month_label === "string" ? map.month_label : "";
        var b = breakerMeterBase;
        if (!b || b.life !== life || b.since !== since || b.eskom !== eskom || b.monthKwh !== monthKwh || b.monthDays !== monthDays) {
            breakerMeterBase = { life: life, since: since, eskom: eskom, monthKwh: monthKwh, monthDays: monthDays, monthLabel: monthLabel, at: Date.now() };
        }
'''

NEW_SET = '''        var monthKwh = typeof map.month_kwh === "number" ? map.month_kwh : null;
        var monthDays = typeof map.month_days === "number" ? map.month_days : 0;
        var monthLabel = typeof map.month_label === "string" ? map.month_label : "";
        var restoreAt = typeof map.restore_at === "number" ? map.restore_at : null;
        var b = breakerMeterBase;
        if (!b || b.life !== life || b.since !== since || b.eskom !== eskom || b.monthKwh !== monthKwh || b.monthDays !== monthDays || b.restoreAt !== restoreAt) {
            breakerMeterBase = { life: life, since: since, eskom: eskom, monthKwh: monthKwh, monthDays: monthDays, monthLabel: monthLabel, restoreAt: restoreAt, at: Date.now() };
        }
'''


def main() -> None:
    s = API.read_text(encoding="utf-8")
    if OLD_FN not in s:
        raise SystemExit("fn not found")
    s = s.replace(OLD_FN, NEW_FN, 1)
    if OLD_CALL not in s:
        raise SystemExit("call not found")
    s = s.replace(OLD_CALL, NEW_CALL, 1)
    if "restore_at" not in s.split("month_label")[-1][:400]:
        if OLD_STATS_AT not in s:
            raise SystemExit("label append not found")
        s = s.replace(OLD_STATS_AT, NEW_STATS_AT, 1)
    API.write_text(s, encoding="utf-8")
    print("api patched")

    j = JS.read_text(encoding="utf-8")
    if OLD_RENDER not in j:
        raise SystemExit("js render not found")
    j = j.replace(OLD_RENDER, NEW_RENDER, 1)
    if OLD_SET not in j:
        raise SystemExit("js set not found")
    j = j.replace(OLD_SET, NEW_SET, 1)
    JS.write_text(j, encoding="utf-8")
    print("js patched")

    h = HTML.read_text(encoding="utf-8")
    h2 = h.replace("app.js?v=263", "app.js?v=264")
    if "app.js?v=264" not in h2:
        raise SystemExit("cache bump failed")
    HTML.write_text(h2, encoding="utf-8")
    print("html v=264")


if __name__ == "__main__":
    main()
