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


LAYOUTS = ("lead", "photo-led", "split", "classic", "compact")


def _image_block(block):
    url = block.get("url") or ""
    if not url:
        return ""
    caption = block.get("caption") or ""
    credit = block.get("credit") or ""
    if credit and credit.lower() not in caption.lower():
        caption = (caption + " Photo: " + credit).strip()
    return (
        "<figure><img src="
        + chr(34)
        + html.escape(url, quote=True)
        + chr(34)
        + " alt="
        + chr(34)
        + html.escape(block.get("alt") or caption or "", quote=True)
        + chr(34)
        + "><figcaption>"
        + html.escape(caption)
        + "</figcaption></figure>"
    )


def _results_block(block):
    cols = block.get("columns") or []
    rows = block.get("rows") or []
    html_rows = [
        "<div class='board'><table><thead><tr>"
        + "".join("<th>" + html.escape(c) + "</th>" for c in cols)
        + "</tr></thead><tbody>"
    ]
    for row in rows:
        html_rows.append("<tr>" + "".join("<td>" + html.escape(str(c)) + "</td>" for c in row) + "</tr>")
    html_rows.append("</tbody></table></div>")
    return "".join(html_rows)


def _story_parts(article):
    image = ""
    paras = []
    board = []
    for block in article.get("blocks") or []:
        kind = block.get("type")
        if kind == "image" and not image:
            image = _image_block(block)
        elif kind == "paragraph":
            paras.append("<p>" + html.escape(block.get("text") or "") + "</p>")
        elif kind == "heading":
            board.append("<h3 class='board-label'>" + html.escape(block.get("text") or "Leaderboard") + "</h3>")
        elif kind == "results":
            board.append(_results_block(block))
    if paras:
        paras[0] = paras[0].replace("<p>", "<p class='lede'>", 1)
    return image, paras, board


def _layout_name(index, article):
    chosen = article.get("layout")
    if chosen in LAYOUTS:
        return chosen
    if article.get("type") == "feature":
        return "lead"
    return LAYOUTS[(index % 4) + 1]


def _render_story(index, article):
    layout = _layout_name(index, article)
    image, paras, board = _story_parts(article)
    kicker = html.escape(article.get("kicker") or (article.get("class_name") or "Weekend").upper())
    headline = html.escape(article.get("headline") or "")
    deck = html.escape(article.get("deck") or "")
    byline = html.escape(article.get("byline") or "Weekend Sailing Roundup")
    dateline = html.escape(article.get("published_at") or "")
    head = (
        "<p class='kicker'>" + kicker + "</p>"
        "<h2>" + headline + "</h2>"
        + (("<p class='deck'>" + deck + "</p>") if deck else "")
        + "<p class='byline'>By " + byline + "  ·  " + dateline + "</p>"
    )
    copy = "".join(paras)
    standings = "".join(board)
    if layout == "lead":
        inner = "<div class='banner'>" + head + "</div><div class='lead-grid'>" + (image or "") + "<div class='copy cols-3'>" + copy + "</div></div>"
    elif layout == "photo-led":
        inner = (image or "") + head + "<div class='copy cols-2'>" + copy + "</div>" + standings
    elif layout == "split":
        inner = head + "<div class='split'><div class='split-photo'>" + (image or "") + "</div><div class='copy'>" + copy + "</div></div>" + standings
    elif layout == "compact":
        inner = "<div class='compact-head'>" + head + "</div><div class='compact-row'>" + (image or "") + "<div class='copy'>" + copy + "</div></div>" + standings
    else:
        mid = copy
        if image and paras:
            mid = paras[0] + image + "".join(paras[1:])
        elif image:
            mid = image + copy
        inner = head + "<div class='copy cols-2'>" + mid + "</div>" + standings
    return "<article class='story story-" + layout + "'>" + inner + "</article>"


