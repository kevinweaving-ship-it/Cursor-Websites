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
        "title": GOLD_ISSUE_TITLE,
        "edition_date": issue,
        "status": "draft",
        "articles": articles,
    }
    (root / "issue.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    (root / "sources" / "build-log.json").write_text(json.dumps(log, indent=2))
    return data, log


LAYOUTS = ("lead", "photo-led", "split", "classic", "compact")
GOLD_ISSUE_TITLE = "South African Sailing — The Weekend Roundup"
GOLD_PAGE_NAME = "The Weekend Roundup"
GOLD_HEADER = """<header class="site-header roundup-site-header" aria-label="SailingSA">
  <div class="container">
    <a class="logo js-go-home" href="https://sailingsa.co.za/" title="Home – SailingSA">
      <img src="https://sailingsa.co.za/assets/logos/sailingsa-logo.png" alt="SailingSA">
    </a>
    <a class="roundup-home" href="https://sailingsa.co.za/" title="Back to Home">
      <img src="https://sailingsa.co.za/assets/back-to-home.png?v=2" alt="Back to Home">
    </a>
  </div>
</header>
"""


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


def _cited_paragraph(text: str, article_id: str = "") -> str:
    escaped = html.escape(text or "")
    prefix = (article_id + "-src-") if article_id else "src-"
    escaped = re.sub(
        r"\[(\d+)\]",
        r'<sup class="cite"><a href="#' + prefix + r'\1">\1</a></sup>',
        escaped,
    )
    return escaped


def _photo_set(images: list[str]) -> str:
    if not images:
        return ""
    cls = "photo-set pair paired-then-full" if len(images) > 1 else "photo-set"
    return "<div class='" + cls + "'>" + "".join(images) + "</div>"


def _story_parts(article):
    images = []
    paras = []
    board = []
    aid = article.get("id") or article.get("event_id") or ""
    for block in article.get("blocks") or []:
        kind = block.get("type")
        if kind == "image":
            images.append(_image_block(block))
        elif kind == "paragraph":
            paras.append("<p>" + _cited_paragraph(block.get("text") or "", aid) + "</p>")
        elif kind == "heading":
            board.append("<h3 class='board-label'>" + html.escape(block.get("text") or "Leaderboard") + "</h3>")
        elif kind == "results":
            board.append(_results_block(block))
    if paras:
        paras[0] = paras[0].replace("<p>", "<p class='lede'>", 1)
    return images, paras, board


def _layout_name(index, article):
    chosen = article.get("layout")
    if chosen in LAYOUTS:
        return chosen
    if article.get("type") == "feature":
        return "lead"
    return LAYOUTS[(index % 4) + 1]


def _render_story(index, article):
    """Gold 2026-09-28 story chrome: heading + photos + copy + boards."""
    layout = _layout_name(index, article)
    images, paras, board = _story_parts(article)
    photos = _photo_set(images)
    aid = html.escape(article.get("id") or article.get("event_id") or "")
    copy = "<div class='copy'>" + "".join(paras) + "</div>" if paras else ""
    if layout == "lead" or article.get("type") == "feature":
        deck = html.escape(article.get("deck") or "")
        inner = (
            '<header class="story-heading"><h1>'
            + GOLD_PAGE_NAME
            + "</h1>"
            + (('<p class="deck">' + deck + "</p>") if deck else "")
            + "</header>"
            + copy
        )
        return '<article class="story story-lead edition-lead" id="' + aid + '">' + inner + "</article>"
    kicker = html.escape(article.get("kicker") or (article.get("class_name") or "Regatta").upper())
    headline = html.escape(article.get("headline") or "")
    deck = html.escape(article.get("deck") or "")
    inner = (
        '<header class="story-heading"><p class="kicker">'
        + kicker
        + "</p><h2>"
        + headline
        + "</h2>"
        + (('<p class="deck">' + deck + "</p>") if deck else "")
        + "</header>"
        + photos
        + copy
        + "".join(board)
    )
    return '<article class="story story-' + layout + ' event-story" id="' + aid + '">' + inner + "</article>"


def newspaper_css():
    return (pathlib.Path(__file__).with_name("gold_default.css")).read_text()


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
    page = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>"
        + GOLD_PAGE_NAME
        + " — "
        + issue
        + "</title><style>"
        + newspaper_css()
        + "</style>"
    )
    try:
        from news_schema import news_article_script

        page += news_article_script(issue, data)
    except Exception:
        pass
    page += (
        "</head><body>"
        + GOLD_HEADER
        + "<main class='paper'><section class='edition-grid'>"
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
