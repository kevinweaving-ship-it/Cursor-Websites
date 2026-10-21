#!/usr/bin/env python3
"""Standalone sailing roundup builder: read-only public results, web research, JSON feed, HTML, PDF."""
import argparse
import datetime as dt
import hashlib
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
        "title": "Last Week's Roundup",
        "edition_date": issue,
        "status": "draft",
        "articles": articles,
    }
    (root / "issue.json").write_text(json.dumps(data, ensure_ascii=False, indent=2))
    (root / "sources" / "build-log.json").write_text(json.dumps(log, indent=2))
    return data, log


LAYOUTS = ("lead", "photo-led", "split", "classic", "compact")

# Single images that do not span the column must sit in the centre, never left or right.
SINGLE_IMAGE_CENTER_MARK = "/* Single non-full-width images stay centered */"
SINGLE_IMAGE_CENTER_CSS = (
    SINGLE_IMAGE_CENTER_MARK
    + """
.photo-set:not(.pair):not(.paired-then-full){justify-items:center}
.photo-set:not(.pair):not(.paired-then-full) figure{justify-self:center;margin-left:auto;margin-right:auto;width:auto;max-width:100%}
.edition-lead .photo-set{justify-items:center}
.edition-lead figure{justify-self:center;margin-left:auto;margin-right:auto}
figure{margin-left:auto;margin-right:auto;text-align:center}
figure img,.source-photo-panel{margin-left:auto;margin-right:auto}
"""
)


def apply_single_image_center_css(page: str) -> str:
    if SINGLE_IMAGE_CENTER_MARK in page:
        return page
    if "</style>" in page:
        return page.replace("</style>", SINGLE_IMAGE_CENTER_CSS + "</style>", 1)
    return page


def _image_block(block):
    url = block.get("url") or ""
    if not url:
        return ""
    caption = block.get("caption") or ""
    credit = block.get("credit") or ""
    if credit and credit.lower() not in caption.lower():
        caption = (caption + " Photo: " + credit).strip()
    region = block.get("source_region")
    if region:
        x, y, w, h = region
        sw, sh = block["source_dimensions"]
        label = html.escape(block.get("alt") or caption or "", quote=True)
        clip = "photo-" + hashlib.sha256((url + repr(region)).encode()).hexdigest()[:16]
        return (
            f'<figure><svg class="source-photo-panel" role="img" aria-label="{label}" viewBox="{x} {y} {w} {h}" xmlns="http://www.w3.org/2000/svg">'
            f'<title>{label}</title><defs><clipPath id="{clip}" clipPathUnits="userSpaceOnUse"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath></defs>'
            f'<image href="{html.escape(url, quote=True)}" x="0" y="0" width="{sw}" height="{sh}" clip-path="url(#{clip})"/></svg>'
            f"<figcaption>{html.escape(caption)}</figcaption></figure>"
        )
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


def _cited_paragraph(text: str) -> str:
    escaped = html.escape(text or "")
    escaped = re.sub(
        r"\[(\d+)\]",
        r'<sup class="cite"><a href="#src-\1">\1</a></sup>',
        escaped,
    )
    return escaped


def _photo_set(images: list[str], media_layout: str = "") -> str:
    if not images:
        return ""
    images = images[:4]
    cls = "photo-set pair" if len(images) > 1 else "photo-set"
    if media_layout == "paired-then-full":
        cls += " paired-then-full"
    return "<div class='" + cls + "'>" + "".join(images) + "</div>"


def _sources_block(article):
    cites = article.get("citations") or [{"url": u} for u in article.get("sources", [])]
    aid = html.escape(article.get("id") or article.get("event_id") or "edition", quote=True)
    links = []
    for index, cite in enumerate(cites, 1):
        url = cite.get("url") if isinstance(cite, dict) else cite
        if not url:
            continue
        label = (
            ("Event calendar" if article.get("type") == "feature" else "Full event results")
            if index == 1
            else ((cite.get("title") if isinstance(cite, dict) else "") or "Source report")
        )
        links.append(
            f'<li id="{aid}-src-{index}"><a href="{html.escape(url, quote=True)}">{html.escape(label)}</a></li>'
        )
    return (
        '<aside class="source-notes" aria-label="Sources"><span class="sources-label">Sources &amp; results</span><ol class="sources">'
        + "".join(links)
        + "</ol></aside>"
        if links
        else ""
    )


