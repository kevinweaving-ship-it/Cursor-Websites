#!/usr/bin/env python3
"""GSC daily retrieval + diagnosis. No website changes. No secrets in git."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .chrome_mac import inspect_environment, is_darwin
from .classify import classify
from .config import default_data_root, run_dir
from .pull_gsc_pages import NeedKevinApproval, pull
from .report import build_report, write_report
from .probe_live import load_sitemap_urls, save_probes, test_urls


def _today() -> str:
    try:
        return datetime.now(ZoneInfo("Africa/Johannesburg")).date().isoformat()
    except Exception:
        return date.today().isoformat()


def _load_yesterday(root: Path, day: str) -> dict | None:
    d = date.fromisoformat(day) - timedelta(days=1)
    p = root / d.isoformat() / "report.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    # fall back to previous gsc_pull
    q = root / d.isoformat() / "gsc_pull.json"
    if q.exists():
        return json.loads(q.read_text(encoding="utf-8"))
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="GSC daily retrieval + live diagnosis")
    ap.add_argument("--data-root", default="", help="Override data dir (default: Mac Application Support)")
    ap.add_argument("--day", default="", help="Run date YYYY-MM-DD (default: SAST today)")
    ap.add_argument("--inspect-only", action="store_true")
    ap.add_argument("--skip-pull", action="store_true", help="Reuse gsc_pull.json in the run dir")
    args = ap.parse_args(argv)

    env = inspect_environment()
    print("GSC_DAILY_INSPECT", json.dumps(env, indent=2))
    if args.inspect_only:
        return 0 if env.get("darwin") else 2

    if not is_darwin():
        print(
            "STOP: this puller must run on the Mac Mini that already has "
            "authenticated Chrome for Search Console. Cloud/Linux cannot use that profile.",
            file=sys.stderr,
        )
        return 2

    day = args.day or _today()
    root = Path(args.data_root) if args.data_root else default_data_root()
    dest = run_dir(day, root)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "inspect.json").write_text(json.dumps(env, indent=2), encoding="utf-8")

    try:
        if args.skip_pull and (dest / "gsc_pull.json").exists():
            pull_data = json.loads((dest / "gsc_pull.json").read_text(encoding="utf-8"))
        else:
            pull_data = pull(dest)
    except NeedKevinApproval as e:
        print("STOP_NEED_KEVIN_GOOGLE_APPROVAL")
        print(str(e))
        print("Approve/sign in on the existing Mac Chrome Google prompt, then re-run.")
        return 3

    sitemap = load_sitemap_urls(dest / "sitemap_urls.txt")
    tested: dict[str, list] = {}
    for issue in pull_data.get("issues") or []:
        rows = issue.get("urls") or []
        urls = []
        crawl_by_url = {}
        for row in rows:
            u = row.get("url") if isinstance(row, dict) else str(row)
            if u:
                urls.append(u)
                if isinstance(row, dict):
                    crawl_by_url[u] = row.get("last_crawl") or ""
        probes = test_urls(urls, sitemap)
        for p in probes:
            p["last_crawl"] = crawl_by_url.get(p["url"], "")
            p["google_issue"] = issue["label"]
            p["classification"] = classify(issue["key"], p)
        tested[issue["key"]] = probes
        save_probes(dest / f"{issue['key']}_probes.json", probes)

    yesterday = _load_yesterday(root, day)
    report = build_report(day, pull_data, tested, yesterday)
    md = write_report(dest, report)
    print(md.read_text(encoding="utf-8"))
    print(f"\nSAVED {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
