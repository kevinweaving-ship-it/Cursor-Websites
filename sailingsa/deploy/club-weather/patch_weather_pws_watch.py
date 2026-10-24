#!/usr/bin/env python3
"""Patch live weather_pws.py for WU 401 autofix + dashboard watch."""
from __future__ import annotations

import time
from pathlib import Path

p = Path("/var/www/sailingsa/sailingsa/backend/weather_pws.py")
text = p.read_text(encoding="utf-8")
bak = p.with_suffix(p.suffix + ".bak_watch_" + time.strftime("%Y%m%dT%H%M%SZ"))
bak.write_text(text, encoding="utf-8")

old = """def fetch_pws_current(pws_id: str, api_key: str) -> dict[str, Any]:
    params = urlencode(
        {
            "stationId": pws_id,
            "format": "json",
            "units": "m",
            "numericPrecision": "decimal",
            "apiKey": api_key,
        }
    )
    req = Request(
        f"{PWS_CURRENT_URL}?{params}",
        headers={"Accept": "application/json", "User-Agent": "SailingSA-weather/1"},
    )
    with urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
    return body if isinstance(body, dict) else {}
"""

new = '''def fetch_pws_current(pws_id: str, api_key: str) -> dict[str, Any]:
    """Fetch current PWS obs; on 401/403 re-scrape WU dashboard key and retry once."""
    import sys
    from urllib.error import HTTPError

    def _pull(key: str) -> dict[str, Any]:
        params = urlencode(
            {
                "stationId": pws_id,
                "format": "json",
                "units": "m",
                "numericPrecision": "decimal",
                "apiKey": key,
            }
        )
        req = Request(
            f"{PWS_CURRENT_URL}?{params}",
            headers={
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (compatible; SailingSA-weather/1)",
                "Origin": "https://www.wunderground.com",
                "Referer": f"https://www.wunderground.com/dashboard/pws/{pws_id}",
            },
        )
        with urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="replace") or "{}")
        return body if isinstance(body, dict) else {}

    try:
        return _pull(api_key)
    except HTTPError as exc:
        if int(getattr(exc, "code", 0) or 0) not in {401, 403}:
            raise
        api_dir = "/var/www/sailingsa/api"
        if api_dir not in sys.path:
            sys.path.insert(0, api_dir)
        import weather_wu_discover as wu_disc
        disc = wu_disc.discover_credentials(str(pws_id) or "IOVERS2", force=True)
        if not disc.get("ok") or not disc.get("api_key"):
            raise
        return _pull(str(disc["api_key"]))
'''

if "dashboard_scrape" in text and "re-scrape WU dashboard key" in text:
    print("already_patched", p)
else:
    if old not in text:
        raise SystemExit("fetch_pws_current block not found for patch")
    text = text.replace(old, new, 1)

if '"html_scrape": False,' in text:
    text = text.replace(
        '"html_scrape": False,',
        '"html_scrape": True,  # WU dashboard watch via weather_wu_discover',
        1,
    )
text = text.replace(
    "Does not scrape HTML dashboards. Polling stays off until an API key exists.",
    "Uses weather_wu_discover to watch/scrape the WU dashboard when env keys rotate.",
    1,
)
p.write_text(text, encoding="utf-8")
print("patched", p, "backup", bak)
