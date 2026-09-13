#!/usr/bin/env python3
"""Surgical live api.py patch: ZVYC cam live/still stamp headers + status.

Marker: ZVYC_CAM_STAMP_v1
Never overwrite live api.py with the repo copy.
"""
from __future__ import annotations

from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")
MARKER = "ZVYC_CAM_STAMP_v1"

OLD_MEM = '''_ZVYC_GRAB_MEM = {"t": 0.0, "jpg": b""}
_ZVYC_GRAB_TTL_SEC = 8.0
'''

NEW_MEM = '''_ZVYC_GRAB_MEM = {"t": 0.0, "jpg": b"", "live": False, "still_at": 0.0, "fail_t": 0.0}
_ZVYC_GRAB_TTL_SEC = 8.0
_ZVYC_GRAB_FAIL_TTL_SEC = 20.0
# ''' + MARKER + '''
'''

OLD_GRAB = r'''def _zvyc_live_cam_frame_jpeg(explicit_token: str = "", fresh: bool = False) -> bytes:
    """Grab one JPEG after ~2s of play. Persist last good still; never the blue 4040 card."""
    last_path = "/var/www/sailingsa/assets/adverts/mm-cape-classic/zvyc-live-cam.jpg"
    tmp_path = last_path + ".tmp"

    def _read_last() -> bytes:
        try:
            with open(last_path, "rb") as f:
                disk = f.read()
            if disk[:2] == b"\xff\xd8":
                return disk
        except Exception:
            pass
        return b""

    now = time.time()
    if not fresh:
        with _ZVYC_GRAB_LOCK:
            cached = _ZVYC_GRAB_MEM.get("jpg") or b""
            if cached[:2] == b"\xff\xd8" and now - float(_ZVYC_GRAB_MEM.get("t") or 0) < _ZVYC_GRAB_TTL_SEC:
                return cached
    url = _zvyc_live_cam_stream_url(explicit_token)
    if url:
        ua = _ZVYC_CAM_FETCH_HEADERS.get("User-Agent") or "Mozilla/5.0"
        headers = f"Referer: {_ZVYC_LIVE_CAM_PAGE}\r\nUser-Agent: {ua}\r\n"
        cmd = [
            _ZVYC_FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-headers",
            headers,
            "-i",
            url,
            "-ss",
            "2",
            "-frames:v",
            "1",
            "-q:v",
            "5",
            "-f",
            "image2",
            "pipe:1",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=20)
            jpg = proc.stdout or b""
            if proc.returncode == 0 and jpg[:2] == b"\xff\xd8":
                try:
                    os.makedirs(os.path.dirname(last_path), exist_ok=True)
                    with open(tmp_path, "wb") as f:
                        f.write(jpg)
                    os.replace(tmp_path, last_path)
                except Exception as e:
                    print(f"[zvyc_live_cam] save still failed: {e}", flush=True)
                with _ZVYC_GRAB_LOCK:
                    _ZVYC_GRAB_MEM["t"] = time.time()
                    _ZVYC_GRAB_MEM["jpg"] = jpg
                return jpg
            print(f"[zvyc_live_cam] grab failed rc={proc.returncode}", flush=True)
        except Exception as e:
            print(f"[zvyc_live_cam] grab failed: {e}", flush=True)
    disk = _read_last()
    if disk:
        with _ZVYC_GRAB_LOCK:
            _ZVYC_GRAB_MEM["t"] = time.time()
            _ZVYC_GRAB_MEM["jpg"] = disk
        return disk
    with _ZVYC_GRAB_LOCK:
        cached = _ZVYC_GRAB_MEM.get("jpg") or b""
        if cached[:2] == b"\xff\xd8":
            return cached
    return b""
'''

