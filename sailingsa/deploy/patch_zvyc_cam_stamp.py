#!/usr/bin/env python3
"""Patch live api.py: probe the real ZVYC HLS feed before saying no live."""
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

OLD_STAMP = '''# ZVYC_CAM_STAMP_v1


def _zvyc_cam_still_path() -> str:
    return "/var/www/sailingsa/assets/adverts/mm-cape-classic/zvyc-live-cam.jpg"


def _zvyc_cam_still_mtime() -> float:
    try:
        return float(os.path.getmtime(_zvyc_cam_still_path()))
    except Exception:
        return 0.0


def _zvyc_cam_sast_iso(ts: float) -> str:
    if not ts:
        return ""
    from datetime import timezone as _tz

    return datetime.fromtimestamp(float(ts), tz=_tz(timedelta(hours=2))).isoformat()


def _zvyc_cam_stamp_headers() -> dict:
    from email.utils import formatdate

    with _ZVYC_GRAB_LOCK:
        live = bool(_ZVYC_GRAB_MEM.get("live"))
        still_at = float(_ZVYC_GRAB_MEM.get("still_at") or 0)
        t = float(_ZVYC_GRAB_MEM.get("t") or 0)
        if live and t and time.time() - t > 90:
            live = False
    if not still_at:
        still_at = _zvyc_cam_still_mtime()
    headers = {
        "Cache-Control": "no-store",
        "X-Zvyc-Cam-Live": "1" if live else "0",
        "Access-Control-Expose-Headers": "X-Zvyc-Cam-Live, X-Zvyc-Cam-Still-At, Last-Modified",
    }
    if still_at:
        headers["X-Zvyc-Cam-Still-At"] = _zvyc_cam_sast_iso(still_at)
        headers["Last-Modified"] = formatdate(still_at, usegmt=True)
    return headers
'''

