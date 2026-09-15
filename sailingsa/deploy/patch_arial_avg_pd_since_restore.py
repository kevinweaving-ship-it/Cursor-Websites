#!/usr/bin/env python3
"""Avg/pd = (register now − restore reading) / elapsed days between those readings."""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/arial_api.py")
HTML = Path("/var/www/sailingsa/arial/index.html")

OLD_STATS = '''        chk = _hours_checksum_lock_current(TUYA_MAINS_METER_ID, lifetime, float(latest.get("ts") or time.time()))
        if chk:
            rows.append({"code": "hours_since_restore_kwh", "value": chk["hours_sum_kwh"]})
            rows.append({"code": "hours_checksum_residual_kwh", "value": chk["residual_kwh"]})
            rows.append({"code": "hours_checksum_ok", "value": chk["ok"]})
    stats = _month_avg_pd_from_bins(TUYA_MAINS_METER_ID)
    if stats:
        rows.append({"code": "month_kwh", "value": stats["month_kwh"]})
        rows.append({"code": "month_days", "value": stats["month_days"]})
        rows.append({"code": "month_avg_pd_kwh", "value": stats["month_avg_pd_kwh"]})
        rows.append({"code": "month_label", "value": stats["month_label"]})
    return rows
'''

NEW_STATS = '''        chk = _hours_checksum_lock_current(TUYA_MAINS_METER_ID, lifetime, float(latest.get("ts") or time.time()))
        if chk:
            rows.append({"code": "hours_since_restore_kwh", "value": chk["hours_sum_kwh"]})
            rows.append({"code": "hours_checksum_residual_kwh", "value": chk["residual_kwh"]})
            rows.append({"code": "hours_checksum_ok", "value": chk["ok"]})
        stats = _avg_pd_since_restore(lifetime, refs)
        if stats:
            rows.append({"code": "month_kwh", "value": stats["month_kwh"]})
            rows.append({"code": "month_days", "value": stats["month_days"]})
            rows.append({"code": "month_avg_pd_kwh", "value": stats["month_avg_pd_kwh"]})
            rows.append({"code": "month_label", "value": stats["month_label"]})
    return rows
'''

OLD_FN = '''def _month_avg_pd_from_bins(device: str) -> dict[str, Any] | None:
'''

NEW_FN = '''def _avg_pd_since_restore(lifetime: float, refs: dict[str, Any]) -> dict[str, Any] | None:
    """(register now − restore) ÷ calendar days from the first full day after restore to today.

    Restore was 01 Sep 18:57, so the first full day is 02 Sep. 02 Sep → 15 Sep = 13 days
    (15 − 2). Not day-of-month (15 → 22.7) and not elapsed hours from 18:57.
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
    days = (today - start).days  # 2 Sep → 15 Sep = 13
    if days < 1:
        days = 1
    return {
        "month_kwh": round(since, 3),
        "month_days": days,
        "month_avg_pd_kwh": round(since / days, 3),
        "month_label": f"Since restore: {since:.0f} kWh / {days} days ({start.day}–{today.day} {_MONTHS[today.month - 1]})",
    }


def _month_avg_pd_from_bins(device: str) -> dict[str, Any] | None:
'''

OLD_HTML = 'title="This month: kWh ÷ calendar days so far (SAST)"'
NEW_HTML = 'title="kWh since restore ÷ days between restore and now"'


def main() -> None:
    s = API.read_text(encoding="utf-8")
    if "def _avg_pd_since_restore" not in s:
        if OLD_FN not in s:
            raise SystemExit("month fn not found")
        s = s.replace(OLD_FN, NEW_FN, 1)
    if OLD_STATS in s:
        s = s.replace(OLD_STATS, NEW_STATS, 1)
    elif "_avg_pd_since_restore(lifetime, refs)" in s:
        print("api stats already")
    else:
        raise SystemExit("stats block not found")
    API.write_text(s, encoding="utf-8")
    print("api patched")
    html = HTML.read_text(encoding="utf-8")
    if OLD_HTML in html:
        HTML.write_text(html.replace(OLD_HTML, NEW_HTML, 1), encoding="utf-8")
        print("html title patched")
    else:
        print("html title already or missing")


if __name__ == "__main__":
    main()
