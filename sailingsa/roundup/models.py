"""Shared helpers for fact-sheet tokens and stable JSON."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


def stable_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def content_hash(data: Any) -> str:
    return hashlib.sha256(stable_json(data).encode("utf-8")).hexdigest()


def slugify(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[^\w\s\-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return re.sub(r"-{2,}", "-", text).strip("-")


def clean_spaces(value: str) -> str:
    return re.sub(r" {2,}", " ", (value or "").replace("\xa0", " ")).strip()


def person_tokens(*names: str | None) -> list[str]:
    out: list[str] = []
    for name in names:
        text = clean_spaces(name or "")
        if text:
            out.append(text)
    return out


def format_nett(value) -> str | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return clean_spaces(str(value))
    if number.is_integer():
        return str(int(number))
    text = f"{number:.1f}".rstrip("0").rstrip(".")
    return text
