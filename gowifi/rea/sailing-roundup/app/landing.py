#!/usr/bin/env python3
"""Write the independent publication landing page, latest pointer, and feed."""
from __future__ import annotations

import html
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PUBLIC_BASE = "https://sailingsa.co.za/sailing-roundup"


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
                "title": data.get("title") or "Weekend Sailing Roundup",
                "edition_date": data.get("edition_date") or folder.name,
                "articles": len(articles),
                "lead": (articles[0].get("headline") if articles else ""),
                "html": f"issues/{folder.name}/",
                "pdf": f"issues/{folder.name}/edition.pdf",
                "json": f"issues/{folder.name}/issue.json",
                "hero": cards[0]["image"] if cards else ((articles[0].get("hero_image") or {}) if articles else {}).get("url"),
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
        "<title>Sailing — SailingSA</title>"
        "<style>body{margin:0;color:#1e293b;background:#f5f7fa;font:17px/1.5 Georgia,serif}"
        ".bar{display:flex;align-items:center;gap:14px;background:#001f3f;color:#fff;padding:14px 24px}"
        ".bar img{height:48px}.bar h1{margin:0;font:700 28px/1 Georgia,serif}"
        ".wrap{max-width:1080px;margin:auto;padding:28px 24px}h2,h3{font-family:Georgia,serif;color:#001f3f}"
        ".cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:16px}"
        ".card{display:block;background:#fff;border:2px solid #001f3f;border-radius:8px;padding:0 0 12px;color:#1e293b;text-decoration:none}"
        ".card img{width:100%;height:140px;object-fit:cover;display:block}.card strong{display:block;padding:8px 10px 0;font:12px/1 sans-serif;letter-spacing:.08em;color:#6B2C91}"
        ".card h3{margin:6px 10px;font-size:18px}.card p{margin:0 10px;color:#334155;font-size:14px}"
        "section{border-top:1px solid #e0e0e0;padding:22px 0}a{color:#001f3f}</style></head>"
        "<body><header class='bar'><a href='https://sailingsa.co.za/'><img src='https://sailingsa.co.za/assets/logos/sailingsa-logo.png' alt='SailingSA'></a><h1>Sailing</h1></header>"
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
