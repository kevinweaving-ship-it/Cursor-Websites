"""ZVYC cam live check: real HLS only. Skyline's 4040 loop is not live."""
from __future__ import annotations

import re

# Webcam 4040's live segments are named 4040livic-*.ts. That is live, not the
# offline card. Offline is 4040.jpg / copyright_violation.
_OFFLINE_RE = re.compile(r"4040\.jpg|copyright_violation|/temp/4040", re.I)


def playlist_is_actual_live(body: str) -> bool:
    """True when HLS is a current broadcast. 4040livic is the ZVYC live cam."""
    text = str(body or "")
    if "#EXTM3U" not in text:
        return False
    if "#EXT-X-ENDLIST" in text:
        return False
    if _OFFLINE_RE.search(text):
        return False
    if "#EXTINF" not in text:
        return False
    return True


def playlist_offline_reason(body: str, status_code: int | None = None) -> str:
    if status_code is not None and int(status_code) >= 400:
        return f"http_{int(status_code)}"
    text = str(body or "")
    if not text:
        return "empty"
    if "#EXTM3U" not in text:
        return "not_playlist"
    if _OFFLINE_RE.search(text):
        return "placeholder_4040"
    if "#EXT-X-ENDLIST" in text:
        return "ended"
    if "#EXTINF" not in text:
        return "no_segments"
    if playlist_is_actual_live(text):
        return "hls"
    return "not_live"
