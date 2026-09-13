"""ZVYC cam live check: real HLS only. Skyline's 4040 loop is not live."""
from __future__ import annotations

import re

_OFFLINE_RE = re.compile(r"4040livic|4040\.jpg|/4040(?:livic)?", re.I)


def playlist_is_actual_live(body: str) -> bool:
    """True only when the HLS playlist is a current, non-placeholder broadcast."""
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
