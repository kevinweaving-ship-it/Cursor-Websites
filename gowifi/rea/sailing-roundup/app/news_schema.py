"""NewsArticle JSON-LD for weekend-roundup HTML. Not used on /regatta pages."""
from __future__ import annotations

import json
from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

SAST = ZoneInfo("Africa/Johannesburg")
PUBLISHER = {
    "@type": "NewsMediaOrganization",
    "name": "SailingSA",
    "url": "https://sailingsa.co.za/",
    "logo": {
        "@type": "ImageObject",
        "url": "https://sailingsa.co.za/assets/logos/sailingsa-logo.png",
    },
}


def _iso_monday(issue: str) -> str:
    try:
        day = date.fromisoformat(issue[:10])
    except ValueError:
        return f"{issue}T06:00:00+02:00"
    return datetime.combine(day, time(6, 0), tzinfo=SAST).isoformat()


def news_article_jsonld(issue: str, data: dict) -> dict:
    articles = data.get("articles") or []
    feature = next((a for a in articles if a.get("type") == "feature"), articles[0] if articles else {})
    headline = (feature.get("headline") or data.get("title") or "South African Sailing — The Weekend Roundup").strip()
    url = f"https://sailingsa.co.za/sailing-roundup/issues/{issue}/"
    published = feature.get("published_at") or data.get("edition_date") or issue
    date_published = _iso_monday(str(published)[:10] if published else issue)
    updated = data.get("updated_at") or datetime.now(timezone.utc).isoformat()
    image = None
    scan = [feature] + [a for a in articles if a is not feature]
    for article in scan:
        hero = ((article.get("hero_image") or {}) or {}).get("url") or ""
        if not hero:
            continue
        if hero.startswith("http"):
            image = hero
            break
        image = f"https://sailingsa.co.za/sailing-roundup/issues/{issue}/{hero.lstrip('/')}"
        break
    about = []
    for article in articles:
        if article.get("type") != "regatta_report":
            continue
        eid = article.get("event_id") or article.get("id")
        if eid and str(eid).startswith("20"):
            about.append(
                {
                    "@type": "SportsEvent",
                    "name": article.get("headline") or eid,
                    "sport": "Sailing",
                    "url": f"https://sailingsa.co.za/regatta/{eid}",
                }
            )
    payload = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": headline,
        "datePublished": date_published,
        "dateModified": updated,
        "author": {"@type": "Organization", "name": (feature.get("byline") or "SailingSA")},
        "publisher": PUBLISHER,
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "url": url,
        "articleSection": "Sailing",
        "inLanguage": "en-ZA",
    }
    if image:
        payload["image"] = [image]
    if about:
        payload["about"] = about
    return payload


def news_article_script(issue: str, data: dict) -> str:
    return (
        '<script type="application/ld+json">'
        + json.dumps(news_article_jsonld(issue, data), ensure_ascii=False)
        + "</script>"
    )
