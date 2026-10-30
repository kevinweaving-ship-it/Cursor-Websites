"""Parent-truth Event Logo helpers.

Rule: the parent /regatta/{id} left header is truth. When that slot is a named
Event Logo, Open / class marks are superseded on cards and on single-class
parent pages. Header JSON left is the same source gold api.py uses.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional
from urllib.parse import unquote

HEADER_ICONS_PATH = os.environ.get(
    "SAILINGS_HEADER_ICONS",
    "/var/www/sailingsa/data/wc_regatta_header_icons.json",
)


def is_event_logo_path(path: str) -> bool:
    raw = str(path or "").split("?", 1)[0]
    try:
        raw = unquote(raw)
    except Exception:
        pass
    return "/artwork/event logo/" in raw.lower()


def is_class_logo_path(path: str) -> bool:
    raw = str(path or "").split("?", 1)[0]
    try:
        raw = unquote(raw)
    except Exception:
        pass
    return "/artwork/class logo/" in raw.lower()


def header_left_url(regatta_id: str, header_path: Optional[str] = None) -> str:
    rid = str(regatta_id or "").strip()
    if not rid:
        return ""
    path = header_path or HEADER_ICONS_PATH
    try:
        if not os.path.isfile(path):
            return ""
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return ""
    if not isinstance(data, dict):
        return ""
    raw = data.get(rid)
    if isinstance(raw, dict):
        return str(raw.get("left") or "").strip()
    return str(raw or "").strip()


def parent_event_logo_url(
    regatta_id: str,
    series: Optional[dict[str, Any]] = None,
    header_path: Optional[str] = None,
) -> str:
    """Event Logo only. Never return a Class Logo path."""
    left = header_left_url(regatta_id, header_path=header_path)
    if is_event_logo_path(left):
        return left
    series_logo = str((series or {}).get("logo") or "").strip()
    if is_event_logo_path(series_logo):
        return series_logo
    return ""
