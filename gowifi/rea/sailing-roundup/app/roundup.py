#!/usr/bin/env python3
"""Standalone sailing roundup builder: read-only public results, web research, JSON feed, HTML, PDF."""
import argparse
import datetime as dt
import html
import json
import pathlib
import re
import subprocess
import sys
import urllib.parse

import requests
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (compatible; SailingRoundupResearch/0.1)"}


def fetch(url, timeout=20):
    r = requests.get(url, headers=UA, timeout=timeout)
    r.raise_for_status()
    return r.text


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def discover(event, limit=8):
    terms = " ".join([event["title"], event.get("club", ""), event.get("date", ""), "sailing photos results"])
    q = urllib.parse.quote_plus(terms)
    results = []
    for engine, url in [
        ("bing", "https://www.bing.com/search?q=" + q),
        ("duckduckgo", "https://www.google.com/search?q=" + q),
    ]:
        try:
            soup = BeautifulSoup(fetch(url), "html.parser")
            selector = "li.b_algo h2 a" if engine == "bing" else "div.MjjYud a"
            for a in soup.select(selector):
                href = a.get("href", "")
                title = clean(a.get_text(" ", strip=True))
                blob = (title + " " + href).lower()
                if href.startswith("http") and title and any(
                    t in blob for t in ["sailing", "regatta", "yacht", "sailingsa", "nationals"]
                ) and not any(x.get("url") == href for x in results):
                    results.append({"title": title, "url": href, "engine": engine, "status": "unverified"})
                    if len(results) >= limit:
                        break
        except Exception as exc:
            results.append({"engine": engine, "error": str(exc)[:160]})
    return results


def event_from_page(url):
    soup = BeautifulSoup(fetch(url), "html.parser")
    title = clean((soup.find("h1") or soup.title).get_text(" ", strip=True))
    tables = []
    for table in soup.select("table"):
        rows = []
        for tr in table.select("tr"):
            cells = [clean(c.get_text(" ", strip=True)) for c in tr.select("th,td")]
            if cells:
                rows.append(cells)
        if len(rows) > 2:
            tables.append(rows[:150])
    return {"id": url.rstrip("/").split("/")[-1], "title": title, "url": url, "tables": tables}