def _story_parts(article):
    images = []
    paras = []
    board = []
    for block in article.get("blocks") or []:
        kind = block.get("type")
        if kind == "image":
            images.append(_image_block(block))
        elif kind == "paragraph":
            paras.append("<p>" + _cited_paragraph(block.get("text") or "") + "</p>")
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
    layout = _layout_name(index, article)
    images, paras, board = _story_parts(article)
    aid = html.escape(article.get("id") or article.get("event_id") or "", quote=True)
    headline = html.escape(article.get("headline") or "")
    lead = article.get("type") == "feature"
    deck = article.get("deck") or ""
    if not lead and "·" in deck:
        deck = " · ".join(part.strip() for part in deck.split("·")[2:])
    kicker = html.escape(article.get("kicker") or article.get("class_name") or "")
    title_tag = "h1" if lead else "h2"
    header = (
        '<header class="story-heading">'
        + ("" if lead else '<p class="kicker">' + kicker + "</p>")
        + f"<{title_tag}>{headline}</{title_tag}>"
        + (('<p class="deck">' + html.escape(deck) + "</p>") if deck else "")
    )
    if lead:
        date = article.get("published_at") or ""
        try:
            date = dt.date.fromisoformat(date).strftime("%-d %B %Y")
        except ValueError:
            pass
        header += (
            '<p class="byline">By '
            + html.escape(article.get("byline") or "SailingSA")
            + '<span aria-hidden="true"> · </span>Published '
            + html.escape(date)
            + "</p>"
        )
    header += "</header>"
    copy = "".join(paras)
    photos = _photo_set(images, article.get("media_layout") or ("paired-then-full" if len(images) > 1 else ""))
    content = header + photos + '<div class="copy">' + copy + "</div>" + "".join(board) + _sources_block(article)
    return (
        f'<article class="story story-{layout} {"edition-lead" if lead else "event-story"}" id="{aid}">'
        + content
        + "</article>"
    )


