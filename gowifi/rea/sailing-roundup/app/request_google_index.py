#!/usr/bin/env python3
"""Ask Google to crawl/index first-party URLs until the daily quota is used.

Priority: Weekend Roundup hub + latest + every issue, then high-traffic site
pages, then recent sitemap URLs. Stops as soon as Google returns quota-exhausted.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from google_index import notify_url_updated

BASE = "https://sailingsa.co.za"
UA = {"User-Agent": "SailingSA-IndexRequest/1.0"}
QUOTA_MARKERS = (
    "quota",
    "rateLimitExceeded",
    "dailyLimitExceeded",
    "RESOURCE_EXHAUSTED",
    "Quota exceeded",
    "userRateLimitExceeded",
)


def _get(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return getattr(resp, "status", 200), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:
        return 0, str(exc)


def _locs(xml: str) -> list[str]:
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)


def priority_urls() -> list[str]:
    """Newest roundup first, then high-traffic site pages, then recent sitemaps."""
    ordered: list[str] = []
    seen: set[str] = set()

    def add(url: str) -> None:
        url = (url or "").strip()
        if not url or url in seen:
            return
        if not url.startswith(BASE):
            return
        if any(x in url for x in ("/api/", "/auth/", "/admin/", "/login")):
            return
        seen.add(url)
        ordered.append(url)

    add(f"{BASE}/sailing-roundup/")
    add(f"{BASE}/sailing-roundup/latest/")
    st, xml = _get(f"{BASE}/sitemap-roundups.xml")
    if st == 200:
        issues = [u for u in _locs(xml) if "/issues/" in u]
        issues.sort(reverse=True)
        for url in issues:
            add(url)

    for url in (
        f"{BASE}/",
        f"{BASE}/about",
        f"{BASE}/stats",
        f"{BASE}/events",
        f"{BASE}/classes",
        f"{BASE}/clubs",
        f"{BASE}/sailors",
    ):
        add(url)

    for name in ("sitemap-regattas.xml", "sitemap-classes.xml", "sitemap-clubs.xml", "sitemap-core.xml"):
        st, xml = _get(f"{BASE}/{name}")
        if st != 200:
            continue
        for url in _locs(xml):
            add(url)
    return ordered


def _quota_hit(result: dict[str, Any]) -> bool:
    blob = json.dumps(result, ensure_ascii=False)
    status = result.get("status")
    if status in (429, 403) and any(m.lower() in blob.lower() for m in QUOTA_MARKERS):
        return True
    if status == 429:
        return True
    return any(m.lower() in blob.lower() for m in ("dailyLimitExceeded", "quotaexceeded"))


def request_until_quota(urls: list[str], *, pause: float = 0.35, limit: int = 200) -> dict[str, Any]:
    submitted: list[str] = []
    failed: list[dict[str, Any]] = []
    skipped = 0
    stop_reason = "completed_list"
    for url in urls[:limit]:
        result = notify_url_updated(url)
        if result.get("skipped"):
            skipped += 1
            stop_reason = result.get("reason") or "no_credentials"
            failed.append(result)
            break
        if result.get("ok"):
            submitted.append(url)
        else:
            failed.append(result)
            if _quota_hit(result):
                stop_reason = "quota_exhausted"
                break
            if result.get("status") == 401:
                stop_reason = "unauthorized"
                break
        time.sleep(pause)
    return {
        "ok": bool(submitted) or stop_reason == "quota_exhausted",
        "stop_reason": stop_reason,
        "submitted": len(submitted),
        "failed": len(failed),
        "skipped_no_credentials": skipped,
        "urls_submitted": submitted,
        "last_error": failed[-1] if failed else None,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--until-quota", action="store_true", help="Keep asking until Google hits the daily max")
    p.add_argument("--limit", type=int, default=200, help="Hard cap (Indexing API default daily quota is 200)")
    p.add_argument("--priority-only", action="store_true", help="Hub + latest + issue URLs only")
    args = p.parse_args()
    urls = priority_urls()
    if args.priority_only:
        urls = [u for u in urls if "/sailing-roundup" in u]
    if not args.until_quota:
        urls = urls[:20]
    stats = request_until_quota(urls, limit=args.limit)
    print(json.dumps(stats, indent=2))
    if stats.get("stop_reason") == "no_credentials":
        sys.exit(2)


if __name__ == "__main__":
    main()
