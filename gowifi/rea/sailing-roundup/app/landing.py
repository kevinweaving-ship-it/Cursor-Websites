#!/usr/bin/env python3
"""Write the independent publication landing page, latest pointer, and feed."""
from __future__ import annotations

import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PUBLIC_BASE = "https://sailingsa.co.za/sailing-roundup"


def _abs_issue_image(folder_name: str, url: str) -> str:
    if not url:
        return ""
    if url.startswith("http") or url.startswith("issues/"):
        return url
    return f"issues/{folder_name}/{url.lstrip('/')}"


def edition_hero(folder_name: str, articles: list[dict], cards: list[dict]) -> str:
    """Weekend hero is the feature photograph, not the first event-logo card."""
    feature = next((a for a in articles if a.get("type") == "feature"), None)
    if feature:
        url = ((feature.get("hero_image") or {}) or {}).get("url") or ""
        if url:
            return _abs_issue_image(folder_name, url)
    for card in cards:
        if card.get("image"):
            return card["image"]
    return ""


def _issues() -> list[dict]:
    root = ROOT / "public" / "issues"
    if not root.exists():
        return []
    out = []
    for folder in sorted(root.iterdir(), reverse=True):
        if not folder.is_dir():
            continue
        data_path = folder / "issue.json"
        if not data_path.exists():
            continue
        data = json.loads(data_path.read_text())
        articles = data.get("articles") or []
        cards = []
        for article in articles:
            if article.get("type") != "regatta_report":
                continue
            hero = ((article.get("hero_image") or {}) or {}).get("url") or ""
            if hero and not hero.startswith("http"):
                hero = f"issues/{folder.name}/{hero}"
            cards.append(
                {
                    "id": article.get("id"),
                    "headline": article.get("headline") or "",
                    "deck": article.get("deck") or "",
                    "kicker": article.get("kicker") or "",
                    "image": hero,
                    "url": f"issues/{folder.name}/#{article.get('id')}",
                }
            )
        (folder / "cards.json").write_text(json.dumps(cards, indent=2, ensure_ascii=False))
        out.append(
            {
                "issue_id": data.get("issue_id") or folder.name,
                "title": data.get("title") or "South African Sailing — The Weekend Roundup",
                "edition_date": data.get("edition_date") or folder.name,
                "articles": len(articles),
                "lead": (articles[0].get("headline") if articles else ""),
                "html": f"issues/{folder.name}/",
                "pdf": f"issues/{folder.name}/edition.pdf",
                "json": f"issues/{folder.name}/issue.json",
                "hero": edition_hero(folder.name, articles, cards),
                "cards": cards,
            }
        )
    return out