def newspaper_css():
    return """
@import url("https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,700;1,500&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap");
:root{--ink:#1e293b;--navy:#001f3f;--muted:#334155;--paper:#f5f7fa;--card:#fff}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:18px/1.6 'Source Serif 4',Georgia,serif}
.paper{max-width:860px;margin:0 auto;background:var(--card)}
.masthead{display:flex;align-items:center;gap:16px;background:var(--navy);color:#fff;padding:14px 28px}
.masthead a{display:flex;align-items:center}
.ssa-logo{height:52px;width:auto;display:block}
.masthead .flag{font:600 11px/1 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;letter-spacing:.22em;text-transform:uppercase;color:#fff;margin:0 0 4px}
.masthead h1{font:700 34px/1 'Playfair Display',Georgia,serif;margin:0;letter-spacing:.02em;color:#fff}
.folio{display:flex;justify-content:space-between;padding:10px 28px;border-bottom:1px solid #e0e0e0;font:12px/1.3 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;letter-spacing:.04em;text-transform:uppercase;color:#64748b}
.edition-grid{display:flex;flex-direction:column;gap:0;padding:0 28px 72px}
.story{break-inside:avoid;page-break-inside:avoid;border-top:1px solid #e0e0e0;margin:36px 0 0;padding:28px 0 8px;background:#fff}
.story-lead{border-top:none;margin-top:18px;padding-top:8px}
.kicker{font:700 12px/1 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;letter-spacing:.14em;margin:0 0 8px;color:#6B2C91}
h2{font:700 32px/1.2 'Playfair Display',Georgia,serif;margin:0 0 10px;color:var(--navy)}
.story-lead h2{font-size:clamp(32px,4.5vw,44px)}
.story-photo-led h2{font-size:34px}
.story-split h2{font-size:32px}
.story-classic h2{font-size:30px}
.story-compact h2{font-size:28px}
.deck{margin:0 0 8px;color:var(--muted);font:italic 17px/1.4 'Playfair Display',Georgia,serif}
.byline{margin:0 0 14px;font:600 11px/1 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;letter-spacing:.08em;text-transform:uppercase;color:#64748b}
.banner{text-align:left}
.copy p{margin:0 0 12px}
.copy .lede{font-size:19px}
.cols-2{column-count:1}
.cols-3{column-count:1}
.split{display:grid;grid-template-columns:1fr;gap:16px}
.compact-row{display:grid;grid-template-columns:1fr;gap:16px}
figure{margin:0 auto 14px;text-align:center}
figure img,.source-photo-panel{width:100%;height:auto;display:block;margin-left:auto;margin-right:auto}
.photo-set{display:grid;grid-template-columns:1fr;gap:12px;margin:0 auto 14px;justify-items:center}
.photo-set:not(.pair):not(.paired-then-full){justify-items:center}
.photo-set:not(.pair):not(.paired-then-full) figure{justify-self:center;margin-left:auto;margin-right:auto;width:auto;max-width:100%}
.photo-set.pair{grid-template-columns:1fr}
.edition-lead .photo-set{justify-items:center}
.edition-lead figure{justify-self:center;margin-left:auto;margin-right:auto}
.story-photo-led figure img{max-height:480px;object-fit:cover}
.story-classic figure{float:none;width:auto;max-width:100%;margin:0 auto 14px}
figcaption{font:12px/1.4 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#64748b;padding-top:6px}
.cite{font-size:11px;line-height:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
.cite a{color:#6B2C91;text-decoration:none}
.sources{margin:18px 0 0;padding-left:18px;font:12px/1.45 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#64748b}
.sources a{color:#334155}
.board-label{font:700 12px/1 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;letter-spacing:.12em;text-transform:uppercase;margin:18px 0 8px;color:var(--navy)}
.board{overflow:hidden;border:2px solid var(--navy);border-radius:8px}
.board table{border-collapse:collapse;width:100%;font:14px/1.35 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
.board th,.board td{border-bottom:1px solid #e0e0e0;padding:8px 10px;text-align:left}
.board th{background:var(--navy);color:#fff;font-weight:600}
.board tr:nth-child(odd) td{background:#f8fafc}
.board tr:first-child td{font-weight:700}
@media (min-width:700px){
  .photo-set.pair{grid-template-columns:1fr 1fr}
}
@media (max-width:860px){
  .edition-grid{display:flex;flex-direction:column;padding:0 16px 48px}
  .masthead{padding:12px 16px}
  .lead-grid,.split,.compact-row{grid-template-columns:1fr}
  .cols-2,.cols-3{column-count:1}
  .photo-set.pair{grid-template-columns:1fr}
  .story-classic figure{float:none;width:100%;margin:0 auto 10px}
  .masthead h1{font-size:26px}
  .ssa-logo{height:40px}
}
@page{size:A3;margin:12mm}
@media print{
  body{background:#fff;font-size:12px}
  .paper{box-shadow:none;max-width:none}
  .story{break-inside:avoid}
  .story-lead{break-after:avoid}
  figure img{filter:none;width:auto;max-width:100%;margin-left:auto;margin-right:auto}
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
        "<title>Sailing — "
        + issue
        + "</title><style>"
        + newspaper_css()
        + "@media print{.story figure img{max-height:190mm;width:auto;max-width:100%;object-fit:contain}.story table{break-inside:avoid}}"
        + "</style></head><body><main class='paper'><header class='masthead'>"
        "<a href='https://sailingsa.co.za/'><img class='ssa-logo' src='https://sailingsa.co.za/assets/logos/sailingsa-logo.png' alt='SailingSA'></a>"
        "<div><p class='flag'>SailingSA</p><h1>Sailing</h1></div>"
        "</header><div class='folio'><span>"
        + html.escape(folio_date)
        + "</span><span>South Africa</span></div><section class='edition-grid'>"
        + "".join(stories)
        + "</section></main></body></html>"
    )
    page = apply_single_image_center_css(page)
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
