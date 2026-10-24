"""Discover Weather Underground / Weather.com PWS fetch credentials from the live dashboard.

WU rotates the browser apiKey embedded in https://www.wunderground.com/dashboard/pws/{STATION}.
The old hardcoded web key (e1f10a…) now 401s while the station is still CONNECTED on the site.

This module:
  1. Knows exactly which scrape fields club weather needs (REQUIRED_SCRAPE).
  2. Watches the dashboard HTML fingerprint for site redesigns.
  3. Auto-fixes on 401/403, empty observations, or fingerprint change by
     re-scraping keys + observation endpoint paths and probing until one works.
  4. Caches a working key so ingest (every 5 min) and /api/weather/hyc keep updating
     without a manual code change when WU redesigns the dashboard.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DASHBOARD = "https://www.wunderground.com/dashboard/pws/{station}"
CURRENT_PATH = "https://api.weather.com/v2/pws/observations/current"
DAY_PATH = "https://api.weather.com/v2/pws/observations/all/1day"
CACHE_ENV = "WU_DISCOVER_CACHE"
DEFAULT_CACHE = Path("/var/www/sailingsa/data/wu_discover_cache.json")
# Keep a working key this long if probes still succeed.
CACHE_TTL_SEC = 6 * 3600
# Even with a working key, re-check the dashboard HTML this often so site
# redesigns are caught before the next hard 401.
WATCH_INTERVAL_SEC = 30 * 60
PROBE_STATION = "IOVERS2"

# Contract: what club weather must obtain from the WU site / API.
# If WU renames these, scrape patterns + probes below must be updated once;
# runtime autofix handles key/URL rotation within this contract.
REQUIRED_SCRAPE: dict[str, Any] = {
    "dashboard_url": "https://www.wunderground.com/dashboard/pws/{STATION}",
    "api_key": {
        "where": "dashboard HTML (apiKey=… / \"apiKey\":\"…\" / PWS observation URLs)",
        "purpose": "authorize api.weather.com PWS observations",
    },
    "endpoints": {
        "current": CURRENT_PATH,
        "day": DAY_PATH,
    },
    "query": {
        "stationId": "{STATION}",
        "format": "json",
        "units": "m",
        "numericPrecision": "decimal",
        "apiKey": "{discovered}",
    },
    "observation_fields": [
        "obsTimeUtc",
        "winddir",
        "humidity",
        "metric.windSpeed",
        "metric.windGust",
        "metric.temp",
        # imperial fallback used when metric block absent
        "imperial.windSpeed",
        "imperial.windGust",
        "imperial.temp",
    ],
    "club_output_units": "knots (converted from mph or km/h)",
}

_mem: dict[str, Any] = {"at": 0.0, "data": None}


def _cache_path() -> Path:
    raw = (os.environ.get(CACHE_ENV) or "").strip()
    return Path(raw) if raw else DEFAULT_CACHE


def _load_cache() -> dict[str, Any]:
    now = time.time()
    hit = _mem.get("data")
    if isinstance(hit, dict) and (now - float(_mem.get("at") or 0)) < 60:
        return hit
    path = _cache_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            _mem["at"] = now
            _mem["data"] = data
            return data
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return {}


def _save_cache(data: dict[str, Any]) -> None:
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
        try:
            os.chmod(path, 0o640)
        except OSError:
            pass
    except OSError:
        pass
    _mem["at"] = time.time()
    _mem["data"] = data


def _fingerprint(text: str, keys: list[str], current: str, day: str) -> str:
    """Stable-ish digest of how the dashboard exposes keys/endpoints."""
    script_srcs = sorted(set(re.findall(r'src="(/[^"]+\.js)"', text)))[:40]
    blob = json.dumps(
        {
            "keys": sorted(keys)[:12],
            "current": current,
            "day": day,
            "scripts": script_srcs,
            "has_next": "__NEXT_DATA__" in text,
            "bytes": len(text),
        },
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


def scrape_dashboard_keys(station_id: str = PROBE_STATION) -> dict[str, Any]:
    """Pull apiKeys and PWS URLs from the public WU dashboard HTML."""
    sid = (station_id or PROBE_STATION).strip().upper() or PROBE_STATION
    url = DASHBOARD.format(station=sid)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        text = resp.read().decode("utf-8", "replace")

    keys = set(re.findall(r"apiKey=([A-Za-z0-9]{20,})", text, flags=re.I))
    keys |= set(re.findall(r'"apiKey"\s*:\s*"([A-Za-z0-9]{20,})"', text))
    keys |= set(re.findall(r"'apiKey'\s*:\s*'([A-Za-z0-9]{20,})'", text))
    # Next.js / embedded JSON blobs often hold the browser key after redesigns.
    for m in re.finditer(r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, flags=re.I | re.S):
        keys |= set(re.findall(r'"apiKey"\s*:\s*"([A-Za-z0-9]{20,})"', m.group(1)))
    for m in re.finditer(r'<script[^>]+type="application/json"[^>]*>(.*?)</script>', text, flags=re.I | re.S):
        chunk = m.group(1)
        if "apiKey" in chunk or "weather.com" in chunk:
            keys |= set(re.findall(r'"apiKey"\s*:\s*"([A-Za-z0-9]{20,})"', chunk))

    urls = sorted(set(re.findall(r"https://api\.weather\.com[^\"'\s<>]+", text)))
    preferred: list[str] = []
    current = CURRENT_PATH
    day = DAY_PATH
    for u in urls:
        m = re.search(r"[?&]apiKey=([A-Za-z0-9]{20,})", u)
        if m:
            keys.add(m.group(1))
            if "/pws/" in u:
                preferred.append(m.group(1))
        if "/observations/current" in u:
            current = u.split("?", 1)[0]
        elif "/observations/all/1day" in u:
            day = u.split("?", 1)[0]

    # Prefer keys already bound to PWS observation URLs (e.g. ff90…), then others.
    ordered: list[str] = []
    for k in preferred + sorted(keys):
        if k not in ordered:
            ordered.append(k)
    fp = _fingerprint(text, ordered, current, day)
    return {
        "station_id": sid,
        "dashboard": url,
        "keys": list(ordered),
        "current_path": current,
        "day_path": day,
        "scraped_at": time.time(),
        "html_bytes": len(text),
        "fingerprint": fp,
        "required": list(REQUIRED_SCRAPE["observation_fields"]),
    }


def _probe_key(api_key: str, station_id: str, current_path: str) -> bool:
    q = urllib.parse.urlencode(
        {
            "stationId": station_id,
            "format": "json",
            "units": "m",
            "numericPrecision": "decimal",
            "apiKey": api_key,
        }
    )
    req = urllib.request.Request(
        f"{current_path}?{q}",
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
            "Origin": "https://www.wunderground.com",
            "Referer": DASHBOARD.format(station=station_id),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8", "replace") or "{}")
        return bool(isinstance(body, dict) and (body.get("observations") or []))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return False


def discover_credentials(station_id: str = PROBE_STATION, force: bool = False) -> dict[str, Any]:
    """Return {api_key, current_path, day_path, source, scraped_at, fingerprint} or {}."""
    sid = (station_id or PROBE_STATION).strip().upper() or PROBE_STATION
    cache = _load_cache()
    age = time.time() - float(cache.get("scraped_at") or 0)
    if (
        not force
        and cache.get("api_key")
        and age < CACHE_TTL_SEC
        and _probe_key(str(cache["api_key"]), sid, str(cache.get("current_path") or CURRENT_PATH))
    ):
        out = dict(cache)
        out["source"] = out.get("source") or "cache"
        out["ok"] = True
        return out

    scraped = scrape_dashboard_keys(sid)
    chosen = ""
    for key in scraped.get("keys") or []:
        if _probe_key(key, sid, str(scraped.get("current_path") or CURRENT_PATH)):
            chosen = key
            break
    if not chosen:
        return {
            "ok": False,
            "err": "no_working_dashboard_key",
            "keys_found": len(scraped.get("keys") or []),
            "dashboard": scraped.get("dashboard"),
            "scraped_at": scraped.get("scraped_at"),
            "fingerprint": scraped.get("fingerprint"),
            "required": REQUIRED_SCRAPE,
        }

    out = {
        "ok": True,
        "api_key": chosen,
        "current_path": scraped.get("current_path") or CURRENT_PATH,
        "day_path": scraped.get("day_path") or DAY_PATH,
        "source": "dashboard_scrape",
        "dashboard": scraped.get("dashboard"),
        "scraped_at": scraped.get("scraped_at") or time.time(),
        "station_id": sid,
        "html_bytes": scraped.get("html_bytes"),
        "fingerprint": scraped.get("fingerprint"),
        "watched_at": time.time(),
    }
    _save_cache(out)
    return out


def watch_site_and_autofix(station_id: str = PROBE_STATION) -> dict[str, Any]:
    """Proactive watcher for ingest timer / health checks.

    Every call:
      - Probes the cached key against the current observations endpoint.
      - Periodically re-scrapes the dashboard fingerprint; if the site changed
        (or the key fails), rediscovers a working apiKey + paths automatically.
    """
    sid = (station_id or PROBE_STATION).strip().upper() or PROBE_STATION
    cache = _load_cache()
    now = time.time()
    key = str(cache.get("api_key") or "")
    current = str(cache.get("current_path") or CURRENT_PATH)
    watched_age = now - float(cache.get("watched_at") or cache.get("scraped_at") or 0)

    if key and _probe_key(key, sid, current):
        if watched_age < WATCH_INTERVAL_SEC:
            out = dict(cache)
            out["ok"] = True
            out["watch"] = "probe_ok"
            out["source"] = out.get("source") or "cache"
            return out
        # Soft watch: re-scrape HTML; keep key unless fingerprint/endpoints moved
        # or the scraped key set no longer includes ours.
        try:
            scraped = scrape_dashboard_keys(sid)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            out = dict(cache)
            out["ok"] = True
            out["watch"] = "scrape_soft_fail"
            out["watch_err"] = str(exc)[:160]
            out["watched_at"] = now
            _save_cache({k: v for k, v in out.items() if k not in ("watch", "watch_err")})
            return out
        old_fp = str(cache.get("fingerprint") or "")
        new_fp = str(scraped.get("fingerprint") or "")
        keys = list(scraped.get("keys") or [])
        path_changed = (
            str(scraped.get("current_path") or CURRENT_PATH) != current
            or str(scraped.get("day_path") or DAY_PATH) != str(cache.get("day_path") or DAY_PATH)
        )
        key_still_listed = (not keys) or (key in keys)
        if old_fp and new_fp and old_fp != new_fp and (path_changed or not key_still_listed):
            disc = discover_credentials(sid, force=True)
            disc["watch"] = "fingerprint_changed_refixed"
            return disc
        # Key still works; refresh fingerprint/watch timestamp.
        cache = dict(cache)
        cache["fingerprint"] = new_fp or old_fp
        cache["watched_at"] = now
        cache["html_bytes"] = scraped.get("html_bytes") or cache.get("html_bytes")
        if scraped.get("current_path"):
            cache["current_path"] = scraped["current_path"]
        if scraped.get("day_path"):
            cache["day_path"] = scraped["day_path"]
        _save_cache(cache)
        out = dict(cache)
        out["ok"] = True
        out["watch"] = "soft_ok"
        out["source"] = out.get("source") or "cache"
        return out

    # Hard path: missing/dead key → full rediscover.
    disc = discover_credentials(sid, force=True)
    disc["watch"] = "probe_failed_refixed" if key else "no_cache_discover"
    return disc


def working_api_key(
    env_key: Optional[str] = None,
    station_id: str = PROBE_STATION,
    force_refresh: bool = False,
) -> tuple[Optional[str], str]:
    """Prefer explicit env key; else discovered dashboard key. Returns (key, source)."""
    if env_key and str(env_key).strip():
        return str(env_key).strip(), "env"
    disc = discover_credentials(station_id=station_id, force=force_refresh)
    if disc.get("ok") and disc.get("api_key"):
        return str(disc["api_key"]), str(disc.get("source") or "discover")
    return None, "none"


def wu_get(
    path: str,
    station_id: str,
    api_key: str,
    units: str = "m",
    extra: Optional[dict] = None,
) -> dict[str, Any]:
    q = {
        "stationId": station_id,
        "format": "json",
        "units": units,
        "numericPrecision": "decimal",
        "apiKey": api_key,
    }
    if extra:
        q.update(extra)
    url = path + "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
            "Origin": "https://www.wunderground.com",
            "Referer": DASHBOARD.format(station=station_id),
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8", "replace") or "{}")
    return body if isinstance(body, dict) else {}


def fetch_with_autofix(
    station_id: str,
    *,
    env_key: Optional[str] = None,
    hours: int = 12,
    units: str = "m",
) -> dict[str, Any]:
    """Current + 1-day observations. On 401/403, re-scrape dashboard and retry once."""
    sid = (station_id or PROBE_STATION).strip().upper()
    key, source = working_api_key(env_key, sid, force_refresh=False)
    disc = _load_cache() if source != "env" else {}
    current_path = str(disc.get("current_path") or CURRENT_PATH)
    day_path = str(disc.get("day_path") or DAY_PATH)

    def _pull(k: str) -> dict[str, Any]:
        day = wu_get(day_path, sid, k, units=units)
        cur = wu_get(current_path, sid, k, units=units)
        obs = list(day.get("observations") or [])
        for row in cur.get("observations") or []:
            oid = row.get("obsTimeUtc")
            if oid and all(x.get("obsTimeUtc") != oid for x in obs):
                obs.append(row)
        return {
            "ok": True,
            "station_id": sid,
            "observations": obs,
            "key_source": source,
            "current_path": current_path,
            "day_path": day_path,
            "hours": hours,
        }

    if not key:
        disc2 = discover_credentials(sid, force=True)
        if not disc2.get("ok"):
            return {"ok": False, "err": disc2.get("err") or "no_api_key", "station_id": sid}
        key = str(disc2["api_key"])
        source = "dashboard_scrape"
        current_path = str(disc2.get("current_path") or CURRENT_PATH)
        day_path = str(disc2.get("day_path") or DAY_PATH)

    try:
        return _pull(key)
    except urllib.error.HTTPError as exc:
        if int(getattr(exc, "code", 0) or 0) not in {401, 403}:
            return {"ok": False, "err": str(exc)[:200], "station_id": sid}
        disc2 = discover_credentials(sid, force=True)
        if not disc2.get("ok"):
            return {"ok": False, "err": f"auth_failed_and_rediscover:{disc2.get('err')}", "station_id": sid}
        key = str(disc2["api_key"])
        source = "dashboard_scrape_retry"
        current_path = str(disc2.get("current_path") or CURRENT_PATH)
        day_path = str(disc2.get("day_path") or DAY_PATH)
        try:
            out = _pull(key)
            out["key_source"] = source
            return out
        except Exception as exc2:  # noqa: BLE001
            return {"ok": False, "err": str(exc2)[:200], "station_id": sid}