NEW_GRAB = r'''def _zvyc_cam_still_path() -> str:
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


def _zvyc_live_cam_frame_jpeg(explicit_token: str = "", fresh: bool = False) -> bytes:
    """Grab one JPEG after ~2s of play. Persist last good still; never the blue 4040 card."""
    last_path = _zvyc_cam_still_path()
    tmp_path = last_path + ".tmp"

    def _read_last() -> bytes:
        try:
            with open(last_path, "rb") as f:
                disk = f.read()
            if disk[:2] == b"\xff\xd8":
                return disk
        except Exception:
            pass
        return b""

    def _mark(live: bool, jpg: bytes, still_at: float | None = None) -> None:
        now = time.time()
        with _ZVYC_GRAB_LOCK:
            if jpg[:2] == b"\xff\xd8":
                _ZVYC_GRAB_MEM["jpg"] = jpg
            _ZVYC_GRAB_MEM["live"] = bool(live)
            _ZVYC_GRAB_MEM["still_at"] = float(still_at or (now if live else _zvyc_cam_still_mtime()))
            if live:
                _ZVYC_GRAB_MEM["t"] = now
                _ZVYC_GRAB_MEM["fail_t"] = 0.0
            else:
                _ZVYC_GRAB_MEM["fail_t"] = now

    now = time.time()
    if not fresh:
        with _ZVYC_GRAB_LOCK:
            cached = _ZVYC_GRAB_MEM.get("jpg") or b""
            live = bool(_ZVYC_GRAB_MEM.get("live"))
            t = float(_ZVYC_GRAB_MEM.get("t") or 0)
            fail_t = float(_ZVYC_GRAB_MEM.get("fail_t") or 0)
            if cached[:2] == b"\xff\xd8" and live and now - t < _ZVYC_GRAB_TTL_SEC:
                return cached
            if cached[:2] == b"\xff\xd8" and not live and fail_t and now - fail_t < _ZVYC_GRAB_FAIL_TTL_SEC:
                return cached
    url = _zvyc_live_cam_stream_url(explicit_token)
    if url:
        ua = _ZVYC_CAM_FETCH_HEADERS.get("User-Agent") or "Mozilla/5.0"
        headers = f"Referer: {_ZVYC_LIVE_CAM_PAGE}\r\nUser-Agent: {ua}\r\n"
        cmd = [
            _ZVYC_FFMPEG,
            "-hide_banner",
            "-loglevel",
            "error",
            "-headers",
            headers,
            "-i",
            url,
            "-ss",
            "2",
            "-frames:v",
            "1",
            "-q:v",
            "5",
            "-f",
            "image2",
            "pipe:1",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=20)
            jpg = proc.stdout or b""
            if proc.returncode == 0 and jpg[:2] == b"\xff\xd8":
                try:
                    os.makedirs(os.path.dirname(last_path), exist_ok=True)
                    with open(tmp_path, "wb") as f:
                        f.write(jpg)
                    os.replace(tmp_path, last_path)
                except Exception as e:
                    print(f"[zvyc_live_cam] save still failed: {e}", flush=True)
                _mark(True, jpg)
                return jpg
            print(f"[zvyc_live_cam] grab failed rc={proc.returncode}", flush=True)
        except Exception as e:
            print(f"[zvyc_live_cam] grab failed: {e}", flush=True)
    disk = _read_last()
    if disk:
        _mark(False, disk, _zvyc_cam_still_mtime())
        return disk
    with _ZVYC_GRAB_LOCK:
        cached = _ZVYC_GRAB_MEM.get("jpg") or b""
        if cached[:2] == b"\xff\xd8":
            _ZVYC_GRAB_MEM["live"] = False
            return cached
    return b""
'''

OLD_THUMB = '''@app.get("/api/regatta/{regatta_id}/zvyc-live-cam-thumb")
async def api_zvyc_live_cam_thumb(
    regatta_id: str, a: str = Query(""), fresh: int = Query(0)
):
    """Return a live-feed screenshot after ~2s of play. Do not store the feed."""
    if str(regatta_id or "").strip() != _CAPE_CLASSIC_MM_REGATTA_ID:
        raise HTTPException(status_code=404, detail="not found")
    import asyncio

    jpg = await asyncio.to_thread(_zvyc_live_cam_frame_jpeg, a, bool(fresh))
    if jpg[:2] == b"\\xff\\xd8":
        return Response(
            content=jpg,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-store"},
        )
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
'''

NEW_THUMB = '''@app.get("/api/regatta/{regatta_id}/zvyc-live-cam-status")
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


@app.get("/api/regatta/{regatta_id}/zvyc-live-cam-thumb")
async def api_zvyc_live_cam_thumb(
    regatta_id: str, a: str = Query(""), fresh: int = Query(0)
):
    """Return a live-feed screenshot after ~2s of play. Do not store the feed."""
    if str(regatta_id or "").strip() != _CAPE_CLASSIC_MM_REGATTA_ID:
        raise HTTPException(status_code=404, detail="not found")
    import asyncio

    jpg = await asyncio.to_thread(_zvyc_live_cam_frame_jpeg, a, bool(fresh))
    headers = _zvyc_cam_stamp_headers()
    if jpg[:2] == b"\\xff\\xd8":
        return Response(
            content=jpg,
            media_type="image/jpeg",
            headers=headers,
        )
    return Response(status_code=204, headers=headers)
'''


def main() -> int:
    text = API.read_text(encoding="utf-8")
    if MARKER in text:
        print("ALREADY_PATCHED")
        if "mm-lipton-reels-card.js?v=mmr126" in text:
            text = text.replace("mm-lipton-reels-card.js?v=mmr126", "mm-lipton-reels-card.js?v=mmr127", 1)
            API.write_text(text, encoding="utf-8")
            print("BUMPED mmr127")
        return 0
    if OLD_MEM not in text:
        raise SystemExit("mem block missing")
    if OLD_GRAB not in text:
        raise SystemExit("grab fn missing")
    if OLD_THUMB not in text:
        raise SystemExit("thumb route missing")
    text = text.replace(OLD_MEM, NEW_MEM, 1)
    text = text.replace(OLD_GRAB, NEW_GRAB, 1)
    text = text.replace(OLD_THUMB, NEW_THUMB, 1)
    if "mm-lipton-reels-card.js?v=mmr126" not in text:
        raise SystemExit("mmr126 missing")
    text = text.replace("mm-lipton-reels-card.js?v=mmr126", "mm-lipton-reels-card.js?v=mmr127", 1)
    if MARKER not in text:
        raise SystemExit("marker failed")
    API.write_text(text, encoding="utf-8")
    print("PATCHED", API, "bytes", API.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