NEW_STAMP = '''# ZVYC_CAM_STAMP_v2
_ZVYC_CAM_STATE_PATH = "/var/www/sailingsa/api/data/zvyc_cam_stamp.json"
_ZVYC_CAM_OFFLINE_RE = re.compile(r"4040livic|4040[.]jpg|/4040", re.I)
_ZVYC_CAM_PROBE_TTL_SEC = 12.0


def _zvyc_cam_still_path() -> str:
    return "/var/www/sailingsa/assets/adverts/mm-cape-classic/zvyc-live-cam.jpg"


def _zvyc_cam_still_mtime() -> float:
    try:
        return float(os.path.getmtime(_zvyc_cam_still_path()))
    except Exception:
        return 0.0


def _zvyc_cam_sast_iso(ts: float) -> str:
    if not ts:
        return ""
    from datetime import timezone as _tz

    return datetime.fromtimestamp(float(ts), tz=_tz(timedelta(hours=2))).isoformat()


def _zvyc_cam_playlist_is_live(body: str) -> bool:
    text = str(body or "")
    if "#EXTM3U" not in text:
        return False
    if "#EXT-X-ENDLIST" in text:
        return False
    if _ZVYC_CAM_OFFLINE_RE.search(text):
        return False
    if "#EXTINF" not in text:
        return False
    return True


def _zvyc_cam_load_state() -> dict:
    try:
        with open(_ZVYC_CAM_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _zvyc_cam_save_state(state: dict) -> None:
    path = _ZVYC_CAM_STATE_PATH
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, path)


def _zvyc_cam_last_live_ts() -> float:
    with _ZVYC_GRAB_LOCK:
        ts = float(_ZVYC_GRAB_MEM.get("last_live_at") or 0)
    if ts:
        return ts
    st = _zvyc_cam_load_state()
    try:
        ts = float(st.get("last_live_at") or 0)
    except Exception:
        ts = 0.0
    if not ts:
        ts = _zvyc_cam_still_mtime()
    if ts:
        with _ZVYC_GRAB_LOCK:
            _ZVYC_GRAB_MEM["last_live_at"] = ts
    return ts


def _zvyc_cam_remember_live(now: float | None = None) -> None:
    ts = float(now or time.time())
    with _ZVYC_GRAB_LOCK:
        _ZVYC_GRAB_MEM["last_live_at"] = ts
        _ZVYC_GRAB_MEM["live"] = True
        _ZVYC_GRAB_MEM["t"] = ts
        _ZVYC_GRAB_MEM["fail_t"] = 0.0
    try:
        st = _zvyc_cam_load_state()
        st["last_live_at"] = ts
        st["last_live_iso"] = _zvyc_cam_sast_iso(ts)
        _zvyc_cam_save_state(st)
    except Exception as e:
        print(f"[zvyc_live_cam] save stamp failed: {e}", flush=True)


def _zvyc_cam_probe_live(explicit_token: str = "") -> bool:
    """Fetch the upstream playlist. 4040 placeholder is not a live feed."""
    now = time.time()
    with _ZVYC_GRAB_LOCK:
        probe_t = float(_ZVYC_GRAB_MEM.get("probe_t") or 0)
        if probe_t and now - probe_t < _ZVYC_CAM_PROBE_TTL_SEC:
            return bool(_ZVYC_GRAB_MEM.get("live"))
        was_live = bool(_ZVYC_GRAB_MEM.get("live"))
        last_t = float(_ZVYC_GRAB_MEM.get("t") or 0)
    url = _zvyc_live_cam_stream_url(explicit_token)
    live = False
    reason = "no_url"
    body = ""
    status_code = 0
    if url:
        try:
            with httpx.Client(
                timeout=8.0, follow_redirects=True, headers=_ZVYC_CAM_FETCH_HEADERS
            ) as client:
                resp = client.get(url)
            status_code = int(resp.status_code)
            body = resp.text or ""
            if status_code >= 400:
                reason = f"http_{status_code}"
            elif _zvyc_cam_playlist_is_live(body):
                live = True
                reason = "hls"
            elif _ZVYC_CAM_OFFLINE_RE.search(body):
                reason = "placeholder_4040"
            elif "#EXT-X-ENDLIST" in body:
                reason = "ended"
            elif "#EXTM3U" not in body:
                reason = "not_playlist"
            else:
                reason = "not_live"
        except Exception as e:
            reason = "error"
            print(f"[zvyc_live_cam] probe failed: {e}", flush=True)
            if was_live and last_t and now - last_t < 90:
                live = True
                reason = "error_keep"
    with _ZVYC_GRAB_LOCK:
        _ZVYC_GRAB_MEM["probe_t"] = now
        _ZVYC_GRAB_MEM["probe_reason"] = reason
        _ZVYC_GRAB_MEM["live"] = bool(live)
        if live:
            _ZVYC_GRAB_MEM["t"] = now
            _ZVYC_GRAB_MEM["fail_t"] = 0.0
        else:
            _ZVYC_GRAB_MEM["fail_t"] = now
    if live and reason != "error_keep":
        _zvyc_cam_remember_live(now)
    return bool(live)


def _zvyc_cam_stamp_headers() -> dict:
    from email.utils import formatdate

    with _ZVYC_GRAB_LOCK:
        live = bool(_ZVYC_GRAB_MEM.get("live"))
        still_at = float(_ZVYC_GRAB_MEM.get("still_at") or 0)
        t = float(_ZVYC_GRAB_MEM.get("t") or 0)
        if live and t and time.time() - t > 90:
            live = False
    if not still_at:
        still_at = _zvyc_cam_still_mtime()
    last_live = _zvyc_cam_last_live_ts()
    headers = {
        "Cache-Control": "no-store",
        "X-Zvyc-Cam-Live": "1" if live else "0",
        "Access-Control-Expose-Headers": (
            "X-Zvyc-Cam-Live, X-Zvyc-Cam-Still-At, X-Zvyc-Cam-Last-Live, Last-Modified"
        ),
    }
    if still_at:
        headers["X-Zvyc-Cam-Still-At"] = _zvyc_cam_sast_iso(still_at)
        headers["Last-Modified"] = formatdate(still_at, usegmt=True)
    if last_live:
        headers["X-Zvyc-Cam-Last-Live"] = _zvyc_cam_sast_iso(last_live)
    return headers
'''

