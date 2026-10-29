"""Inspect current hubs + near-term event URLs. Do not flood Google.

Official path for generic pages: sitemap index + URL Inspection.
Do not use the Indexing API (JobPosting/BroadcastEvent only).
Do not click Validate Fix.
Do not PUT every child sitemap (that doubled submitted and left feeds pending).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import SITE, server_data_root
from .probe_live import load_sitemap_urls
from .server_api import ensure_index_only_sitemaps, inspect_url, list_sitemaps
from .server_auth import NeedGoogleConsent, access_token
from .watchlist import priority_event_urls

SAST = ZoneInfo("Africa/Johannesburg")


def _coverage_bucket(coverage: str) -> str:
    c = (coverage or "").strip().lower()
    if c in ("submitted and indexed", "indexed"):
        return "indexed"
    if "crawled" in c and "not indexed" in c:
        return "crawled_not_indexed"
    if "discovered" in c or "unknown" in c:
        return "not_crawled"
    return "other"


def run(*, secret_dir: Path | None = None, data_root: Path | None = None) -> dict:
    root = data_root or server_data_root()
    day = datetime.now(SAST).date().isoformat()
    dest = root / day
    dest.mkdir(parents=True, exist_ok=True)
    sitemap = load_sitemap_urls(dest / "sitemap_urls.txt")
    urls = priority_event_urls(sitemap)
    token = access_token(secret_dir)
    feeds = ensure_index_only_sitemaps(token)
    inspections: dict[str, dict] = {}
    rows = []
    buckets = {"indexed": 0, "crawled_not_indexed": 0, "not_crawled": 0, "other": 0}
    for url in urls:
        try:
            ins = inspect_url(token, url)
        except Exception as e:
            ins = {"error": f"{type(e).__name__}: {e}"}
        inspections[url] = ins
        st = ins.get("indexStatusResult") or {}
        coverage = st.get("coverageState") or ins.get("error") or ""
        bucket = _coverage_bucket(coverage)
        buckets[bucket] = buckets.get(bucket, 0) + 1
        rows.append(
            {
                "url": url,
                "coverage": coverage,
                "verdict": st.get("verdict") or "",
                "last_crawl": st.get("lastCrawlTime") or "",
                "fetch": st.get("pageFetchState") or "",
                "robots": st.get("robotsTxtState") or "",
                "in_sitemap": bool(st.get("sitemap")),
                "bucket": bucket,
            }
        )
    payload = {
        "run_at": datetime.now(SAST).isoformat(),
        "site": SITE,
        "gsc_feeds": feeds,
        "sitemaps": list_sitemaps(token),
        "buckets": buckets,
        "rows": rows,
    }
    (dest / "inspect_priority.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        f"PRIORITY {payload['run_at']}",
        "indexed {indexed} | crawled-not-indexed {crawled_not_indexed} | not-crawled {not_crawled} | other {other}".format(
            **buckets
        ),
    ]
    for row in rows:
        lines.append(
            f"{row['verdict'] or '-':8} {str(row['coverage'])[:40]:40} "
            f"{row['url']}"
        )
    (dest / "inspect_priority.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    gsc_path = dest / "gsc_api.json"
    if gsc_path.is_file():
        google = json.loads(gsc_path.read_text(encoding="utf-8"))
        merged = dict(google.get("inspections") or {})
        merged.update(inspections)
        google["inspections"] = merged
        gsc_path.write_text(json.dumps(google, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Inspect priority event URLs; keep GSC index-only")
    ap.add_argument("--data-root", default="")
    ap.add_argument("--secret-dir", default="")
    args = ap.parse_args(argv)
    try:
        payload = run(
            secret_dir=Path(args.secret_dir) if args.secret_dir else None,
            data_root=Path(args.data_root) if args.data_root else None,
        )
    except NeedGoogleConsent as e:
        print("GSC AUTH", e)
        return 1
    print("GSC FEEDS", payload.get("gsc_feeds"))
    print("BUCKETS", payload.get("buckets"))
    for row in payload["rows"]:
        print(
            f"{row['verdict'] or '-':8} {str(row['coverage'])[:42]:42} "
            f"crawl={str(row['last_crawl'])[:19]:19} sitemap={row['in_sitemap']} {row['url']}"
        )
    print("SAVED inspect_priority.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
