"""Read-only GpsGate client. Token stays in the process environment."""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Mapping, Optional

ALLOWED_USER_IDS = frozenset({2619, 2079})
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIMEOUT_SEC = 15
_MAX_ATTEMPTS = 4
_BACKOFF_SEC = (1.0, 2.0, 4.0)
_MAX_RETRY_AFTER_SEC = 8.0
_SCALAR = (str, int, float, bool, type(None))


class GpsGateError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GpsGateNotAllowed(GpsGateError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        raise GpsGateError("unexpected redirect %s" % code, status_code=code)


def _require_user(user_id: int) -> int:
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        raise GpsGateNotAllowed("user id is not allowlisted")
    if uid not in ALLOWED_USER_IDS or str(user_id).strip() != str(uid):
        raise GpsGateNotAllowed("user id is not allowlisted")
    return uid


def _config() -> tuple:
    base = (os.environ.get("GPSGATE_BASE_URL") or "").strip().rstrip("/")
    app_raw = (os.environ.get("GPSGATE_APP_ID") or "").strip()
    token = os.environ.get("GPSGATE_TOKEN") or ""
    if not base or not app_raw or not token.strip():
        raise GpsGateError("GpsGate environment is incomplete")
    if not base.startswith("https://"):
        raise GpsGateError("GPSGATE_BASE_URL must be https")
    try:
        app_id = int(app_raw)
    except ValueError:
        raise GpsGateError("GPSGATE_APP_ID is invalid")
    return base, app_id, token.strip()


def _num(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _variables(raw: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            value = item.get("value")
            if not isinstance(value, _SCALAR):
                continue
            out.append(
                {
                    "name": item.get("name") if isinstance(item.get("name"), str) else None,
                    "type": item.get("type") if isinstance(item.get("type"), str) else None,
                    "time": item.get("time") if isinstance(item.get("time"), str) else None,
                    "value": value,
                }
            )
        return out
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            if not isinstance(key, str) or not isinstance(value, _SCALAR):
                continue
            out.append({"name": key, "type": None, "time": None, "value": value})
    return out


def _normalize(raw: Mapping[str, Any]) -> Dict[str, Any]:
    pos = raw.get("position") if isinstance(raw.get("position"), Mapping) else {}
    vel = raw.get("velocity") if isinstance(raw.get("velocity"), Mapping) else {}
    utc = raw.get("utc") if isinstance(raw.get("utc"), str) else raw.get("uTC")
    valid = raw.get("valid")
    return {
        "utc": utc if isinstance(utc, str) else None,
        "lat": _num(pos.get("latitude")),
        "lon": _num(pos.get("longitude")),
        "altitude": _num(pos.get("altitude")),
        "groundSpeed": _num(vel.get("groundSpeed")),
        "heading": _num(vel.get("heading")),
        "valid": valid if isinstance(valid, bool) else None,
        "variables": _variables(raw.get("variables")),
    }


def _retry_after(header: Optional[str], attempt: int) -> float:
    if header:
        try:
            return min(float(header), _MAX_RETRY_AFTER_SEC)
        except ValueError:
            pass
    idx = min(attempt, len(_BACKOFF_SEC) - 1)
    return _BACKOFF_SEC[idx]


class GpsGateClient:
    """GET status and tracks for the allowlisted assets only."""

    def __init__(self) -> None:
        self._base, self._app_id, self._token = _config()
        self._opener = urllib.request.build_opener(_NoRedirect)

    def status(self, user_id: int) -> Dict[str, Any]:
        uid = _require_user(user_id)
        path = "/applications/%s/users/%s/status" % (self._app_id, uid)
        return _normalize(self._get(path))

    def tracks(self, user_id: int, on_date: str) -> List[Dict[str, Any]]:
        uid = _require_user(user_id)
        if not isinstance(on_date, str) or not _DATE_RE.match(on_date):
            raise GpsGateError("tracks date must be YYYY-MM-DD")
        path = "/applications/%s/users/%s/tracks" % (self._app_id, uid)
        body = self._get(path, {"Date": on_date})
        if not isinstance(body, list):
            raise GpsGateError("tracks response was not a list")
        return [_normalize(item) for item in body if isinstance(item, Mapping)]

    def _get(self, path: str, query: Optional[Mapping[str, str]] = None) -> Any:
        url = self._base + "/comGpsGate/api/v.1" + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        last_code: Optional[int] = None
        for attempt in range(_MAX_ATTEMPTS):
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "Authorization": self._token},
                method="GET",
            )
            try:
                resp = self._opener.open(req, timeout=_TIMEOUT_SEC)
                raw = resp.read()
                code = resp.status
            except urllib.error.HTTPError as err:
                last_code = err.code
                if err.code in (429, 503) and attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(_retry_after(err.headers.get("Retry-After"), attempt))
                    continue
                raise GpsGateError("GpsGate HTTP %s" % err.code, status_code=err.code)
            except urllib.error.URLError:
                raise GpsGateError("GpsGate request failed")
            if code in (429, 503) and attempt < _MAX_ATTEMPTS - 1:
                time.sleep(_retry_after(resp.headers.get("Retry-After"), attempt))
                continue
            if code != 200:
                raise GpsGateError("GpsGate HTTP %s" % code, status_code=code)
            try:
                return json.loads(raw.decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError):
                raise GpsGateError("GpsGate response was not JSON", status_code=code)
        raise GpsGateError("GpsGate HTTP %s" % (last_code or 503), status_code=last_code)
