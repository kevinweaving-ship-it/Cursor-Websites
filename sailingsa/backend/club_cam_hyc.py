"""HYC live cam — pass-through of Cam 5 on the club DS NVR.

Do not snapshot-poll. Stream the live feed through the same Arial hikpoc/go2rtc
path used for other Hikvision NVRs:

  GET /api/club-cam/hyc/live  → HLS from local go2rtc (src=hyc).

Upstream (first match):
  HYC_NVR_LIVE_URL     explicit URL override
  go2rtc HLS           HYC_GO2RTC_URL + src=HYC_GO2RTC_SRC (default hyc)
  HYC_NVR_HOST + Cam 5 HTTP live preview (ISAPI channel 502 = Cam 5 substream)

go2rtc producer: Hik-Connect serial D23413606 (HYC DS-7608NI-K2/8P) channel 5.
Credentials stay on the server / hikpoc bridge.
"""
from __future__ import annotations

import json
import os
import ssl
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import (
    HTTPDigestAuthHandler,
    HTTPPasswordMgrWithDefaultRealm,
    Request,
    build_opener,
    urlopen,
)
from zoneinfo import ZoneInfo

CAM_NO = 5
# Cam 5 main = 501, substream live preview = 502 (HTTP pass-through).
ISAPI_LIVE_CHANNEL = CAM_NO * 100 + 2
ISAPI_MAIN_CHANNEL = CAM_NO * 100 + 1
LABEL = "HYC club cam"
KIND = "live"
SAST = ZoneInfo("Africa/Johannesburg")
LIVE_SRC = "/api/club-cam/hyc/live"
UA = "SailingSA-club-cam/1.0"
GO2RTC_DEFAULT = "http://127.0.0.1:1984"
GO2RTC_SRC_DEFAULT = "hyc"
HIK_SERIAL = "D23413606"
HIK_CHANNEL = CAM_NO

_vis_cache = {"at": 0.0, "visible": True}
_VIS_TTL = 1.0


def vis_path() -> Path:
    raw = (os.environ.get("HYC_CAM_VISIBLE_FILE") or "").strip()
    if raw:
        return Path(raw)
    for cand in (
        Path("/var/lib/sailingsa/club-cam-hyc.json"),
        Path("/tmp/sailingsa-club-cam-hyc.json"),
    ):
        parent = cand.parent
        try:
            parent.mkdir(parents=True, exist_ok=True)
            if os.access(parent, os.W_OK):
                return cand
        except OSError:
            continue
    return Path("/tmp/sailingsa-club-cam-hyc.json")


