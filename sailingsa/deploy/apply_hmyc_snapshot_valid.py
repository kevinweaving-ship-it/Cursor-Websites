#!/usr/bin/env python3
"""GET-validate HMYC latest.jpg. Empty 200 image/jpeg is not a valid snapshot."""
from pathlib import Path

WX = Path("/var/www/sailingsa/api/weather_agromet.py")
MARK = "HMYC_SNAPSHOT_VALID_v1"

OLD = '''def snapshot_status() -> dict:
    """HEAD latest.jpg. This is a snapshot file, not a live stream."""
    try:
        req = urllib.request.Request(
            CAM_STILL,
            method="HEAD",
            headers={"User-Agent": "SailingSA-weather/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_lm = resp.headers.get("Last-Modified") or ""
        as_at = None
        last_iso = None
        if raw_lm:
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(raw_lm)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            last_iso = dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            as_at = _format_as_at(dt)
        return {
            "ok": True,
            "kind": "snapshot",
            "label": CAM_LABEL,
            "interval_sec": CAM_INTERVAL_SEC,
            "src": CAM_STILL,
            "last_modified": last_iso,
            "as_at": as_at,
        }
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        return {
            "ok": False,
            "kind": "snapshot",
            "label": CAM_LABEL,
            "interval_sec": CAM_INTERVAL_SEC,
            "src": CAM_STILL,
            "err": str(exc)[:200],
        }
'''

NEW = '''def snapshot_status() -> dict:
    """GET latest.jpg. 200 + image/jpeg + 0 bytes is the down camera — not valid."""
    base = {
        "ok": False,
        "valid": False,
        "kind": "snapshot",
        "label": CAM_LABEL,
        "interval_sec": CAM_INTERVAL_SEC,
        "src": CAM_STILL,
    }
    try:
        req = urllib.request.Request(
            CAM_STILL,
            method="GET",
            headers={"User-Agent": "SailingSA-weather/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15, context=_SSL) as resp:
            status = int(getattr(resp, "status", 200) or 200)
            raw_lm = resp.headers.get("Last-Modified") or ""
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            cl = resp.headers.get("Content-Length")
            head = resp.read(16)
            if cl and str(cl).isdigit():
                n = int(cl)
            else:
                rest = resp.read()
                n = len(head) + len(rest)
                head = head + rest
        as_at = None
        last_iso = None
        if raw_lm:
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(raw_lm)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            last_iso = dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
            as_at = _format_as_at(dt)
        jpeg = head.startswith(b"\\xff\\xd8\\xff")
        valid = status == 200 and ctype.startswith("image/") and jpeg and n >= 2048
        reason = ""
        if not valid:
            if n < 2048:
                reason = "empty_or_tiny"
            elif not jpeg:
                reason = "not_jpeg"
            else:
                reason = "not_image"
        base.update(
            {
                "ok": True,
                "valid": valid,
                "bytes": n,
                "content_type": ctype,
                "last_modified": last_iso,
                "as_at": as_at,
                "reason": reason,
            }
        )
        return base  # ''' + MARK + '''
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        base["err"] = str(exc)[:200]
        return base
'''


def main() -> None:
    text = WX.read_text()
    if MARK in text:
        print("WX_ALREADY")
        return
    n = text.count(OLD)
    if n != 1:
        raise SystemExit(f"ANCHOR_{n}")
    WX.write_text(text.replace(OLD, NEW, 1))
    print("WX_OK")


if __name__ == "__main__":
    main()
