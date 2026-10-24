"""Search Console head tags for the Weekend Roundup hub and every issue.

Inserts canonical, robots, description, Open Graph, and NewsArticle / CollectionPage
JSON-LD. Does not change article bodies, decks, photos, or CSS.
"""
from __future__ import annotations

import html
import json
import pathlib
import re
from typing import Any

BASE = "https://sailingsa.co.za"
HUB = f"{BASE}/sailing-roundup/"
LATEST = f"{BASE}/sailing-roundup/latest/"
MARK_START = "<!-- ssa-gsc -->"
MARK_END = "<!-- /ssa-gsc -->"
ISSUE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def _abs(issue: str, url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"{BASE}/sailing-roundup/issues/{issue}/{url.lstrip('/')}"


def _issue_url(monday: str) -> str:
    return f"{BASE}/sailing-roundup/issues/{monday}/"


def issue_meta(monday: str, data: dict[str, Any] | None = None) -> dict[str, str]:
    data = data or {}
    articles = list(data.get("articles") or [])
    feature = next((a for a in articles if a.get("type") == "feature"), articles[0] if articles else {})
    reports = [a for a in articles if a.get("type") == "regatta_report"]
    lead = reports[0] if reports else feature
    headline = (lead.get("headline") or data.get("title") or "Weekly Roundup").strip()
    title = f"{headline} — {monday}"
    deck = (feature.get("deck") or lead.get("deck") or "").strip()
    description = deck
    if lead is not feature and lead.get("headline"):
        extra = (lead.get("headline") or "").strip()
        description = f"{deck}. {extra}".strip(". ").strip()
    if not description:
        description = f"South African sailing weekend roundup for the week ending {monday}."
    image = ""
    scan = [feature] + reports
    for article in scan:
        hero = ((article.get("hero_image") or {}) or {}).get("url") or ""
        if hero:
            image = _abs(monday, hero)
            break
    published = str(feature.get("published_at") or data.get("edition_date") or monday)[:10]
    return {
        "monday": monday,
        "title": title,
        "description": description[:297] + ("…" if len(description) > 297 else ""),
        "image": image,
        "published": published,
        "url": _issue_url(monday),
        "canonical": _issue_url(monday),
    }


def _meta_tags(*, title: str, description: str, url: str, canonical: str, image: str, og_type: str) -> str:
    lines = [
        f'<link rel="canonical" href="{_esc(canonical)}">',
        '<meta name="robots" content="index, follow">',
        f'<meta name="description" content="{_esc(description)}">',
        f'<meta property="og:type" content="{_esc(og_type)}">',
        f'<meta property="og:site_name" content="SailingSA">',
        f'<meta property="og:title" content="{_esc(title)}">',
        f'<meta property="og:description" content="{_esc(description)}">',
        f'<meta property="og:url" content="{_esc(url)}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{_esc(title)}">',
        f'<meta name="twitter:description" content="{_esc(description)}">',
    ]
    if image:
        lines.append(f'<meta property="og:image" content="{_esc(image)}">')
        lines.append(f'<meta name="twitter:image" content="{_esc(image)}">')
    return "".join(lines)


def issue_jsonld(monday: str, data: dict[str, Any] | None = None, *, canonical: str | None = None) -> dict[str, Any]:
    from news_schema import news_article_jsonld

    payload = news_article_jsonld(monday, data or {})
    if canonical:
        payload["url"] = canonical
        payload["mainEntityOfPage"] = {"@type": "WebPage", "@id": canonical}
    return payload


def hub_jsonld(newest: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "The Weekend Roundup — SailingSA",
        "url": HUB,
        "description": "Monday magazine of South African weekend sailing. One URL per week with racing.",
        "isPartOf": {"@type": "WebSite", "name": "SailingSA", "url": f"{BASE}/"},
    }
    if newest:
        payload["mainEntity"] = {"@type": "NewsArticle", "url": _issue_url(newest)}
    return payload


def issue_head(monday: str, data: dict[str, Any] | None = None, *, canonical: str | None = None) -> str:
    meta = issue_meta(monday, data)
    canon = canonical or meta["canonical"]
    tags = _meta_tags(
        title=meta["title"],
        description=meta["description"],
        url=meta["url"] if not canonical else canon,
        canonical=canon,
        image=meta["image"],
        og_type="article",
    )
    payload = issue_jsonld(monday, data, canonical=canon)
    if meta["image"] and "image" not in payload:
        payload["image"] = [meta["image"]]
    script = '<script type="application/ld+json">' + json.dumps(payload, ensure_ascii=False) + "</script>"
    return MARK_START + tags + script + MARK_END


def hub_head(newest: str | None = None) -> str:
    description = "Monday magazine of South African weekend sailing. New issue most Mondays when there was racing."
    if newest:
        description = f"{description} Latest: {_issue_url(newest)}"
    tags = _meta_tags(
        title="The Weekend Roundup — SailingSA",
        description=description,
        url=HUB,
        canonical=HUB,
        image="",
        og_type="website",
    )
    script = '<script type="application/ld+json">' + json.dumps(hub_jsonld(newest), ensure_ascii=False) + "</script>"
    return MARK_START + tags + script + MARK_END


def strip_seo_head(html_text: str) -> str:
    return re.sub(re.escape(MARK_START) + r".*?" + re.escape(MARK_END), "", html_text, flags=re.S)


def inject_seo_head(html_text: str, block: str) -> str:
    text = strip_seo_head(html_text)
    if "</head>" in text:
        return text.replace("</head>", block + "</head>", 1)
    if "<body" in text:
        return re.sub(r"(<body[^>]*>)", block + r"\1", text, count=1, flags=re.I)
    return block + text


def _load_issue_json(issue_dir: pathlib.Path) -> dict[str, Any]:
    path = issue_dir / "issue.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def patch_html_file(path: pathlib.Path, block: str) -> bool:
    if not path.is_file():
        return False
    before = path.read_text(encoding="utf-8")
    after = inject_seo_head(before, block)
    if after == before:
        return False
    path.write_text(after, encoding="utf-8")
    return True


def patch_web_root(web_root: pathlib.Path | str) -> dict[str, Any]:
    """Patch hub + /latest/ + every issue HTML. Body/CSS unchanged."""
    root = pathlib.Path(web_root)
    candidates = [
        root / "sailing-roundup",
        pathlib.Path("/var/www/sailingsa/sailing-roundup"),
        pathlib.Path(__file__).resolve().parent.parent / "public",
    ]
    changed = []
    for base in candidates:
        issues_dir = base / "issues"
        if not issues_dir.is_dir():
            continue
        mondays = sorted((p.name for p in issues_dir.iterdir() if p.is_dir() and ISSUE_RE.match(p.name)), reverse=True)
        newest = mondays[0] if mondays else None
        hub = base / "index.html"
        if patch_html_file(hub, hub_head(newest)):
            changed.append(str(hub))
        latest_html = base / "latest" / "index.html"
        if newest and latest_html.is_file():
            data = _load_issue_json(issues_dir / newest)
            if patch_html_file(latest_html, issue_head(newest, data, canonical=_issue_url(newest))):
                changed.append(str(latest_html))
        for monday in mondays:
            issue_dir = issues_dir / monday
            data = _load_issue_json(issue_dir)
            if patch_html_file(issue_dir / "index.html", issue_head(monday, data)):
                changed.append(str(issue_dir / "index.html"))
        break
    return {"ok": True, "patched": len(changed), "files": changed}
