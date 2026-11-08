"""NewsArticle JSON-LD for weekend-roundup HTML. Not used on /regatta pages.

SportsEvent in about[] is only emitted when Google's Events rich-result
required fields are present: name, startDate, and location. Incomplete
SportsEvent markup is a Search Console ERROR.
"""
from __future__ import annotations

import json
import re
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
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")
SLUG_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-([a-z0-9]+)-", re.I)


def _iso_monday(issue: str) -> str:
    try:
        day = date.fromisoformat(issue[:10])
    except ValueError:
        return f"{issue}T06:00:00+02:00"
    return datetime.combine(day, time(6, 0), tzinfo=SAST).isoformat()


def _iso_day(value: object) -> str:
    text = str(value or "").strip()
    match = DATE_RE.match(text)
    if not match:
        return ""
    try:
        date.fromisoformat(match.group(1))
    except ValueError:
        return ""
    return match.group(1)


def _event_id(article: dict) -> str:
    eid = str(article.get("event_id") or article.get("id") or "").strip()
    return eid if eid.startswith("20") else ""


def _venue_name(article: dict, eid: str) -> str:
    for key in ("club_name", "host_club_name", "venue", "club"):
        name = str(article.get(key) or "").strip()
        if name:
            return name
    match = SLUG_RE.match(eid)
    if match:
        return match.group(2).upper()
    return ""


def sports_event(article: dict) -> dict | None:
    """Complete SportsEvent or None. Never emit startDate/location-less Events markup."""
    eid = _event_id(article)
    if not eid:
        return None
    start = _iso_day(article.get("start_date") or article.get("start") or article.get("event_start") or eid)
    venue = _venue_name(article, eid)
    if not start or not venue:
        return None
    location: dict = {
        "@type": "Place",
        "name": venue,
        "address": {"@type": "PostalAddress", "addressCountry": "ZA"},
    }
    club_slug = str(article.get("host_club_slug") or "").strip()
    if club_slug:
        location["url"] = f"https://sailingsa.co.za/club/{club_slug}"
    name = (article.get("headline") or article.get("event_name") or eid).strip()
    payload: dict = {
        "@type": "SportsEvent",
        "name": name,
        "sport": "Sailing",
        "url": f"https://sailingsa.co.za/regatta/{eid}",
        "startDate": start,
        "location": location,
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
    }
    description = (article.get("headline") or article.get("deck") or "").strip()
    if description:
        payload["description"] = description
    end = _iso_day(article.get("end_date") or article.get("end") or article.get("event_end"))
    if end:
        payload["endDate"] = end
    return payload


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
        event = sports_event(article)
        if event:
            about.append(event)
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
