"""URLs the server can monitor without Page Indexing example lists."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from .config import SITE
from .probe_live import load_sitemap_urls

_SEED = Path(__file__).with_name("watchlist_seed.json")

PREFIX_QUOTA = {
    "/sailor/": 8,
    "/regatta/": 8,
    "/class/": 6,
    "/club/": 6,
    "/event/": 4,
    "/events/": 4,
}


def _norm(url: str) -> str:
    return url.strip()


def load_seed() -> dict:
    if not _SEED.is_file():
        return {"core": [SITE + "/"], "prior_real": []}
    return json.loads(_SEED.read_text(encoding="utf-8"))


def persist_reals(
    dest: Path, urls: list[str], sitemap: set[str] | None = None
) -> None:
    """Keep only current REAL URLs that are still in the live sitemap.

    Dead aliases (404/301 not in sitemap) must not re-seed tomorrow's watchlist.
    """
    keep: list[str] = []
    seen: set[str] = set()
    for u in urls:
        u = _norm(u)
        if not u or u in seen:
            continue
        if sitemap is not None and u not in sitemap:
            continue
        seen.add(u)
        keep.append(u)
    dest.write_text(json.dumps({"prior_real": keep}, indent=2) + "\n", encoding="utf-8")


def _sitemap_sample(sitemap: set[str]) -> list[str]:
    buckets: dict[str, list[str]] = {k: [] for k in PREFIX_QUOTA}
    other: list[str] = []
    for u in sorted(sitemap):
        path = urlparse(u).path or "/"
        hit = False
        for prefix, n in PREFIX_QUOTA.items():
            if path.startswith(prefix) and len(buckets[prefix]) < n:
                buckets[prefix].append(u)
                hit = True
                break
        if not hit and len(other) < 6:
            other.append(u)
    out: list[str] = []
    for v in buckets.values():
        out.extend(v)
    out.extend(other)
    return out


def build_watchlist(data_root: Path, sitemap: set[str], budget: int) -> list[str]:
    seed = load_seed()
    yesterday = data_root / "watchlist_real.json"
    extra = []
    if yesterday.is_file():
        extra = json.loads(yesterday.read_text(encoding="utf-8")).get("prior_real") or []
    ordered = []
    seen = set()
    for u in (
        list(seed.get("core") or [])
        + list(seed.get("prior_real") or [])
        + extra
        + _sitemap_sample(sitemap)
    ):
        u = _norm(u)
        if not u or u in seen:
            continue
        seen.add(u)
        ordered.append(u)
        if len(ordered) >= budget:
            break
    return ordered
