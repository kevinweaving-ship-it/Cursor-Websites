#!/usr/bin/env python3
"""Write Google sitemaps for the Weekend Roundup hub and every issue URL.

Google discovers new Monday issues from:
  - /sitemap-roundups.xml  (hub + /latest/ + every /issues/YYYY-MM-DD/)
  - /sitemap-news.xml      (issues published in the last 48 hours, news:news)
  - /sitemap.xml           (index lists both)
  - /robots.txt            (Sitemap: lines)

Monday publish and the daily sitemap cron both call write_web_root().
Failures here must never block an issue publish.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterable
from xml.sax.saxutils import escape

BASE = "https://sailingsa.co.za"
HUB = f"{BASE}/sailing-roundup/"
LATEST = f"{BASE}/sailing-roundup/latest/"
ISSUE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PING = "https://www.google.com/ping?sitemap="


def _esc(url: str) -> str:
    return escape(url or "", {'"': "&quot;", "'": "&apos;"})


def _issue_roots(web_root: pathlib.Path) -> list[pathlib.Path]:
    return [
        web_root / "sailing-roundup" / "issues",
        pathlib.Path("/var/www/sailingsa/sailing-roundup/issues"),
        pathlib.Path(__file__).resolve().parent.parent / "public" / "issues",
    ]


def published_issues(web_root: pathlib.Path | None = None) -> list[dict]:
    """Newest first: {monday, url, lastmod, title}."""
    web_root = pathlib.Path(web_root or "/var/www/sailingsa")
    seen: set[str] = set()
    out: list[dict] = []
    for root in _issue_roots(web_root):
        if not root.is_dir():
            continue
        for name in sorted((p.name for p in root.iterdir() if p.is_dir()), reverse=True):
            if not ISSUE_RE.match(name) or name in seen:
                continue
            issue_json = root / name / "issue.json"
            html = root / name / "index.html"
            if not issue_json.is_file() and not html.is_file():
                continue
            title = "South African Sailing — The Weekend Roundup"
            pub = name
            if issue_json.is_file():
                try:
                    data = json.loads(issue_json.read_text(encoding="utf-8"))
                    title = (data.get("title") or title).strip()
                    pub = (data.get("edition_date") or name)[:10]
                except Exception:
                    pass
            seen.add(name)
            out.append(
                {
                    "monday": name,
                    "url": f"{BASE}/sailing-roundup/issues/{name}/",
                    "lastmod": pub,
                    "title": f"{title} — {name}",
                }
            )
        if out:
            break
    return out


def public_urls(issues: Iterable[dict]) -> list[tuple[str, str]]:
    """Hub + latest + every issue HTML. These are the URLs Google must index."""
    rows = list(issues)
    last = max((i["lastmod"] for i in rows), default=dt.date.today().isoformat())
    entries = [(HUB, last), (LATEST, last)]
    seen = {HUB, LATEST}
    for item in rows:
        url = item["url"]
        if url in seen:
            continue
        seen.add(url)
        entries.append((url, item["lastmod"]))
    return entries


def news_urls(issues: Iterable[dict], now: dt.datetime | None = None) -> list[dict]:
    now = now or dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(hours=48)
    kept = []
    for item in issues:
        try:
            pub = dt.datetime.fromisoformat(item["lastmod"]).replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
        if pub < cutoff - dt.timedelta(hours=20):
            continue
        kept.append(item)
    return kept


def urlset_xml(entries: list[tuple[str, str]]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for loc, lastmod in entries:
        lines.append("  <url>")
        lines.append(f"    <loc>{_esc(loc)}</loc>")
        lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append("    <changefreq>weekly</changefreq>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def news_xml(items: list[dict]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">',
    ]
    for item in items:
        pub = item["lastmod"]
        lines.append("  <url>")
        lines.append(f"    <loc>{_esc(item['url'])}</loc>")
        lines.append("    <news:news>")
        lines.append("      <news:publication>")
        lines.append("        <news:name>SailingSA</news:name>")
        lines.append("        <news:language>en</news:language>")
        lines.append("      </news:publication>")
        lines.append(f"      <news:publication_date>{pub}T06:00:00+02:00</news:publication_date>")
        lines.append(f"      <news:title>{_esc(item['title'])}</news:title>")
        lines.append("    </news:news>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def ensure_index(index_path: pathlib.Path, today: str | None = None) -> None:
    """Keep sitemap-roundups.xml and sitemap-news.xml in the sitemap index."""
    today = today or dt.date.today().isoformat()
    needed = (
        f"{BASE}/sitemap-news.xml",
        f"{BASE}/sitemap-roundups.xml",
    )
    if not index_path.is_file():
        body = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        ]
        for loc in needed:
            body += ["  <sitemap>", f"    <loc>{_esc(loc)}</loc>", f"    <lastmod>{today}</lastmod>", "  </sitemap>"]
        body.append("</sitemapindex>")
        index_path.write_text("\n".join(body) + "\n", encoding="utf-8")
        return
    text = index_path.read_text(encoding="utf-8")
    changed = False
    for loc in needed:
        if loc in text:
            text = re.sub(
                r"(<loc>" + re.escape(_esc(loc)) + r"</loc>\s*<lastmod>)[^<]+",
                r"\g<1>" + today,
                text,
                count=1,
            )
            continue
        insert = (
            f"  <sitemap>\n    <loc>{_esc(loc)}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n  </sitemap>\n"
        )
        if "</sitemapindex>" in text:
            text = text.replace("</sitemapindex>", insert + "</sitemapindex>")
        else:
            text = text.rstrip() + "\n" + insert
        changed = True
    if changed or today in text:
        index_path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def ensure_robots(robots_path: pathlib.Path) -> None:
    lines = [
        "Disallow: /sailing-roundup/archive.json",
        "Disallow: /sailing-roundup/feed.json",
        "Disallow: /sailing-roundup/cards.json",
        "Disallow: /sailing-roundup/latest.json",
        f"Sitemap: {BASE}/sitemap.xml",
        f"Sitemap: {BASE}/sitemap-roundups.xml",
        f"Sitemap: {BASE}/sitemap-news.xml",
    ]
    if robots_path.is_file():
        text = robots_path.read_text(encoding="utf-8")
    else:
        text = "User-agent: *\nAllow: /\n\n"
    for line in lines:
        if line not in text:
            if not text.endswith("\n"):
                text += "\n"
            text += line + "\n"
    robots_path.write_text(text, encoding="utf-8")


def ping_google(sitemap_url: str) -> dict:
    url = PING + urllib.parse.quote(sitemap_url, safe="")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SailingSA-Sitemap/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"ok": True, "sitemap": sitemap_url, "status": getattr(resp, "status", 200)}
    except Exception as exc:
        return {"ok": False, "sitemap": sitemap_url, "error": str(exc)[:180]}


def write_web_root(web_root: pathlib.Path | str, *, ping: bool = True) -> dict:
    root = pathlib.Path(web_root)
    root.mkdir(parents=True, exist_ok=True)
    issues = published_issues(root)
    entries = public_urls(issues)
    news = news_urls(issues)
    (root / "sitemap-roundups.xml").write_text(urlset_xml(entries), encoding="utf-8")
    (root / "sitemap-news.xml").write_text(news_xml(news), encoding="utf-8")
    ensure_index(root / "sitemap.xml")
    ensure_robots(root / "robots.txt")
    seo = {}
    try:
        from seo_head import patch_web_root

        seo = patch_web_root(root)
    except Exception as exc:
        seo = {"ok": False, "error": str(exc)[:180]}
    pings = []
    if ping:
        for name in ("sitemap.xml", "sitemap-roundups.xml", "sitemap-news.xml"):
            pings.append(ping_google(f"{BASE}/{name}"))
    return {
        "ok": True,
        "issues": len(issues),
        "roundup_urls": len(entries),
        "news_urls": len(news),
        "urls": [u for u, _ in entries],
        "seo": seo,
        "google_ping": pings,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--web-root", default="/var/www/sailingsa")
    p.add_argument("--no-ping", action="store_true")
    args = p.parse_args()
    print(json.dumps(write_web_root(args.web_root, ping=not args.no_ping), indent=2))


if __name__ == "__main__":
    main()