def write_public_index() -> dict:
    issues = _issues()
    public = ROOT / "public"
    public.mkdir(parents=True, exist_ok=True)
    latest = issues[0] if issues else None
    (public / "latest.json").write_text(json.dumps(latest, indent=2, ensure_ascii=False) if latest else "{}")
    feed = []
    for item in issues[:6]:
        feed.append(
            {
                "title": f"{item['title']} — {item['edition_date']}",
                "url": f"{PUBLIC_BASE}/{item['html']}",
                "excerpt": item.get("lead") or f"{item['articles']} weekend reports",
                "published_at": item["edition_date"],
                "image": item.get("hero"),
                "source": "Weekend Sailing Roundup",
                "category": "weekend_roundup",
                "pdf": f"{PUBLIC_BASE}/{item['pdf']}",
            }
        )
    (public / "feed.json").write_text(json.dumps(feed, indent=2, ensure_ascii=False))
    archive = []
    for item in issues:
        archive.append(
            {
                "title": f"{item['title']} — {item['edition_date']}",
                "url": f"{PUBLIC_BASE}/{item['html']}",
                "excerpt": item.get("lead") or f"{item['articles']} weekend reports",
                "published_at": item["edition_date"],
                "image": item.get("hero") or "",
                "source": "Weekend Sailing Roundup",
                "category": "weekend_roundup",
                "pdf": f"{PUBLIC_BASE}/{item['pdf']}",
            }
        )
    (public / "archive.json").write_text(json.dumps(archive, indent=2, ensure_ascii=False))
    (public / "cards.json").write_text(
        json.dumps({"issues": [{k: item.get(k) for k in ("issue_id", "edition_date", "html", "pdf", "cards")} for item in issues]}, indent=2)
    )
    cards = []
    for item in issues:
        event_cards = []
        for card in item.get("cards") or []:
            img = (
                f"<img src='{html.escape(card['image'], quote=True)}' alt=''>"
                if card.get("image")
                else ""
            )
            event_cards.append(
                "<a class='card' href='"
                + html.escape(card["url"], quote=True)
                + "'>"
                + img
                + "<strong>"
                + html.escape(card.get("kicker") or "")
                + "</strong><h3>"
                + html.escape(card.get("headline") or "")
                + "</h3><p>"
                + html.escape(card.get("deck") or "")
                + "</p></a>"
            )
        cards.append(
            "<section class='issue'>"
            f"<h2><a href='{html.escape(item['html'], quote=True)}'>{html.escape(item['title'])} — {html.escape(item['edition_date'])}</a></h2>"
            f"<p><a href='{html.escape(item['html'], quote=True)}'>Open edition</a> · "
            f"<a href='{html.escape(item['pdf'], quote=True)}'>PDF</a></p>"
            "<div class='cards'>"
            + "".join(event_cards)
            + "</div></section>"
        )
    page = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>The Weekend Roundup — SailingSA</title>"
        '<style>@import url("https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600&display=swap");'
        ":root{--ink:#172b3a;--navy:#001f3f;--muted:#697078;--paper:#f2f0eb;--rule:#d9d7d1;--accent:#8b6c43}"
        "body{margin:0;color:var(--ink);background:var(--paper);font:18px/1.6 'Source Serif 4',Georgia,serif}"
        ".roundup-site-header{position:sticky;top:0;z-index:40;width:100%;background:#001f3f;border-bottom:1px solid rgba(255,255,255,.1);height:80px}"
        ".roundup-site-header .container{max-width:1200px;height:80px;margin:0 auto;padding:0 16px;display:flex;align-items:center;justify-content:space-between;gap:12px}"
        ".roundup-site-header .logo img{display:block;height:68px;width:auto;max-width:46vw}"
        ".roundup-home img{display:block;height:46px;width:auto;max-width:100%}"
        ".wrap{max-width:1040px;margin:auto;padding:36px 5.5% 80px}h2,h3{font-family:'Playfair Display',Georgia,serif;font-weight:500;color:var(--navy)}"
        "h2{font-size:clamp(26px,3vw,36px);letter-spacing:-.02em}h2 a{color:var(--navy);text-decoration:none}"
        ".cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:16px}"
        ".card{display:block;background:#fff;border-top:2px solid var(--navy);padding:0 0 14px;color:var(--ink);text-decoration:none}"
        ".card img{width:100%;height:140px;object-fit:cover;display:block}.card strong{display:block;padding:12px 12px 0;font:650 11px/1.3 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;letter-spacing:.18em;text-transform:uppercase;color:var(--accent)}"
        ".card h3{margin:8px 12px;font-size:20px;line-height:1.25}.card p{margin:0 12px;color:var(--muted);font-size:13px}"
        "section{border-top:1px solid var(--rule);padding:28px 0}section:first-child{border-top:0;padding-top:0}"
        "a{color:var(--accent)}</style></head>"
        '<body><header class="site-header roundup-site-header" aria-label="SailingSA">'
        '<div class="container"><a class="logo js-go-home" href="https://sailingsa.co.za/" title="Home – SailingSA">'
        '<img src="https://sailingsa.co.za/assets/logos/sailingsa-logo.png" alt="SailingSA"></a>'
        '<a class="roundup-home" href="https://sailingsa.co.za/" title="Back to Home">'
        '<img src="https://sailingsa.co.za/assets/back-to-home.png?v=2" alt="Back to Home"></a></div></header>'
        "<main class='wrap'>" + "".join(cards) + "</main></body></html>"
    )
    (public / "index.html").write_text(page)
    latest_dir = public / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    if latest:
        src = ROOT / "public" / "issues" / latest["issue_id"] / "index.html"
        pdf = ROOT / "public" / "issues" / latest["issue_id"] / "edition.pdf"
        if src.exists():
            (latest_dir / "index.html").write_text(src.read_text())
        if pdf.exists():
            (latest_dir / "edition.pdf").write_bytes(pdf.read_bytes())
    return {"issues": len(issues), "latest": latest["issue_id"] if latest else None, "feed": str(public / "feed.json")}


if __name__ == "__main__":
    print(json.dumps(write_public_index()))