def create(issue, urls):
    root = ROOT / "issues" / issue
    (root / "sources").mkdir(parents=True, exist_ok=True)
    articles = []
    log = []
    for url in urls:
        try:
            ev = event_from_page(url)
            research = discover({"title": ev["title"], "date": issue})
            (root / "sources" / (ev["id"] + ".json")).write_text(
                json.dumps({"event": ev, "web_discovery": research}, indent=2, ensure_ascii=False)
            )
            if not ev["tables"]:
                log.append({"event": ev["id"], "status": "skipped_no_table"})
                continue
            article = {
                "id": ev["id"],
                "type": "regatta_report",
                "headline": ev["title"],
                "deck": "Published results and external reporting under editorial review",
                "byline": "Sailing Weekend Roundup",
                "published_at": issue,
                "event_id": ev["id"],
                "hero_image": None,
                "blocks": [
                    {
                        "type": "paragraph",
                        "text": "Results are available from the original event page. Further reporting and photographs require verification.",
                    },
                    {
                        "type": "results",
                        "source_event_url": url,
                        "columns": ev["tables"][0][0],
                        "rows": ev["tables"][0][1:],
                        "as_of": issue,
                    },
                ],
                "sources": [url],
                "research_candidates": research,
                "review_status": "draft",
            }
            articles.append(article)
            log.append({"event": ev["id"], "status": "draft", "rows": len(ev["tables"][0])})
        except Exception as exc:
            log.append({"url": url, "status": "error", "error": str(exc)[:200]})
    data = {
        "schema_version": "1.0",
        "issue_id": issue,
        "title": "Weekend Sailing Roundup",
        "edition_date": issue,
        "status": "draft",
        "articles": articles,
    }
    (root / "issue.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    (root / "sources" / "build-log.json").write_text(json.dumps(log, indent=2))
    return data, log


def _image_block(block):
    rights = block.get("rights_status")
    source = block.get("source_url") or block.get("url") or ""
    if rights in ("external_link_only", "source_attributed") or not block.get("url"):
        label = html.escape(block.get("caption") or "View original photograph or post at source")
        return (
            "<p><a href="
            + chr(34)
            + html.escape(source, quote=True)
            + chr(34)
            + ">"
            + label
            + "</a></p>"
        )
    return (
        "<figure><img src="
        + chr(34)
        + html.escape(block.get("url", ""), quote=True)
        + chr(34)
        + " alt="
        + chr(34)
        + html.escape(block.get("alt") or "", quote=True)
        + chr(34)
        + "><figcaption>"
        + html.escape(block.get("caption") or "")
        + "</figcaption></figure>"
    )


def render(issue):
    data = json.loads((ROOT / "issues" / issue / "issue.json").read_text())
    out = ROOT / "public" / "issues" / issue
    out.mkdir(parents=True, exist_ok=True)
    (out / "issue.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    chunks = []
    for a in data.get("articles") or []:
        body = [
            "<article><h2>"
            + html.escape(a.get("headline") or "")
            + "</h2><p class='deck'>"
            + html.escape(a.get("deck") or "")
            + "</p>"
        ]
        for block in a.get("blocks") or []:
            kind = block.get("type")
            if kind == "paragraph":
                body.append("<p>" + html.escape(block.get("text") or "") + "</p>")
            elif kind == "results":
                cols = block.get("columns") or []
                rows = block.get("rows") or []
                body.append(
                    "<div class='table-scroll'><table><thead><tr>"
                    + "".join("<th>" + html.escape(c) + "</th>" for c in cols)
                    + "</tr></thead><tbody>"
                )
                for row in rows:
                    body.append("<tr>" + "".join("<td>" + html.escape(str(c)) + "</td>" for c in row) + "</tr>")
                body.append("</tbody></table></div>")
            elif kind == "heading":
                body.append("<h3>" + html.escape(block.get("text") or "") + "</h3>")
            elif kind == "image":
                body.append(_image_block(block))
            elif kind == "video":
                url = block.get("source_url") or block.get("url") or ""
                body.append(
                    "<p><a href="
                    + chr(34)
                    + html.escape(url, quote=True)
                    + chr(34)
                    + ">Watch video at source</a></p>"
                )
        social = a.get("social_sources") or []
        if social:
            body.append("<h3>Social and media sources</h3><ul>")
            for post in social:
                url = post.get("url") or ""
                title = post.get("title") or post.get("headline") or url
                body.append(
                    "<li><a href="
                    + chr(34)
                    + html.escape(url, quote=True)
                    + chr(34)
                    + ">"
                    + html.escape(title)
                    + "</a></li>"
                )
            body.append("</ul>")
        body.append("</article>")
        chunks.append("".join(body))
    if not chunks:
        chunks.append("<article><p>No scored weekend events were published for this edition.</p></article>")
    css = (
        '@import url("https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;600;700&family=Libre+Baskerville:wght@400;700&display=swap");'
        "body{margin:0;color:#162338;background:#fff;font:16px/1.7 'DM Sans',sans-serif}"
        ".wrap{max-width:1080px;margin:auto;padding:36px 24px}"
        "h1,h2{font-family:'Libre Baskerville',Georgia,serif;line-height:1.25}"
        "h1{font-size:clamp(32px,5vw,60px)}h2{font-size:clamp(23px,3vw,35px)}"
        "header{border-bottom:4px solid #16385a;padding-bottom:22px}"
        "article{margin:42px 0;border-bottom:1px solid #ddd;padding-bottom:32px}"
        ".deck{color:#607080}img{max-width:100%;height:auto}.table-scroll{overflow-x:auto}"
        "table{border-collapse:collapse;width:100%;font-size:13px}td,th{border:1px solid #ddd;padding:7px}"
        "th{background:#eaf0f5;text-align:left}@media print{article{break-inside:avoid}body{font-size:12px}}"
    )
    page = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Weekend Sailing Roundup "
        + issue
        + "</title><style>"
        + css
        + "</style></head><body><main class='wrap'><header><strong>WEEKEND SAILING ROUNDUP</strong><h1>"
        + html.escape(data.get("title") or "Weekend Sailing Roundup")
        + "</h1><p>"
        + issue
        + "</p></header>"
        + "".join(chunks)
        + "</main></body></html>"
    )
    (out / "index.html").write_text(page)
    browser = "/opt/chromium/chrome"
    if pathlib.Path(browser).exists():
        try:
            p = subprocess.run(
                [
                    browser,
                    "--headless",
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage",
                    "--no-pdf-header-footer",
                    "--print-to-pdf=" + str(out / "edition.pdf"),
                    (out / "index.html").resolve().as_uri(),
                ],
                timeout=40,
                capture_output=True,
            )
            if p.returncode:
                print("PDF error:", p.stderr.decode(errors="replace")[-200:], file=sys.stderr)
        except Exception as e:
            print("PDF error:", e, file=sys.stderr)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["build", "render", "serve"])
    p.add_argument("--issue", default=dt.date.today().isoformat())
    p.add_argument("--event-url", action="append", default=[])
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args()
    if args.command == "build":
        data, log = create(args.issue, args.event_url)
        print(json.dumps({"issue": args.issue, "articles": len(data["articles"]), "events": log}))
        render(args.issue)
    elif args.command == "render":
        print(render(args.issue))
    else:
        from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
        import functools

        print("Serving", ROOT / "public", "on port", args.port, flush=True)
        ThreadingHTTPServer(
            ("127.0.0.1", args.port),
            functools.partial(SimpleHTTPRequestHandler, directory=str(ROOT / "public")),
        ).serve_forever()


if __name__ == "__main__":
    main()
