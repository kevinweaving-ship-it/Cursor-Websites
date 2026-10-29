#!/usr/bin/env python3
"""Ubuntu GSC daily: official API + live probes + known remediations.

This is the only daily GSC tool. Cron: /etc/cron.d/sailingsa_gsc_daily
→ /usr/local/sbin/sailingsa-gsc-daily at 09:00 Africa/Johannesburg.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from urllib.parse import urlparse

from .autofix import run as run_autofix
from .classify import HUMAN, OK, REAL, STALE, classify, issue_key_from_inspect
from .config import GSC_RESOURCE, INSPECT_BUDGET, SITE, server_data_root
from .probe_live import load_sitemap_urls, save_probes, test_urls
from .server_api import inspect_url, list_sitemaps, list_sites, search_analytics_totals, submit_published_sitemaps
from .server_auth import NeedGoogleConsent, access_token
from .seo_health import evaluate_health, health_lines, write_health
from .page_indexing import probe_families, render_lines as page_indexing_lines, write_page_indexing
from .pagespeed import render_lines as pagespeed_lines
from .pagespeed import run as run_pagespeed
from .rich_results import audit_web_root, render_lines as rich_results_lines
from .watchlist import build_watchlist, persist_reals, priority_event_urls
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
    index_submitted = 0
    errors = warnings = 0
    last_dl = ""
    paths = []
    for sm in sitemaps:
        paths.append(sm.get("path") or "")
        errors += int(sm.get("errors") or 0)
        warnings += int(sm.get("warnings") or 0)
        last_dl = last_dl or (sm.get("lastDownloaded") or "")
        for c in sm.get("contents") or []:
            n = int(c.get("submitted") or 0)
            submitted += n
            if sm.get("isSitemapsIndex") or (sm.get("path") or "").rstrip("/").endswith("/sitemap.xml"):
                index_submitted = max(index_submitted, n if c.get("type") == "web" else index_submitted)
    # Index rollup already includes children. Summing both doubles GSC "submitted".
    if index_submitted:
        submitted = index_submitted
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
    ap = argparse.ArgumentParser(description="Server-first GSC daily check + known fixes")
    ap.add_argument("--data-root", default="")
    ap.add_argument("--secret-dir", default="")
    ap.add_argument("--day", default="")
    ap.add_argument("--inspect-budget", type=int, default=INSPECT_BUDGET)
    ap.add_argument("--no-google", action="store_true", help="live probes only")
    ap.add_argument("--no-fix", action="store_true", help="classify only; do not apply remediations")
    args = ap.parse_args(argv)

    day = args.day or _today()
    root = Path(args.data_root) if args.data_root else server_data_root()
    secret = Path(args.secret_dir) if args.secret_dir else None
    dest = root / day
    dest.mkdir(parents=True, exist_ok=True)

    sitemap = load_sitemap_urls(dest / "sitemap_urls.txt")
    priority = priority_event_urls(sitemap)
    urls = build_watchlist(root, sitemap, max(args.inspect_budget, 20))
    (dest / "watchlist.txt").write_text("\n".join(urls) + "\n", encoding="utf-8")
    (dest / "priority_urls.txt").write_text("\n".join(priority) + "\n", encoding="utf-8")

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
            google["sitemap_submit"] = submit_published_sitemaps(token)
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

    apply_fixes = not args.no_fix
    autofix = run_autofix(apply=apply_fixes, probes=probes)
    (dest / "autofix.json").write_text(json.dumps(autofix, indent=2) + "\n", encoding="utf-8")
    if apply_fixes and autofix.get("applied"):
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
    sm_now = _sitemap_summary(google.get("sitemaps") or [])
    if int(sm_now.get("count") or 0) > 1:
        attn.append(
            f"GSC has {sm_now.get('count')} sitemap feeds; should be sitemap.xml only"
        )
    try:
        import urllib.request

        req = urllib.request.Request(
            SITE.rstrip("/") + "/robots.txt",
            headers={"User-Agent": "SailingSA-GSC/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            robots = resp.read().decode("utf-8", "replace")
        if "Allow: /api/og/" not in robots or "Allow: /api/club-logo/" not in robots:
            attn.append("robots.txt missing Allow /api/og/ or /api/club-logo/")
    except Exception as e:
        attn.append(f"robots.txt check failed: {type(e).__name__}")

    health = evaluate_health(
        day=day,
        google=google,
        probes=probes,
        sitemap_summary=_sitemap_summary(google.get("sitemaps") or []),
        search_analytics=google.get("search_analytics") or {},
        data_root=root,
        as_of=datetime.now(SAST),
    )
    write_health(dest, health)
    for a in health.get("alerts") or []:
        if a not in attn:
            attn.append(a)

    sub = google.get("sitemap_submit")
    if isinstance(sub, list):
        bad = [row for row in sub if not row.get("ok")]
        if bad:
            names = ", ".join((row.get("feed") or "").rsplit("/", 1)[-1] for row in bad)
            attn.append(f"Sitemap submit failed: {names}")
    try:
        page_idx = probe_families()
    except Exception as e:
        page_idx = {"error": f"{type(e).__name__}: {e}", "broken": [str(e)], "snapshot": []}
    write_page_indexing(dest, page_idx)
    for item in page_idx.get("broken") or []:
        attn.append(f"INDEX FAMILY {item}")
    try:
        rich = audit_web_root(inspections=inspections, dest=dest)
    except Exception as e:
        rich = {"error": f"{type(e).__name__}: {e}", "live": {}, "gsc": {}}
        (dest / "rich_results.json").write_text(json.dumps(rich, indent=2) + "\n")
    live_err_n = int((rich.get("live") or {}).get("error_pages") or 0)
    gsc_err_n = int((rich.get("gsc") or {}).get("event_error_urls") or 0)
    if live_err_n:
        attn.append(f"EVENT JSON-LD errors on {live_err_n} pages")
    if gsc_err_n:
        attn.append(f"GSC Event ERRORS on {gsc_err_n} inspected URLs")
    try:
        psi = run_pagespeed(dest=dest, apply=apply_fixes, fetch=not args.no_google)
    except Exception as e:
        psi = {"error": f"{type(e).__name__}: {e}", "scores": {}, "autofix": {}}
        (dest / "pagespeed.json").write_text(json.dumps(psi, indent=2) + "\n")
    mob = ((psi.get("scores") or {}).get("mobile") or {})
    if isinstance(mob.get("performance"), int) and mob["performance"] < 70:
        attn.append(f"PageSpeed mobile {mob['performance']} LCP {mob.get('lcp_s')}s")
    payload = {
        "run_date": day,
        "sitemap_submit": sub,
        "property": GSC_RESOURCE,
        "auth": google["auth"],
        "apply_fixes": apply_fixes,
        "autofix": {
            "actions": autofix.get("actions") or [],
            "still_broken": autofix.get("still_broken") or [],
            "five_xx": autofix.get("five_xx") or 0,
        },
        "sitemap": _sitemap_summary(google.get("sitemaps") or []),
        "search_analytics": google.get("search_analytics") or {},
        "inspect_summary": {"n": sum(1 for v in inspections.values() if v), "pass": pass_n, "not_indexed": not_idx},
        "priority": {
            "urls": priority,
            "rows": [
                {
                    "url": u,
                    "coverage": ((inspections.get(u) or {}).get("indexStatusResult") or {}).get(
                        "coverageState"
                    )
                    or (inspections.get(u) or {}).get("error")
                    or "",
                    "verdict": _inspect_verdict(inspections.get(u) or {}),
                    "last_crawl": ((inspections.get(u) or {}).get("indexStatusResult") or {}).get(
                        "lastCrawlTime"
                    )
                    or "",
                    "robots": ((inspections.get(u) or {}).get("indexStatusResult") or {}).get(
                        "robotsTxtState"
                    )
                    or "",
                }
                for u in priority
            ],
        },
        "classes": cls,
        "delta": delta,
        "real_urls": real_urls,
        "url_class": {p["url"]: p.get("classification") for p in probes},
        "attention": attn,
        "seo_health": {
            "healthy": health.get("healthy"),
            "alerts": health.get("alerts") or [],
            "googlebot": health.get("googlebot"),
            "sitemap": health.get("sitemap"),
            "indexing": {
                k: (health.get("indexing") or {}).get(k)
                for k in (
                    "indexed",
                    "crawled_not_indexed",
                    "not_crawled",
                    "canonical_gsc_mismatch",
                    "note",
                )
            },
            "live_canonical_mismatches": len(health.get("canonical_live_mismatches") or []),
            "performance": health.get("performance"),
        },
        "page_indexing": {
            "snapshot_date": page_idx.get("snapshot_date"),
            "snapshot_total": page_idx.get("snapshot_total"),
            "by_action": page_idx.get("by_action"),
            "broken": page_idx.get("broken") or [],
            "known_gaps": page_idx.get("known_gaps") or [],
            "families": page_idx.get("families") or [],
            "snapshot": [
                {
                    "key": r.get("key"),
                    "label": r.get("label"),
                    "pages": r.get("pages"),
                    "action": r.get("action"),
                }
                for r in (page_idx.get("snapshot") or [])
            ],
        },
        "page_indexing_cohorts": None,
        "page_indexing_note": page_idx.get("note")
        or (
            "Official Search Console API has no Page Indexing report. "
            "Do not click Validate Fix."
        ),
        "rich_results": {
            "live": rich.get("live") or {},
            "gsc": rich.get("gsc") or {},
            "error": rich.get("error"),
        },
        "rich_results_note": rich.get("note")
        or (
            "Official Search Console API has no Enhancement report table. "
            "We audit live Event JSON-LD and read URL Inspection richResultsResult."
        ),
        "pagespeed": {
            "scores": psi.get("scores") or {},
            "autofix": psi.get("autofix") or {},
            "error": psi.get("error"),
        },
    }
    (dest / "gsc_api.json").write_text(json.dumps(google, indent=2) + "\n", encoding="utf-8")
    (dest / "report.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (dest / "inspect_priority.json").write_text(
        json.dumps(payload.get("priority") or {}, indent=2) + "\n", encoding="utf-8"
    )
    write_whatsapp(dest, payload)
    md = [
        f"# GSC server daily — {day}",
        "",
        f"Auth: {google['auth']}",
        f"Fixes: {'ON' if apply_fixes else 'OFF'}"
        + (
            f" actions={autofix.get('actions') or []} still={autofix.get('still_broken') or []}"
            if apply_fixes
            else ""
        ),
        f"Live classes: {cls}",
        f"Inspected: {payload['inspect_summary']}",
        f"Priority: {[(r.get('verdict'), (r.get('coverage') or '')[:32], r.get('url')) for r in (payload.get('priority') or {}).get('rows') or []]}",
        "",
        *health_lines(health),
        "",
        *page_indexing_lines(page_idx),
        "",
        payload["page_indexing_note"],
        "",
        *rich_results_lines(rich),
        "",
        payload["rich_results_note"],
        "",
        *pagespeed_lines(psi),
        "",
    ]
    (dest / "REPORT.md").write_text("\n".join(md), encoding="utf-8")
    print((dest / "whatsapp_gsc.txt").read_text(encoding="utf-8"))
    print(f"SAVED {dest}")
    return 0 if google["auth"] in ("OK", "PENDING") else 1


if __name__ == "__main__":
    raise SystemExit(main())