def newspaper_css():
    return """
@import url("https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&family=Oswald:wght@500;600&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap");
:root{--ink:#111;--rule:#111;--muted:#444;--paper:#f6f1e4;--card:#fffdf6}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.45 'Source Serif 4',Georgia,serif}
.paper{max-width:1180px;margin:0 auto;padding:18px 22px 48px;background:var(--card);box-shadow:0 0 0 1px #d7cbb0}
.masthead{text-align:center;border-top:4px solid var(--rule);border-bottom:1px solid var(--rule);padding:10px 0 8px}
.masthead .flag{font:600 11px/1 Oswald,sans-serif;letter-spacing:.28em;text-transform:uppercase}
.masthead h1{font:700 54px/0.92 'Libre Baskerville',Georgia,serif;margin:6px 0 4px;letter-spacing:-1px}
.folio{display:flex;justify-content:space-between;border-top:3px double var(--rule);border-bottom:1px solid var(--rule);font:600 11px/1 Oswald,sans-serif;letter-spacing:.12em;text-transform:uppercase;padding:6px 2px;margin-bottom:18px}
.edition-grid{display:grid;grid-template-columns:1fr 1fr;gap:22px 26px;align-items:start}
.story{break-inside:avoid;page-break-inside:avoid;border-bottom:1px solid #cfc3a6;padding-bottom:16px}
.story-lead{grid-column:1/-1;border-bottom:3px double var(--rule);padding-bottom:20px;margin-bottom:4px}
.kicker{font:600 11px/1 Oswald,sans-serif;letter-spacing:.16em;margin:0 0 4px;color:#6a1d1d}
h2{font:700 28px/1.12 'Libre Baskerville',Georgia,serif;margin:0 0 6px}
.story-lead h2{font-size:clamp(34px,5vw,52px);text-align:center}
.story-photo-led h2{font-size:34px}
.story-split h2{font-size:26px}
.story-classic h2{font-size:24px;font-style:italic}
.story-compact h2{font-size:21px;font-family:Oswald,sans-serif;letter-spacing:.02em;text-transform:uppercase}
.deck{margin:0 0 6px;color:var(--muted);font:italic 16px/1.35 'Libre Baskerville',Georgia,serif}
.byline{margin:0 0 10px;font:600 10px/1 Oswald,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:#333}
.banner{text-align:center}
.lead-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:18px;align-items:start}
.copy p{margin:0 0 9px}
.copy .lede:first-letter{font:700 46px/0.72 'Libre Baskerville',Georgia,serif;float:left;padding:4px 6px 0 0}
.cols-2{column-count:2;column-gap:18px}
.cols-3{column-count:3;column-gap:16px}
.split{display:grid;grid-template-columns:42% 1fr;gap:14px;align-items:start}
.compact-row{display:grid;grid-template-columns:34% 1fr;gap:12px;align-items:start}
figure{margin:0 0 10px}
figure img{width:100%;height:auto;display:block;filter:grayscale(12%);border:1px solid #111}
.story-photo-led figure img{max-height:420px;object-fit:cover}
.story-classic figure{float:right;width:46%;margin:4px 0 8px 12px}
figcaption{font:11px/1.3 'Source Serif 4',serif;color:#555;padding-top:4px}
.board-label{font:600 11px/1 Oswald,sans-serif;letter-spacing:.14em;text-transform:uppercase;margin:12px 0 4px;border-top:2px solid #111;padding-top:6px}
.board{overflow:hidden;border:1px solid #111}
.board table{border-collapse:collapse;width:100%;font:12px/1.25 Oswald,sans-serif;letter-spacing:.02em}
.board th,.board td{border-bottom:1px solid #ddd;padding:4px 6px;text-align:left}
.board th{background:#111;color:#fff;font-weight:600}
.board tr:nth-child(odd) td{background:#f3efe3}
.board tr:first-child td{font-weight:700}
@media (max-width:860px){
  .edition-grid,.lead-grid,.split,.compact-row{grid-template-columns:1fr}
  .cols-2,.cols-3{column-count:1}
  .story-classic figure{float:none;width:100%;margin:0 0 10px}
  .masthead h1{font-size:34px}
}
@page{size:A3;margin:10mm}
@media print{
  body{background:#fff;font-size:11.5px}
  .paper{box-shadow:none;max-width:none;padding:0}
  .story{break-inside:avoid}
  .story-lead{break-after:avoid}
  figure img{filter:none}
  .board{break-inside:avoid}
}
"""


def render(issue):
    src = ROOT / "issues" / issue / "issue.json"
    if not src.exists():
        src = ROOT / "public" / "issues" / issue / "issue.json"
    data = json.loads(src.read_text())
    out = ROOT / "public" / "issues" / issue
    out.mkdir(parents=True, exist_ok=True)
    (out / "issue.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))
    media_src = ROOT / "issues" / issue / "media"
    if media_src.exists():
        dest_media = out / "media"
        dest_media.mkdir(parents=True, exist_ok=True)
        for img in media_src.iterdir():
            if img.is_file():
                (dest_media / img.name).write_bytes(img.read_bytes())
    stories = []
    for i, article in enumerate(data.get("articles") or []):
        stories.append(_render_story(i, article))
    if not stories:
        stories.append("<article class='story'><p>No scored weekend events were published for this edition.</p></article>")
    try:
        day = dt.date.fromisoformat(issue)
        folio_date = day.strftime("%A %d %B %Y").upper()
    except ValueError:
        folio_date = issue
    page = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Weekend Sailing Roundup "
        + issue
        + "</title><style>"
        + newspaper_css()
        + "</style></head><body><main class='paper'><header class='masthead'>"
        "<div class='flag'>Independent Monday Edition</div><h1>The Weekend Sailing Roundup</h1>"
        "</header><div class='folio'><span>Vol. 1  ·  No. "
        + html.escape(issue)
        + "</span><span>"
        + html.escape(folio_date)
        + "</span><span>South Africa</span></div><section class='edition-grid'>"
        + "".join(stories)
        + "</section></main></body></html>"
    )
    (out / "index.html").write_text(page)
    browser = next(
        (
            path
            for path in (
                "/opt/chromium/chrome",
                "/usr/bin/google-chrome",
                "/usr/local/bin/google-chrome",
                "/usr/bin/chromium",
                "/usr/bin/chromium-browser",
            )
            if pathlib.Path(path).exists()
        ),
        "",
    )
    if browser:
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
                    "--paper-width=11.69",
                    "--paper-height=16.54",
                    (out / "index.html").resolve().as_uri(),
                ],
                timeout=50,
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
