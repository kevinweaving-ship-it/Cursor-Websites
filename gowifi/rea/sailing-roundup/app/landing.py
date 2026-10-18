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
                "hero": ((articles[0].get("hero_image") or {}) if articles else {}).get("url"),
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
    cards = []
    for item in issues:
        cards.append(
            "<article class='issue'>"
            f"<h2><a href='{html.escape(item['html'], quote=True)}'>{html.escape(item['title'])} — {html.escape(item['edition_date'])}</a></h2>"
            f"<p>{html.escape(item.get('lead') or '')}</p>"
            f"<p><a href='{html.escape(item['html'], quote=True)}'>Open landing page</a> · "
            f"<a href='{html.escape(item['pdf'], quote=True)}'>Download PDF</a></p>"
            "</article>"
        )
    page = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>Weekend Sailing Roundup</title>"
        "<style>body{margin:0;color:#162338;background:#fff;font:16px/1.6 'DM Sans',sans-serif}"
        ".wrap{max-width:960px;margin:auto;padding:36px 24px}h1,h2{font-family:Georgia,serif}"
        "article{border-bottom:1px solid #ddd;padding:18px 0}a{color:#16385a}</style></head>"
        "<body><main class='wrap'><header><strong>INDEPENDENT PUBLICATION</strong>"
        "<h1>Weekend Sailing Roundup</h1>"
        "<p>Monday landing page and PDF edition. Built independently; published at sailingsa.co.za/sailing-roundup.</p>"
        "</header>" + "".join(cards) + "</main></body></html>"
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
