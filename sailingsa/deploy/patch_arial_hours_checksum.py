#!/usr/bin/env python3
"""Keep Hansekop hourly bins checksummed to the meter register (restore → now)."""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/arial_api.py")

OLD_ROWS_TAIL = '''        offset = refs.get("eskomOffsetKwh")
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

NEW_ROWS_TAIL = '''        offset = refs.get("eskomOffsetKwh")
        if isinstance(offset, (int, float)):
            rows.append({"code": "eskom_kwh", "value": round(lifetime + float(offset), 1)})
        chk = _hours_checksum_lock_current(TUYA_MAINS_METER_ID, lifetime, float(latest.get("ts") or time.time()))
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

OLD_MONTH_END = '''    _month_pd_cache.update({"at": now, "device": device, "data": data})
    return data


def _energy_merge_disk(data: Any) -> None:
'''

NEW_MONTH_END = '''    _month_pd_cache.update({"at": now, "device": device, "data": data})
    return data


_checksum_force: dict[str, dict[str, float]] = {}
_checksum_cache: dict[str, Any] = {"at": 0.0, "data": None}


def _hours_checksum_lock_current(device: str, register_kwh: float, now: float | None = None) -> dict[str, Any]:
    """Completed hours stay frozen; current hour = (register - restore) - sum(completed).

    Identity: sum(hourly kWh from restore through now) == meter register since restore.
    """
    ts = float(now if now is not None else time.time())
    refs = _meter_refs_load()
    restore_ts = float(refs.get("restoreAt") or 0.0)
    restore_kwh = float(refs.get("meterKwhAtRestore") or 0.0)
    expected = round(max(0.0, float(register_kwh) - restore_kwh), 6)
    restore_key = datetime.fromtimestamp(restore_ts, tz=timezone.utc).astimezone(_SAST).strftime("%Y%m%d%H") if restore_ts else "0000000000"
    now_key = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(_SAST).strftime("%Y%m%d%H")
    with _energy_lock:
        _energy_load()
        hours = _energy_bins.setdefault(device, {})
        completed = 0.0
        for key, val in hours.items():
            if restore_key <= str(key) < now_key and isinstance(val, (int, float)):
                completed += float(val)
        current = round(max(0.0, expected - completed), 6)
        prev = hours.get(now_key)
        if prev != current:
            hours[now_key] = current
            _checksum_force.setdefault(device, {})[now_key] = current
            _energy_save()
        got = round(completed + current, 6)
    residual = round(expected - got, 6)
    data = {
        "restore_kwh": restore_kwh,
        "register_kwh": round(float(register_kwh), 6),
        "expected_kwh": expected,
        "hours_sum_kwh": got,
        "residual_kwh": residual,
        "ok": abs(residual) < 0.05,
    }
    _checksum_cache.update({"at": time.time(), "data": data})
    _month_pd_cache["at"] = 0.0
    return data


def _energy_merge_disk(data: Any) -> None:
'''

OLD_SAVE_WRITE = '''                "bins": _energy_bins,
                "recent": {dev: [[t, w] for t, w in rows] for dev, rows in _energy_recent.items()},
'''

NEW_SAVE_WRITE = '''                "bins": _energy_bins,
                "recent": {dev: [[t, w] for t, w in rows] for dev, rows in _energy_recent.items()},
'''

OLD_SAVE_MERGE = '''def _energy_save() -> None:
    """Merge with what is on disk, then write. Caller holds _energy_lock."""
    global _energy_mtime
    path = _energy_store_path()
'''

# We'll patch after merge in _energy_save by inserting force apply. Need exact save body.

OLD_RECORD_ADD = '''            key = _sa_hour_key(cur)
            hours[key] = round(hours.get(key, 0.0) + avg_w * (seg_end - cur) / 3_600_000.0, 6)
            cur = seg_end
'''

NEW_RECORD_ADD = '''            key = _sa_hour_key(cur)
            # Completed hours are frozen to the meter register checksum; only the current hour integrates watts.
            if key < _sa_hour_key(ts):
                cur = seg_end
                continue
            hours[key] = round(hours.get(key, 0.0) + avg_w * (seg_end - cur) / 3_600_000.0, 6)
            cur = seg_end
'''

OLD_APPLY_END = '''        if not online:
            with _energy_lock:
                _energy_last.pop(device, None)
    return used
'''

NEW_APPLY_END = '''        if not online:
            with _energy_lock:
                _energy_last.pop(device, None)
    if reading.get("meterKwh") is not None:
        _hours_checksum_lock_current(device, float(reading["meterKwh"]), reading.get("ts"))
    return used
'''


def _patch(path: Path, old: str, new: str, already: str) -> str:
    text = path.read_text(encoding="utf-8")
    if already in text and old not in text:
        return "already"
    if old not in text:
        raise SystemExit(f"block not found: {already}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return "patched"


def main() -> None:
    bak = API.with_name(API.name + ".bak-checksum")
    if not bak.exists():
        bak.write_bytes(API.read_bytes())
    print("fn", _patch(API, OLD_MONTH_END, NEW_MONTH_END, "def _hours_checksum_lock_current"))
    print("rows", _patch(API, OLD_ROWS_TAIL, NEW_ROWS_TAIL, "hours_since_restore_kwh"))
    print("record", _patch(API, OLD_RECORD_ADD, NEW_RECORD_ADD, "Completed hours are frozen"))
    print("apply", _patch(API, OLD_APPLY_END, NEW_APPLY_END, "_hours_checksum_lock_current(device, float(reading"))

    # After merge_disk inside _energy_save, re-apply forced current-hour values so max() cannot undo the checksum.
    text = API.read_text(encoding="utf-8")
    needle = '''            _energy_merge_disk(json.loads(path.read_text(encoding="utf-8")))
'''
    inject = '''            _energy_merge_disk(json.loads(path.read_text(encoding="utf-8")))
            for dev, forced in _checksum_force.items():
                mine = _energy_bins.setdefault(str(dev), {})
                mine.update(forced)
'''
    if "for dev, forced in _checksum_force.items()" in text:
        print("save-force already")
    elif needle not in text:
        raise SystemExit("energy_save merge not found")
    else:
        API.write_text(text.replace(needle, inject, 1), encoding="utf-8")
        print("save-force patched")


if __name__ == "__main__":
    main()
