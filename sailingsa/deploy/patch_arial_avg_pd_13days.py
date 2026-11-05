#!/usr/bin/env python3
from pathlib import Path

OLD_FN = '''def _avg_pd_since_restore(lifetime: float, refs: dict[str, Any]) -> dict[str, Any] | None:
    """(register now − restore reading) ÷ elapsed days between those two readings."""
    restore_ts = refs.get("restoreAt")
    if not isinstance(restore_ts, (int, float)) or float(restore_ts) <= 0:
        return None
    anchor = refs.get("meterKwhAtRestore")
    if not isinstance(anchor, (int, float)):
        anchor = 0.0
    since = max(0.0, float(lifetime) - float(anchor))
    days = (time.time() - float(restore_ts)) / 86_400.0
    if days < 1.0 / 24.0:
        days = 1.0 / 24.0
    return {
        "month_kwh": round(since, 3),
        "month_days": round(days, 3),
        "month_avg_pd_kwh": round(since / days, 3),
        "month_label": f"Since restore: {since:.0f} kWh / {days:.1f} days",
    }
'''

NEW_FN = '''def _avg_pd_since_restore(lifetime: float, refs: dict[str, Any]) -> dict[str, Any] | None:
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

OLD_JS = """        var avgPd = (b.monthKwh != null && b.monthDays > 0) ? (b.monthKwh + add) / b.monthDays : null;
"""
NEW_JS = """        var avgPd = (b.since != null && b.monthDays > 0) ? (b.since + add) / b.monthDays : null;
"""


def main() -> None:
    api = Path("/var/www/sailingsa/api/arial_api.py")
    s = api.read_text(encoding="utf-8")
    if OLD_FN not in s:
        if "first full day 02 Sep" in s:
            print("api already")
        else:
            raise SystemExit("old fn not found")
    else:
        api.write_text(s.replace(OLD_FN, NEW_FN, 1), encoding="utf-8")
        print("api patched")

    js = Path("/var/www/sailingsa/arial/app.js")
    j = js.read_text(encoding="utf-8")
    if OLD_JS in j:
        js.write_text(j.replace(OLD_JS, NEW_JS, 1), encoding="utf-8")
        print("js patched")
    elif NEW_JS in j:
        print("js already")
    else:
        raise SystemExit("js avg not found")

    html = Path("/var/www/sailingsa/arial/index.html")
    h = html.read_text(encoding="utf-8")
    h2 = h.replace("app.js?v=262", "app.js?v=263")
    if "app.js?v=263" not in h2:
        if "app.js?v=263" in h:
            print("html already")
            return
        raise SystemExit("cache bump failed")
    html.write_text(h2, encoding="utf-8")
    print("html v=263")


if __name__ == "__main__":
    main()
