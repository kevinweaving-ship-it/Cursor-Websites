"""URLs the server can monitor without Page Indexing example lists."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from .config import SITE

_SEED = Path(__file__).with_name("watchlist_seed.json")

PREFIX_QUOTA = {
    "/sailor/": 8,
    "/regatta/": 12,
    "/class/": 6,
    "/club/": 6,
    "/event/": 4,
    "/events/": 4,
}

# Dated public event slugs /regatta/YYYY-MM-DD-...
_DATED_REGATTA = re.compile(r"^/regatta/(\d{4}-\d{2}-\d{2})-")

# Always inspect these even when they fall outside the newest-dated window.
FLAGSHIP_PATHS = (
    "/",
    "/events",
    "/regatta/2026-09-13-zvyc-cape-classic",
    "/regatta/2026-08-29-lipton-challenge-cup",
)
RECENT_EVENT_LIMIT = 8


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


def _regatta_sort_key(url: str) -> tuple:
    """Newest dated /regatta/YYYY-MM-DD-* first; undated numeric IDs last."""
    path = urlparse(url).path or "/"
    m = _DATED_REGATTA.match(path)
    if m:
        try:
            d = date.fromisoformat(m.group(1))
            return (0, -d.toordinal(), path)
        except ValueError:
            pass
    return (1, 0, path)


def _sitemap_sample(sitemap: set[str]) -> list[str]:
    buckets: dict[str, list[str]] = {k: [] for k in PREFIX_QUOTA}
    other: list[str] = []
    regatta_sorted = sorted(
        (u for u in sitemap if (urlparse(u).path or "/").startswith("/regatta/")),
        key=_regatta_sort_key,
    )
    rest = sorted(u for u in sitemap if u not in set(regatta_sorted))
    for u in list(regatta_sorted) + rest:
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


def priority_event_urls(sitemap: set[str] | None = None, *, today: date | None = None) -> list[str]:
    """Hubs + flagship + newest dated /regatta URLs. Never the sailor catalogue."""
    today = today or date.today()
    src = set(sitemap or [])
    out: list[str] = []
    seen: set[str] = set()

    def _add(url: str) -> None:
        u = _norm(url)
        if not u or u in seen:
            return
        seen.add(u)
        out.append(u)

    for path in FLAGSHIP_PATHS:
        _add(SITE.rstrip("/") + path)
    dated: list[tuple[date, str]] = []
    for u in src:
        path = urlparse(u).path or "/"
        m = _DATED_REGATTA.match(path)
        if not m:
            continue
        try:
            d = date.fromisoformat(m.group(1))
        except ValueError:
            continue
        dated.append((d, u))
    dated.sort(key=lambda row: row[0], reverse=True)
    upcoming = [u for d, u in dated if d >= today]
    recent = [u for d, u in dated if d < today][:RECENT_EVENT_LIMIT]
    for u in upcoming + recent:
        _add(u)
    return out


def build_watchlist(data_root: Path, sitemap: set[str], budget: int) -> list[str]:
    seed = load_seed()
    yesterday = data_root / "watchlist_real.json"
    extra = []
    if yesterday.is_file():
        extra = json.loads(yesterday.read_text(encoding="utf-8")).get("prior_real") or []
    # Core + current sitemap sample first so 2026 event URLs are inspected.
    # Historic REAL junk (404/301 aliases) is last and dropped if not in sitemap.
    seed_prior = [
        u
        for u in (seed.get("prior_real") or [])
        if not sitemap or _norm(u) in sitemap
    ]
    ordered = []
    seen = set()
    for u in (
        priority_event_urls(sitemap)
        + list(seed.get("core") or [])
        + _sitemap_sample(sitemap)
        + extra
        + seed_prior
    ):
        u = _norm(u)
        if not u or u in seen:
            continue
        seen.add(u)
        ordered.append(u)
        if len(ordered) >= budget:
            break
    return ordered