OLD_MARK = '''            if live:
                _ZVYC_GRAB_MEM["t"] = now
                _ZVYC_GRAB_MEM["fail_t"] = 0.0
            else:
                _ZVYC_GRAB_MEM["fail_t"] = now
'''

NEW_MARK = '''            if live:
                _ZVYC_GRAB_MEM["t"] = now
                _ZVYC_GRAB_MEM["fail_t"] = 0.0
            else:
                _ZVYC_GRAB_MEM["fail_t"] = now
        if live:
            _zvyc_cam_remember_live(now)
'''

OLD_GRAB_URL = '''    url = _zvyc_live_cam_stream_url(explicit_token)
    if url:
'''

NEW_GRAB_URL = '''    if not _zvyc_cam_probe_live(explicit_token):
        disk = _read_last()
        if disk:
            _mark(False, disk, _zvyc_cam_still_mtime())
            return disk
        return b""
    url = _zvyc_live_cam_stream_url(explicit_token)
    if url:
'''

OLD_STATUS = '''@app.get("/api/regatta/{regatta_id}/zvyc-live-cam-status")
def api_zvyc_live_cam_status(regatta_id: str):
    """Cheap live/stale flag for the ZVYC cam stamp. No ffmpeg."""
    if str(regatta_id or "").strip() != _CAPE_CLASSIC_MM_REGATTA_ID:
        raise HTTPException(status_code=404, detail="not found")
    now = time.time()
    with _ZVYC_GRAB_LOCK:
        live = bool(_ZVYC_GRAB_MEM.get("live"))
        still_at = float(_ZVYC_GRAB_MEM.get("still_at") or 0)
        t = float(_ZVYC_GRAB_MEM.get("t") or 0)
        if live and t and now - t > 90:
            live = False
    if not still_at:
        still_at = _zvyc_cam_still_mtime()
    return {
        "live": live,
        "still_at": _zvyc_cam_sast_iso(still_at),
        "still_age_sec": int(now - still_at) if still_at else None,
    }
'''

NEW_STATUS = '''@app.get("/api/regatta/{regatta_id}/zvyc-live-cam-status")
def api_zvyc_live_cam_status(regatta_id: str):
    """Probe the actual HLS feed. 4040 placeholder is not live."""
    if str(regatta_id or "").strip() != _CAPE_CLASSIC_MM_REGATTA_ID:
        raise HTTPException(status_code=404, detail="not found")
    live = _zvyc_cam_probe_live()
    now = time.time()
    with _ZVYC_GRAB_LOCK:
        still_at = float(_ZVYC_GRAB_MEM.get("still_at") or 0)
        reason = str(_ZVYC_GRAB_MEM.get("probe_reason") or "")
    if not still_at:
        still_at = _zvyc_cam_still_mtime()
    last_live = _zvyc_cam_last_live_ts()
    return {
        "live": bool(live),
        "last_live_at": _zvyc_cam_sast_iso(last_live),
        "still_at": _zvyc_cam_sast_iso(still_at),
        "still_age_sec": int(now - still_at) if still_at else None,
        "reason": reason,
    }
'''


def apply(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "ZVYC_CAM_STAMP_v2" in text and "last_live_at" in text and "placeholder_4040" in text:
        print("already patched")
        changed = False
    else:
        for name, old, new in (
            ("stamp", OLD_STAMP, NEW_STAMP),
            ("mark", OLD_MARK, NEW_MARK),
            ("grab", OLD_GRAB_URL, NEW_GRAB_URL),
            ("status", OLD_STATUS, NEW_STATUS),
        ):
            if old not in text:
                raise SystemExit(f"block not found: {name}")
            text = text.replace(old, new, 1)
            print("replaced", name)
        changed = True
    if "mm-lipton-reels-card.js?v=mmr138" in text:
        text = text.replace(
            "mm-lipton-reels-card.js?v=mmr138",
            "mm-lipton-reels-card.js?v=mmr139",
            1,
        )
        print("bumped mmr139")
        changed = True
    if not changed:
        return
    path.write_text(text, encoding="utf-8")
    print("wrote", path)


if __name__ == "__main__":
    apply(API)
