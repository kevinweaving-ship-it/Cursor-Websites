#!/usr/bin/env python3
"""Read-only client for SailingSA's sailor Media-tab tool.

Uses GET /api/member/{sa_id}/public-mentions — the same source as
Timothy Weaving (21172) and Joshua Keytel (13522) profile Media tabs.
Does not write to SailingSA.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import urllib.parse
import urllib.request

BASE = "https://sailingsa.co.za"
UA = {"User-Agent": "SailingRoundupResearch/1.0"}
REFERENCE_SAILORS = (
    ("21172", "Timothy Weaving"),
    ("13522", "Joshua Keytel"),
)


def _get_json(url: str, timeout: int = 25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def fetch_mentions(sa_id) -> dict:
    sid = str(sa_id).strip()
    if not sid.isdigit():
        return {"sa_id": sid, "items": [], "error": "sa_id must be numeric"}
    try:
        data = _get_json(f"{BASE}/api/member/{sid}/public-mentions")
    except Exception as exc:
        return {"sa_id": sid, "items": [], "error": str(exc)[:200]}
    items = data.get("items") if isinstance(data, dict) else []
    return {
        "sa_id": sid,
        "media_score": data.get("media_score") if isinstance(data, dict) else None,
        "items": items or [],
    }


def search_sailor(name: str) -> list:
    q = urllib.parse.quote((name or "").strip())
    if not q:
        return []
    try:
        data = _get_json(f"{BASE}/api/search?q={q}")
    except Exception:
        return []
    rows = data if isinstance(data, list) else []
    out = []
    for row in rows:
        sid = str(row.get("sas_id") or "").strip()
        if sid.isdigit():
            out.append(
                {
                    "sa_id": sid,
                    "name": " ".join(
                        x for x in (row.get("first_names"), row.get("surname")) if x
                    ).strip(),
                    "club": row.get("club"),
                }
            )
    return out


def parse_day(value) -> dt.date | None:
    if not value:
        return None
    text = str(value)[:10]
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return None


def mention_text(item: dict) -> str:
    return " ".join(
        str(item.get(key) or "")
        for key in ("headline", "snippet", "title", "description", "source", "url")
    ).lower()


def filter_for_event(items, start: dt.date, end: dt.date, terms: list[str], lookback_days: int = 2):
    """Keep mentions published from shortly before the event through issue week."""
    window_start = start - dt.timedelta(days=lookback_days)
    window_end = end + dt.timedelta(days=10)
    wanted = [t.lower() for t in terms if t and len(t) > 2]
    kept = []
    for item in items or []:
        day = parse_day(item.get("published_at") or item.get("date_iso"))
        if day and (day < window_start or day > window_end):
            continue
        text = mention_text(item)
        hits = sum(1 for t in wanted if t in text)
        # Dated + on-topic, or undated but clearly about this event.
        if day and hits >= 1:
            kept.append(item)
        elif not day and hits >= 2:
            kept.append(item)
    return kept


def collect_for_sailors(sa_ids, start: dt.date, end: dt.date, terms: list[str]) -> dict:
    sailors = []
    matched = []
    seen = set()
    for sid in sa_ids:
        pack = fetch_mentions(sid)
        sailors.append(
            {
                "sa_id": pack.get("sa_id"),
                "media_score": pack.get("media_score"),
                "item_count": len(pack.get("items") or []),
                "error": pack.get("error"),
            }
        )
        for item in filter_for_event(pack.get("items") or [], start, end, terms):
            url = (item.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            matched.append({"sa_id": str(sid), **item})
    return {"sailors": sailors, "matched": matched}


def check_reference_sailors() -> dict:
    """Sanity-check the Media-tab tool against Tim and Josh Keytel."""
    out = []
    for sid, name in REFERENCE_SAILORS:
        pack = fetch_mentions(sid)
        items = pack.get("items") or []
        platforms = {}
        for item in items:
            host = urllib.parse.urlparse(item.get("url") or "").netloc.lower().removeprefix("www.")
            key = host.split(":")[0] or (item.get("source") or "unknown")
            platforms[key] = platforms.get(key, 0) + 1
        out.append(
            {
                "name": name,
                "sa_id": sid,
                "media_score": pack.get("media_score"),
                "items": len(items),
                "error": pack.get("error"),
                "platforms": platforms,
                "latest": [
                    {
                        "published_at": it.get("published_at"),
                        "source": it.get("source"),
                        "headline": (it.get("headline") or "")[:120],
                        "url": it.get("url"),
                    }
                    for it in items[:5]
                ],
            }
        )
    return {"tool": "GET /api/member/{sa_id}/public-mentions", "sailors": out}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sa-id", action="append", default=[])
    p.add_argument("--check-reference", action="store_true")
    args = p.parse_args()
    if args.check_reference or not args.sa_id:
        print(json.dumps(check_reference_sailors(), indent=2, ensure_ascii=False))
    else:
        print(json.dumps([fetch_mentions(s) for s in args.sa_id], indent=2, ensure_ascii=False))