def is_visible() -> bool:
    now = time.time()
    if now - float(_vis_cache.get("at") or 0) < _VIS_TTL:
        return bool(_vis_cache.get("visible", True))
    visible = True
    path = vis_path()
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "visible" in data:
                visible = bool(data.get("visible"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        visible = True
    _vis_cache["at"] = now
    _vis_cache["visible"] = visible
    return visible


def set_visible(visible: bool) -> bool:
    flag = bool(visible)
    path = vis_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"visible": flag}, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    _vis_cache["at"] = time.time()
    _vis_cache["visible"] = flag
    return flag


def nvr_host() -> str:
    return (os.environ.get("HYC_NVR_HOST") or "").strip().rstrip("/")


def nvr_user() -> str:
    return (os.environ.get("HYC_NVR_USER") or "").strip()


def nvr_password() -> str:
    return os.environ.get("HYC_NVR_PASSWORD") or ""


def nvr_port() -> int:
    raw = (os.environ.get("HYC_NVR_PORT") or "80").strip()
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = 80
    return n if n > 0 else 80


def nvr_base() -> str:
    host = nvr_host()
    if not host:
        return ""
    if "://" in host:
        return host.rstrip("/")
    port = nvr_port()
    return f"http://{host}" + ("" if port in (80, 0) else f":{port}")


def live_channel() -> int:
    raw = (os.environ.get("HYC_NVR_LIVE_CHANNEL") or str(ISAPI_LIVE_CHANNEL)).strip()
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = ISAPI_LIVE_CHANNEL
    return n if n > 0 else ISAPI_LIVE_CHANNEL


def go2rtc_src() -> str:
    raw = (os.environ.get("HYC_GO2RTC_SRC") or GO2RTC_SRC_DEFAULT).strip()
    if raw.lower() in {"0", "off", "false", "no", "-"}:
        return ""
    return raw


def go2rtc_hls_url() -> str:
    src = go2rtc_src()
    if not src:
        return ""
    base = (os.environ.get("HYC_GO2RTC_URL") or GO2RTC_DEFAULT).strip().rstrip("/")
    return f"{base}/api/stream.m3u8?src={src}"


def live_url() -> str:
    """NVR live pass-through URL for Cam 5."""
    explicit = (os.environ.get("HYC_NVR_LIVE_URL") or os.environ.get("HYC_CAM5_LIVE_URL") or "").strip()
    if explicit:
        return explicit
    hls = go2rtc_hls_url()
    if hls:
        return hls
    base = nvr_base()
    if not base:
        return ""
    return f"{base}/ISAPI/Streaming/channels/{live_channel()}/httpPreview"


def allowed_upstream(url: str) -> bool:
    live = live_url()
    if not live or not url:
        return False
    a = urlparse(url)
    b = urlparse(live)
    host_ok = bool(a.hostname) and a.hostname == b.hostname
    return a.scheme in ("http", "https") and host_ok


def stream_kind(url: str | None = None) -> str:
    u = (url or live_url()).lower()
    if not u:
        return "hls"
    if ".m3u8" in u or "mpegurl" in u or "/hls" in u:
        return "hls"
    if u.endswith(".mp4") or "stream.mp4" in u or "/mse" in u:
        return "mp4"
    if "httpreview" in u or "mjpeg" in u or "multipart" in u:
        return "mjpeg"
    return "hls"


def _opener(url: str):
    user = nvr_user()
    password = nvr_password()
    if not url or not user:
        return None
    origin = nvr_base() or "{0.scheme}://{0.netloc}".format(urlparse(url))
    mgr = HTTPPasswordMgrWithDefaultRealm()
    mgr.add_password(None, origin, user, password)
    mgr.add_password(None, url, user, password)
    return build_opener(HTTPDigestAuthHandler(mgr))


def _format_as_at(dt: datetime) -> str:
    return dt.astimezone(SAST).strftime("%H:%M")


def open_live(url: str | None = None, timeout: float | None = None):
    """Open the NVR live feed. Returns (fp, content_type, err). Caller closes fp."""
    target = (url or live_url()).strip()
    if not target:
        return None, "", "HYC live URL not set (go2rtc / HYC_NVR_LIVE_URL / HYC_NVR_HOST)"
    req = Request(target, headers={"User-Agent": UA})
    opener = _opener(target)
    try:
        if opener is not None:
            resp = opener.open(req, timeout=timeout)
        else:
            resp = urlopen(req, timeout=timeout, context=ssl._create_unverified_context())
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
        return resp, ctype, ""
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return None, "", str(exc)[:200]


def probe_live() -> tuple[bool, str]:
    fp, _ctype, err = open_live(timeout=8)
    if fp is None:
        return False, err or "nvr live unreachable"
    try:
        peek = fp.read(32)
    except (OSError, TimeoutError) as exc:
        try:
            fp.close()
        except OSError:
            pass
        return False, str(exc)[:200]
    try:
        fp.close()
    except OSError:
        pass
    if not peek:
        return False, "empty nvr live feed"
    return True, ""


def rewrite_hls_playlist(text: str, playlist_url: str) -> str:
    """Point relative HLS URIs back through our pass-through."""
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            lines.append(raw)
            continue
        abs_u = urljoin(playlist_url, line)
        lines.append(LIVE_SRC + "?u=" + quote(abs_u, safe=""))
    return "\n".join(lines) + "\n"


def status_payload(*, allowed: bool, can_toggle: bool) -> dict:
    visible = is_visible()
    url = live_url()
    kind = stream_kind(url)
    live = False
    err = ""
    as_at = None
    last_iso = None
    if allowed:
        live, err = probe_live()
        if live:
            dt = datetime.now(timezone.utc)
            last_iso = dt.isoformat().replace("+00:00", "Z")
            as_at = _format_as_at(dt)
    else:
        err = "hidden"
    return {
        "ok": bool(allowed and live),
        "kind": KIND,
        "reason": "pass-through",
        "live": bool(allowed and live),
        "visible": visible,
        "allowed": allowed,
        "can_toggle": can_toggle,
        "label": LABEL,
        "channel": CAM_NO,
        "isapi_channel": live_channel(),
        "stream_kind": kind,
        "src": LIVE_SRC,
        "stream_url": LIVE_SRC if allowed else "",
        "interval_sec": 0,
        "last_modified": last_iso,
        "as_at": as_at,
        "err": err or None,
    }
