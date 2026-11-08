"""Inspect current event URLs + re-submit the sitemap.

Official Google path for generic pages: sitemap submit + URL Inspection.
The Indexing API is JobPosting/BroadcastEvent only — do not publish regatta URLs.
Does not click Validate Fix.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import ROOT_SITEMAP, SITE, server_data_root
from .server_api import inspect_url, list_sitemaps, submit_sitemap
from .server_auth import NeedGoogleConsent, access_token
from .watchlist import load_seed

SAST = ZoneInfo("Africa/Johannesburg")
PRIORITY_PATHS = (
    "/",
    "/events",
    "/regatta/2026-09-13-zvyc-cape-classic",
    "/regatta/2026-08-29-lipton-challenge-cup",
    "/regatta/2026-10-24-ullman-sails-womens-series-day-2",
    "/regatta/2026-10-17-mac-tsl-wc-team-sailing",
    "/class/ilca-6",
    "/club/rcyc",
)


def _urls() -> list[str]:
    seed = load_seed()
    out: list[str] = []
    seen: set[str] = set()
    for u in list(seed.get("core") or []) + [SITE.rstrip("/") + p for p in PRIORITY_PATHS]:
        u = (u or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def run(*, secret_dir: Path | None = None, data_root: Path | None = None) -> dict:
    root = data_root or server_data_root()
    day = datetime.now(SAST).date().isoformat()
    dest = root / day
    dest.mkdir(parents=True, exist_ok=True)
    token = access_token(secret_dir)
    submitted = None
    submit_error = ""
    try:
        submitted = submit_sitemap(token, ROOT_SITEMAP)
    except Exception as e:
        submit_error = f"{type(e).__name__}: {e}"
    inspections: dict[str, dict] = {}
    rows = []
    for url in _urls():
        try:
            ins = inspect_url(token, url)
        except Exception as e:
            ins = {"error": f"{type(e).__name__}: {e}"}
        inspections[url] = ins
        st = ins.get("indexStatusResult") or {}
        rows.append(
            {
                "url": url,
                "coverage": st.get("coverageState") or ins.get("error") or "",
                "verdict": st.get("verdict") or "",
                "last_crawl": st.get("lastCrawlTime") or "",
                "fetch": st.get("pageFetchState") or "",
                "robots": st.get("robotsTxtState") or "",
                "in_sitemap": bool(st.get("sitemap")),
            }
        )
    payload = {
        "run_at": datetime.now(SAST).isoformat(),
        "sitemap_submit_ok": not submit_error,
        "sitemap_submit_error": submit_error,
        "sitemaps": list_sitemaps(token) if not submit_error else [],
        "submitted": submitted,
        "rows": rows,
    }
    (dest / "inspect_priority.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    gsc_path = dest / "gsc_api.json"
    if gsc_path.is_file():
        google = json.loads(gsc_path.read_text(encoding="utf-8"))
        merged = dict(google.get("inspections") or {})
        merged.update(inspections)
        google["inspections"] = merged
        gsc_path.write_text(json.dumps(google, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Inspect priority event URLs; submit sitemap")
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
    print("SITEMAP SUBMIT", "OK" if payload["sitemap_submit_ok"] else payload["sitemap_submit_error"])
    for row in payload["rows"]:
        print(
            f"{row['verdict'] or '-':8} {row['coverage'][:42]:42} "
            f"crawl={str(row['last_crawl'])[:19]:19} sitemap={row['in_sitemap']} {row['url']}"
        )
    print("SAVED inspect_priority.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
