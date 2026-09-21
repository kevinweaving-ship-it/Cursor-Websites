#!/usr/bin/env python3
"""Ubuntu GSC daily: official API + live probes. Monitoring only. No site fixes."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from urllib.parse import urlparse

from .classify import HUMAN, OK, REAL, STALE, classify, issue_key_from_inspect
from .config import GSC_RESOURCE, INSPECT_BUDGET, SITE, server_data_root
from .probe_live import load_sitemap_urls, save_probes, test_urls
from .server_api import inspect_url, list_sitemaps, list_sites, search_analytics_totals
from .server_auth import NeedGoogleConsent, access_token
from .watchlist import build_watchlist, persist_reals
from .whatsapp_gsc import class_counts, write_whatsapp

SAST = ZoneInfo("Africa/Johannesburg")


def _intentional_watch(probe: dict) -> str | None:
    path = urlparse(probe.get("url") or "").path.rstrip("/") or "/"
    final = probe.get("status") or 0
    if path == "/media" and final == 404:
        return OK
    if path in ("/results", "/media") or path.startswith("/test/"):
        if final == 200:
            return OK
    return None


def _today() -> str:
    return datetime.now(SAST).date().isoformat()


def _sitemap_summary(sitemaps: list[dict]) -> dict:
    submitted = 0
    errors = warnings = 0
    last_dl = ""
    paths = []
    for sm in sitemaps:
        paths.append(sm.get("path") or "")
        errors += int(sm.get("errors") or 0)
        warnings += int(sm.get("warnings") or 0)
        last_dl = last_dl or (sm.get("lastDownloaded") or "")
        for c in sm.get("contents") or []:
            submitted += int(c.get("submitted") or 0)
    return {
        "count": len(sitemaps),
        "paths": paths,
        "submitted": submitted,
        "errors": errors,
        "warnings": warnings,
        "last_downloaded": last_dl[:10] if last_dl else "",
        # contents[].indexed is deprecated by Google — not used.
    }


def _inspect_verdict(result: dict) -> str:
    st = (result or {}).get("indexStatusResult") or {}
    return (st.get("verdict") or "").upper()


def _delta(today_probes: list[dict], yesterday: dict | None) -> dict:
    today_real = {p["url"] for p in today_probes if p.get("classification") == REAL}
    y_real = set((yesterday or {}).get("real_urls") or [])
    y_cls = (yesterday or {}).get("url_class") or {}
    now_stale = 0
    for u, kind in y_cls.items():
        if kind == REAL:
            row = next((p for p in today_probes if p.get("url") == u), None)
            if row and row.get("classification") == STALE:
                now_stale += 1
    return {
        "real_delta": (len(today_real) - len(y_real)) if yesterday else "n/a",
        "new_real": len(today_real - y_real) if yesterday else len(today_real),
        "now_stale": now_stale,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Server-first GSC monitoring (no fixes)")
    ap.add_argument("--data-root", default="")
    ap.add_argument("--secret-dir", default="")
    ap.add_argument("--day", default="")
    ap.add_argument("--inspect-budget", type=int, default=INSPECT_BUDGET)
    ap.add_argument("--no-google", action="store_true", help="live probes only")
    args = ap.parse_args(argv)

    day = args.day or _today()
    root = Path(args.data_root) if args.data_root else server_data_root()
    secret = Path(args.secret_dir) if args.secret_dir else None
    dest = root / day
    dest.mkdir(parents=True, exist_ok=True)

    sitemap = load_sitemap_urls(dest / "sitemap_urls.txt")
    urls = build_watchlist(root, sitemap, max(args.inspect_budget, 20))
    (dest / "watchlist.txt").write_text("\n".join(urls) + "\n", encoding="utf-8")

    google: dict = {
        "auth": "PENDING",
        "property": GSC_RESOURCE,
        "sites": [],
        "sitemaps": [],
        "search_analytics": {},
        "inspections": {},
    }
    token = None
    if not args.no_google:
        try:
            token = access_token(secret)
            google["auth"] = "OK"
            google["sites"] = list_sites(token)
            names = [s.get("siteUrl") for s in google["sites"]]
            if GSC_RESOURCE not in names and SITE.rstrip("/") + "/" not in names:
                google["auth"] = "OK_BUT_PROPERTY_MISSING"
            google["sitemaps"] = list_sitemaps(token)
            end = date.fromisoformat(day)
            start = end - timedelta(days=7)
            google["search_analytics"] = search_analytics_totals(
                token, start=start.isoformat(), end=end.isoformat()
            )
        except NeedGoogleConsent as e:
            google["auth"] = "PENDING"
            google["auth_error"] = str(e)
        except Exception as e:
            google["auth"] = "ERROR"
            google["auth_error"] = f"{type(e).__name__}: {e}"

    inspections: dict[str, dict] = {}
    if token:
        for i, url in enumerate(urls):
            if i >= args.inspect_budget:
                break
            try:
                inspections[url] = inspect_url(token, url)
            except Exception as e:
                inspections[url] = {"error": f"{type(e).__name__}: {e}"}
    google["inspections"] = {u: inspections.get(u) for u in urls}

    probes = test_urls(urls, sitemap)
    for p in probes:
        ins = inspections.get(p["url"]) or {}
        st = ins.get("indexStatusResult") or {}
        p["google_verdict"] = _inspect_verdict(ins)
        p["google_coverage"] = st.get("coverageState") or ""
        p["last_crawl"] = st.get("lastCrawlTime") or ""
        p["page_fetch_state"] = st.get("pageFetchState") or ""
        p["issue_key"] = issue_key_from_inspect(st, p)
        p["classification"] = classify(p["issue_key"], p)
        known = _intentional_watch(p)
        if known:
            p["classification"] = known
        p["in_google_sitemap"] = bool(st.get("sitemap"))
    save_probes(dest / "probes.json", probes)

    ypath = root / (date.fromisoformat(day) - timedelta(days=1)).isoformat() / "report.json"
    yesterday = json.loads(ypath.read_text(encoding="utf-8")) if ypath.is_file() else None

    cls = class_counts(probes)
    real_urls = [p["url"] for p in probes if p.get("classification") == REAL]
    persist_reals(root / "watchlist_real.json", real_urls, sitemap)

    pass_n = sum(1 for p in probes if p.get("google_verdict") == "PASS")
    not_idx = sum(
        1 for p in probes if p.get("google_verdict") in ("FAIL", "NEUTRAL")
    )
    delta = _delta(probes, yesterday)
    attn = []
    if google["auth"] != "OK":
        attn.append(f"GSC OAuth {google['auth']}: {google.get('auth_error') or 'one-time consent required'}")
    for p in probes:
        if p.get("classification") == REAL:
            attn.append(f"REAL {p.get('first_status')} {p['url']}")
        if len(attn) >= 6:
            break
    if delta.get("new_real"):
        attn.insert(0, f"{delta['new_real']} new REAL vs yesterday")

    payload = {
        "run_date": day,
        "property": GSC_RESOURCE,
        "auth": google["auth"],
        "apply_fixes": False,
        "sitemap": _sitemap_summary(google.get("sitemaps") or []),
        "search_analytics": google.get("search_analytics") or {},
        "inspect_summary": {"n": sum(1 for v in inspections.values() if v), "pass": pass_n, "not_indexed": not_idx},
        "classes": cls,
        "delta": delta,
        "real_urls": real_urls,
        "url_class": {p["url"]: p.get("classification") for p in probes},
        "attention": attn,
        "page_indexing_cohorts": None,
        "page_indexing_note": (
            "Official Search Console API has no Page Indexing report "
            "(cohort names, example lists, validation, indexed/not-indexed totals)."
        ),
    }
    (dest / "gsc_api.json").write_text(json.dumps(google, indent=2) + "\n", encoding="utf-8")
    (dest / "report.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_whatsapp(dest, payload)
    md = [
        f"# GSC server daily — {day}",
        "",
        f"Auth: {google['auth']}",
        "Fixes: OFF",
        f"Live classes: {cls}",
        f"Inspected: {payload['inspect_summary']}",
        "",
        payload["page_indexing_note"],
        "",
    ]
    (dest / "REPORT.md").write_text("\n".join(md), encoding="utf-8")
    print((dest / "whatsapp_gsc.txt").read_text(encoding="utf-8"))
    print(f"SAVED {dest}")
    return 0 if google["auth"] in ("OK", "PENDING") else 1


if __name__ == "__main__":
    raise SystemExit(main())
