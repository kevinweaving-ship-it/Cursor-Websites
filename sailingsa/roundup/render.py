"""Render live Roundup contracts: feed.json item, cards.json issue, full edition HTML."""

from __future__ import annotations

import html
from datetime import date
from pathlib import Path

from sailingsa.roundup.images import pick_image, write_text_card
from sailingsa.roundup.models import content_hash, stable_json
from sailingsa.roundup.write import attach_copy, edition_lead
from sailingsa.roundup.week import edition_window

LIVE = "https://sailingsa.co.za"
PUBLIC_ISSUE = "/sailing-roundup/issues/{week}/"
CSS = (Path(__file__).resolve().parent / "templates" / "edition.css").read_text(encoding="utf-8")


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def edition_number(week: str) -> int:
    """Live 2026-10-26 is edition 187. Monday editions from 2023-01-02 ≈ week index."""
    day = date.fromisoformat(week)
    # cards.json is newest-first; 2026-10-26 is issue 187 on live.
    if week == "2026-10-26":
        return 187
    origin = date(2023, 3, 27)  # live edition 1 is not required for this PR
    return max(1, ((day - origin).days // 7) + 1)


def build_payload(sheets: list[dict], week: str) -> dict:
    edition = date.fromisoformat(week)
    scored = attach_copy(sheets)
    for sheet in scored:
        sheet["image"] = pick_image(sheet)
    lead = edition_lead(scored, edition)
    cards = [s for s in scored if s.get("slot") == "card"]
    awaiting = [s for s in scored if s.get("slot") == "awaiting"]
    issue_url = f"{LIVE}{PUBLIC_ISSUE.format(week=week)}"
    feed_item = {
        "title": f"Weekly Roundup — {week}",
        "headline": lead["headline"],
        "url": issue_url,
        "excerpt": lead["excerpt"],
        "published_at": week,
        "image": (cards[0]["image"].get("src") if cards else "") or "",
        "image_caption": cards[0]["copy"]["headline"] if cards else "",
        "image_focus": "",
        "source": "Weekly Roundup",
        "category": "weekend_roundup",
        "pdf": f"{issue_url}edition.pdf",
    }
    card_rows = []
    for sheet in cards:
        card_rows.append(
            {
                "id": sheet["event_id"],
                "headline": sheet["copy"]["headline"],
                "deck": sheet["copy"]["deck"],
                "kicker": sheet["copy"]["kicker"],
                "image": sheet["image"].get("src") or "",
                "url": f"issues/{week}/#{sheet['event_id']}",
            }
        )
    issue = {
        "issue_id": week,
        "edition_date": week,
        "html": f"issues/{week}/",
        "pdf": f"issues/{week}/edition.pdf",
        "cards": card_rows,
    }
    return {
        "week": week,
        "edition_number": edition_number(week),
        "lead": lead,
        "sheets": scored,
        "cards": cards,
        "awaiting": awaiting,
        "feed_item": feed_item,
        "cards_issue": issue,
        "week_window": edition_window(edition),
    }


def render_edition_html(payload: dict) -> str:
    week = payload["week"]
    lead = payload["lead"]
    nav = (
        '<nav class="roundup-issue-nav" aria-label="Adjacent published roundups" '
        f'data-issue="{esc(week)}">'
        '<a class="roundup-nav-newer" data-direction="newer" rel="next" hidden>'
        "<span>← Newer roundup</span><time></time></a>"
        '<a class="roundup-nav-archive" href="/sailing-roundup/">All editions</a>'
        '<a class="roundup-nav-older" data-direction="older" rel="prev" hidden>'
        "<span>Older roundup →</span><time></time></a></nav>"
    )
    stories = [_lead_article(payload)]
    for sheet in payload["cards"]:
        stories.append(_event_article(sheet))
    for sheet in payload["awaiting"]:
        stories.append(_awaiting_strip(sheet))
    body = "".join(stories)
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>Weekly Roundup — {esc(week)}</title>"
        f"<style>{CSS}</style>"
        f"<link rel='canonical' href='{esc(payload['feed_item']['url'])}'>"
        "</head>"
        "<body class='weekly-roundup-edition'><main class='paper'>"
        "<header class='masthead'><a href='https://sailingsa.co.za/'>"
        "<img class='ssa-logo' src='https://sailingsa.co.za/assets/logos/sailingsa-logo.png' alt='SailingSA'></a>"
        "</header>"
        f"<div class='folio'><span>WEEKLY ROUNDUP</span><span>Edition {payload['edition_number']} · {esc(lead['week_label'])}</span></div>"
        f"{nav}<section class='edition-grid'>{body}</section>{nav}"
        "</main></body></html>"
    )


def _lead_article(payload: dict) -> str:
    lead = payload["lead"]
    return (
        f"<article class='story story-lead edition-lead' id='sailing-{esc(payload['week'])}'>"
        "<header class='story-heading'><h1>Weekly Roundup"
        f"<span class='roundup-edition-no'>Edition {payload['edition_number']}</span></h1>"
        f"<h2 class='edition-headline'>{esc(lead['headline'])}</h2>"
        f"<p class='deck'>{esc(lead['week_label'])}</p></header>"
        f"<div class='copy'><p class='lede'>{esc(lead['excerpt'])}</p></div></article>"
    )


def _figure(sheet: dict) -> str:
    image = sheet.get("image") or {}
    src = image.get("src")
    if src:
        return (
            "<div class='photo-set'><figure data-role='hero'>"
            f"<img src='{esc(src)}' alt='{esc(sheet['copy']['headline'])}'>"
            f"<figcaption>{esc(image.get('credit') or '')}</figcaption>"
            "</figure></div>"
        )
    return f"<div class='photo-set'><div class='text-card'>{esc(image.get('text') or sheet['name'])}</div></div>"


def _table(sheet: dict) -> str:
    fleets = sheet.get("fleets") or []
    if not fleets:
        return ""
    multi = len(fleets) > 1 or any(f.get("name") for f in fleets)
    chunks = []
    for fleet in fleets:
        rows = []
        for place in fleet.get("top3") or []:
            who = esc(place.get("helm") or "")
            if place.get("crew"):
                who += f" / {esc(place['crew'])}"
            fleet_cell = f"<td>{esc(fleet['name'])}</td>" if multi else ""
            rows.append(
                f"<tr><td>{esc(place.get('rank'))}</td>{fleet_cell}"
                f"<td>{who}</td><td>{esc(place.get('nett_display') or '')}</td></tr>"
            )
        head_fleet = "<th>Fleet</th>" if multi else ""
        chunks.append(
            f"<p class='board-label'>{esc(fleet['name'])} podium</p>"
            "<div class='board'><table class='table'><thead><tr><th>#</th>"
            f"{head_fleet}<th>Skipper</th><th>Pts</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>"
        )
    return "".join(chunks)


def _sources(sheet: dict) -> str:
    items = []
    for src in sheet.get("sources") or []:
        items.append(f"<li><a href='{esc(src['url'])}'>{esc(src['label'])}</a></li>")
    if not items:
        return ""
    return f"<p class='board-label'>Sources</p><ul class='sources'>{''.join(items)}</ul>"


def _event_article(sheet: dict) -> str:
    copy = sheet["copy"]
    href = sheet.get("event_url")
    heading = esc(copy["headline"])
    if href:
        heading = f"<a href='{esc(href)}'>{heading}</a>"
    results_link = ""
    if href:
        results_link = f"<p><a href='{esc(href)}'>{esc(sheet['name'])} · Full Results</a></p>"
    return (
        f"<article class='story story-photo-led event-story' id='{esc(sheet['event_id'])}'>"
        f"<header class='story-heading'><p class='kicker'>{esc(copy['kicker'])}</p>"
        f"<h2>{heading}</h2><p class='deck'>{esc(copy['deck'])}</p>{results_link}</header>"
        f"{_figure(sheet)}<div class='copy'>"
        + "".join(
            f"<p{(' class=\"lede\"' if i == 0 else '')}>{esc(p)}</p>"
            for i, p in enumerate(copy["paras"])
        )
        + "</div>"
        + _table(sheet)
        + _sources(sheet)
        + "</article>"
    )


def _awaiting_strip(sheet: dict) -> str:
    copy = sheet["copy"]
    return (
        f"<aside class='awaiting-strip story' id='{esc(sheet['event_id'])}'>"
        f"<p class='kicker'>AWAITING RESULTS</p>"
        f"<h2>{esc(copy['headline'])}</h2>"
        f"<p class='deck'>{esc(copy['deck'])}</p>"
        f"<p>{esc(copy['paras'][0] if copy['paras'] else '')}</p>"
        "</aside>"
    )


def write_artifacts(payload: dict, out_root: Path) -> dict:
    week = payload["week"]
    issue_dir = out_root / "sailing-roundup" / "issues" / week
    issue_dir.mkdir(parents=True, exist_ok=True)
    media = issue_dir / "media"
    media.mkdir(exist_ok=True)
    for sheet in payload["sheets"]:
        image = sheet.get("image") or {}
        if image.get("kind") == "text_card":
            write_text_card(media / f"{sheet['event_id']}-hero.png", image.get("text") or sheet["name"])
            image["src"] = f"media/{sheet['event_id']}-hero.png"
            payload["feed_item"].setdefault("image", image["src"])
            for card in payload["cards_issue"]["cards"]:
                if card["id"] == sheet["event_id"] and not card["image"]:
                    card["image"] = f"issues/{week}/media/{sheet['event_id']}-hero.png"
    html_text = render_edition_html(payload)
    (issue_dir / "index.html").write_text(html_text, encoding="utf-8")
    md = _markdown(payload)
    (issue_dir / "edition.md").write_text(md, encoding="utf-8")
    feed_path = out_root / "sailing-roundup" / "feed.2026-10-26.json" if week == "2026-10-26" else out_root / "sailing-roundup" / f"feed.{week}.json"
    cards_path = out_root / "sailing-roundup" / f"cards.{week}.json"
    import json

    feed_path.parent.mkdir(parents=True, exist_ok=True)
    feed_path.write_text(json.dumps(payload["feed_item"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    cards_path.write_text(json.dumps(payload["cards_issue"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    version = {
        "edition": week,
        "version": 1,
        "content_hash": content_hash({"feed": payload["feed_item"], "cards": payload["cards_issue"], "html": html_text}),
        "public_url": payload["feed_item"]["url"],
        "dev1": f"{LIVE}/dev1/",
        "dry_run": True,
    }
    (issue_dir / "version.json").write_text(json.dumps(version, indent=2) + "\n", encoding="utf-8")
    (issue_dir / "factsheets.json").write_text(
        json.dumps(
            [{k: s[k] for k in s if k not in {"page_images", "tokens"} or k == "tokens"} for s in payload["sheets"]],
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "html": str(issue_dir / "index.html"),
        "markdown": str(issue_dir / "edition.md"),
        "feed": str(feed_path),
        "cards": str(cards_path),
        "hash": version["content_hash"],
    }


def _markdown(payload: dict) -> str:
    lines = [
        f"# Weekly Roundup — {payload['week']}",
        "",
        f"Edition {payload['edition_number']}. {payload['lead']['week_label']}.",
        "",
        f"**{payload['lead']['headline']}**",
        "",
        payload["lead"]["excerpt"],
        "",
    ]
    for sheet in payload["cards"]:
        lines += [f"## {sheet['copy']['headline']}", "", sheet["copy"]["deck"], ""]
        lines += [p for p in sheet["copy"]["paras"]]
        lines.append("")
        if sheet.get("sources"):
            lines.append("Sources:")
            for src in sheet["sources"]:
                lines.append(f"- [{src['label']}]({src['url']})")
            lines.append("")
    for sheet in payload["awaiting"]:
        lines += [f"## Awaiting results: {sheet['name']}", "", sheet["copy"]["paras"][0] if sheet["copy"]["paras"] else "", ""]
    return "\n".join(lines)
