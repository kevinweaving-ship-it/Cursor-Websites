"""Arial source registry: tools/listeners feed sites. Sources stay separate."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_PATHS = (
    Path(os.getenv("ARIAL_SOURCES_REGISTRY") or ""),
    Path("/opt/arial-sources/registry.json"),
    Path(__file__).resolve().parent / "registry.json",
)


def registry_path() -> Path:
    for p in DEFAULT_PATHS:
        if p and str(p) and p.is_file():
            return p
    return Path(__file__).resolve().parent / "registry.json"


def load_registry() -> dict[str, Any]:
    path = registry_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {"version": 0, "sources": {}, "sites": {}}
    data["_path"] = str(path)
    return data


def site_sources(site_id: str) -> dict[str, Any]:
    reg = load_registry()
    site = (reg.get("sites") or {}).get(site_id) or {}
    catalog = reg.get("sources") or {}
    uses = []
    for item in site.get("uses") or []:
        src_id = item.get("source")
        defn = dict(catalog.get(src_id) or {})
        uses.append({**defn, **item, "source": src_id})
    return {
        "ok": True,
        "rule": reg.get("rule"),
        "site": {"id": site_id, "url": site.get("url"), "label": site.get("label")},
        "uses": uses,
    }
