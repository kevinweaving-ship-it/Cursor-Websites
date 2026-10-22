#!/usr/bin/env python3
"""Step 3: sports-desk editor writes Last Week's Roundup from locked facts + stored heroes.

The writer is a United Robots / Wordsmith-style desk: every sentence is a data
point. ChatGPT is not the default. Generic filler is discarded. Official-only
plus the stored photograph is a pass.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import os

from ai_tools import available as ai_available, chat as ai_chat, load_env
from desk_editor import (
    edit_event,
    is_generic,
    photo_caption,
    qa,
    week_fact_card,
    week_fact_from_report,
    week_lead_errors,
)
from event_rewrite import (
    citation_index,
    deck_from_facts,
    facts_from_rows,
    layout_for,
    strip_cite_marks,
    unique_headline,
)
from evidence_pipeline import feature, unlisted_event_names
from events_weekend import saturday_sunday


def _as_monday(monday):
    if isinstance(monday, str):
        return __import__("datetime").date.fromisoformat(str(monday)[:10])
    return monday


def raw_context(rec: dict, facts: dict, hero: dict | None = None) -> dict:
    """Headline + context starting point for one scored event."""
    equals = rec.get("equals") or {}
    return {
        "slug": rec.get("slug") or facts.get("slug") or "",
        "headline": unique_headline(facts),
        "name": equals.get("name") or facts.get("title") or rec.get("name") or "",
        "host": equals.get("host") or facts.get("club") or "",
        "start": equals.get("start") or facts.get("start") or "",
        "end": equals.get("end") or facts.get("end") or "",
        "url": equals.get("url") or facts.get("url") or rec.get("url") or "",
        "winner": facts.get("winner") or rec.get("winner") or "",
        "entries": facts.get("entries") or rec.get("entries") or 0,
        "races": facts.get("races") or 0,
        "fleets": equals.get("fleets") or facts.get("fleets") or [],
        "leaderboards": equals.get("leaderboards") or facts.get("class_leaderboards") or [],
        "hero": (hero or {}).get("local_path") or "",
        "hero_title": (hero or {}).get("title") or "",
        "hero_source": (hero or {}).get("source_url") or "",
        "third_party": False,
    }


def media_note(hero: dict | None, facts: dict) -> str:
    """Desk mention of the stored photograph — caption-quality, never system speak."""
    from desk_editor import photo_line

    return photo_line(hero, facts)


def _required_tokens(facts: dict) -> list[str]:
    winner = (facts.get("winner_helm") or (facts.get("winner") or "").split(" and ")[0] or "").strip()
    token = winner.split()[0] if winner else ""
    return [t for t in (token, facts.get("title") or "") if t and t != "The"]


def _locked(text: str, facts: dict) -> bool:
    blob = (text or "").lower()
    return all(tok.lower() in blob for tok in _required_tokens(facts))


def _system_prompt() -> str:
    return (
        "You are a newspaper sports editor. Rewrite only from the supplied facts. "
        "Do not invent sailors, scores, clubs, or colour. "
        "No generic phrases. No 'exciting weekend'. Specific names, venue, points."
    )


def _week_system_prompt() -> str:
    return (
        "You are a newspaper sports editor writing the introduction to Last Week's Roundup. "
        "Use only the structured event facts. Group by venue or sporting significance. "
        "Do not tally events. Do not paste headlines. Do not invent conditions, drama, "
        "identities, or results. Provisional standings stay provisional. "
        "Name every scored event exactly. Unlisted events go in a separate paragraph "
        "and must not be described as having published results."
    )


def _week_accepts(text: str, facts: dict) -> bool:
    cards = list(facts.get("week_cards") or [])
    unlisted = list(facts.get("unlisted") or [])
    return bool(text) and not week_lead_errors(text, cards, unlisted)


def polish_copy(kind: str, context: dict, facts: dict, draft: str, polish=None) -> tuple[str | None, str]:
    """Optional extra pass. The desk draft is the article unless this stays locked and specific."""
    week = kind == "week feature" or bool(facts.get("week_cards"))
    if polish is not None:
        text = polish(kind, context, facts, draft)
        if not text:
            return None, "desk"
        if week:
            return (text.strip(), "injected") if _week_accepts(text, facts) else (None, "desk")
        if _locked(text, facts) and not is_generic(text) and not qa(text, facts):
            return text.strip(), "injected"
        return None, "desk"
    if os.getenv("ROUNDUP_USE_AI") != "1":
        return None, "desk"
    load_env()
    prompt = _week_system_prompt() if week else _system_prompt()
    user = kind + "\n" + json.dumps({"context": context, "draft": draft}, ensure_ascii=False)
    text, provider = ai_chat(prompt, user)
    if not text:
        return None, "desk"
    if week:
        return (text.strip(), provider) if _week_accepts(text, facts) else (None, "desk")
    if _locked(text, facts) and not is_generic(text) and not qa(text, facts):
        return text.strip(), provider
    return None, "desk"


def ai_polish(kind: str, context: dict, facts: dict, draft: str) -> str | None:
    """Optional AI call. Must keep the locked facts or it is discarded."""
    text, _provider = polish_copy(kind, context, facts, draft)
    return text


def _article_images(hero: dict | None) -> list[dict]:
    """Up to four stored photographs. Never invent fillers for empty slots."""
    if not hero:
        return []
    images = [item for item in (hero.get("images") or []) if isinstance(item, dict)]
    if not images and hero.get("status") == "pass" and (hero.get("local_path") or hero.get("url")):
        images = [hero]
    out = []
    seen = set()
    for item in images:
        if (item.get("status") or "pass") not in ("pass", "ok", ""):
            continue
        path = item.get("local_path") or item.get("url") or ""
        if not path or path in seen:
            continue
        seen.add(path)
        out.append(item)
        if len(out) >= 4:
            break
    return out


def _image_block(item: dict, facts: dict, rec: dict) -> dict:
    block = {
        "type": "image",
        "url": item.get("local_path") or item.get("url") or "",
        "alt": item.get("title") or facts.get("title") or rec.get("name") or "",
        "caption": photo_caption(item, facts),
        "credit": item.get("credit") or "Event photography",
        "source_url": item.get("source_url") or facts.get("url") or "",
        "rights_status": "source_attributed",
    }
    if item.get("source_region") and not item.get("cropped"):
        block["source_region"] = item["source_region"]
        block["source_dimensions"] = item.get("source_dimensions")
    return block


def write_event_article(issue: str, rec: dict, facts: dict, hero: dict | None, layout: str = "classic", polish=None) -> dict:
    """Write one event article from official data + stored hero. Third-party is optional."""
    ctx = raw_context(rec, facts, hero)
    cluster = {"articles": [], "count": 0}
    cites = citation_index(cluster, facts)
    paras = edit_event(facts, hero)
    polished, writer = polish_copy("event article", ctx, facts, " ".join(paras), polish=polish)
    if polished:
        paras = [p.strip() for p in re.split(r"\n{2,}", polished) if p.strip()] or paras
    paras = [strip_cite_marks(p) for p in paras]
    images = _article_images(hero)
    blocks = [_image_block(item, facts, rec) for item in images]
    for text in paras:
        blocks.append({"type": "paragraph", "text": text})
    cols, table = facts.get("leaderboard") or ([], [])
    blocks.append({"type": "results", "source_event_url": facts.get("url") or "", "columns": cols, "rows": table, "as_of": issue})
    third_party = False
    first = images[0] if images else None
    return {
        "id": facts.get("slug") or rec.get("slug"),
        "type": "regatta_report",
        "headline": unique_headline(facts),
        "deck": deck_from_facts(facts),
        "event_title": facts.get("title") or "",
        "byline": "SailingSA",
        "kicker": (
            (" / ".join(facts.get("classes") or []) if facts.get("mixed_class") else (facts.get("class_name") or "Regatta")).upper()
            + "  ·  "
            + (facts.get("club") or "")
        ),
        "published_at": issue,
        "event_id": facts.get("slug") or rec.get("slug"),
        "layout": layout,
        "entries": facts.get("entries") or 0,
        "media_layout": "paired-then-full" if len(images) > 1 else "",
        "hero_image": {
            "url": first.get("local_path") or first.get("url"),
            "source_url": first.get("source_url"),
            "rights_status": "source_attributed",
        }
        if first
        else None,
        "blocks": blocks,
        "sources": [c["url"] for c in cites],
        "citations": cites,
        "review_status": "rewritten",
        "third_party": third_party,
        "needs_external": not third_party,
        "ai_writer": writer,
        "club": facts.get("club") or "",
        "class_name": facts.get("class_name") or "",
        "start_date": facts.get("start") or "",
        "end_date": facts.get("end") or "",
        "week_fact": week_fact_card(facts, rec),
    }


def write_week_feature(issue, monday, table_events, reports, polish=None) -> dict:
    monday = _as_monday(monday)
    art = feature(issue, monday, table_events, reports)
    sat, sun = saturday_sunday(monday)
    cards = [week_fact_from_report(report) for report in reports or []]
    unlisted = list(art.get("unlisted_events") or [])
    lock = {
        "title": "Last Week's Roundup",
        "week_cards": cards,
        "unlisted": unlisted,
    }
    draft = "\n\n".join(
        b.get("text") or "" for b in art.get("blocks") or [] if b.get("type") == "paragraph"
    )
    polished, writer = polish_copy(
        "week feature",
        {
            "deck": art.get("deck"),
            "unlisted": unlisted,
            "events": cards,
        },
        lock,
        draft,
        polish=polish,
    )
    if polished and not week_lead_errors(polished, cards, unlisted):
        art["blocks"] = [b for b in art.get("blocks") or [] if b.get("type") != "paragraph"]
        art["blocks"].extend(
            {"type": "paragraph", "text": strip_cite_marks(p.strip())}
            for p in re.split(r"\n{2,}", polished)
            if p.strip()
        )
    art["weekend"] = [sat.isoformat(), sun.isoformat()]
    art["ai_writer"] = writer if polished else "desk"
    art["week_cards"] = cards
    return art


def write_issue(issue, monday, roster_events, table_events, facts_by_slug, heroes, root=None, polish=None) -> dict:
    """Build the week lead + scored event articles. Biggest fleet first. Official-only is a pass."""
    root = root or ROOT
    monday = _as_monday(monday)
    issue = issue or monday.isoformat()
    scored = [e for e in (roster_events or []) if e.get("status") == "pass"]
    scored.sort(
        key=lambda e: int((facts_by_slug.get(e.get("slug") or "") or {}).get("entries") or e.get("entries") or 0),
        reverse=True,
    )
    reports = []
    for index, rec in enumerate(scored):
        slug = rec.get("slug") or ""
        facts = facts_by_slug.get(slug)
        if not facts:
            continue
        article = write_event_article(issue, rec, facts, (heroes or {}).get(slug), layout=layout_for(index, "regatta_report"), polish=polish)
        reports.append(article)
        (root / "issues" / issue / "sources").mkdir(parents=True, exist_ok=True)
        (root / "issues" / issue / "sources" / f"{slug}-article.json").write_text(
            json.dumps(article, indent=2, ensure_ascii=False) + "\n"
        )
    lead = write_week_feature(issue, monday, table_events, reports, polish=polish)
    covered = {a.get("event_id") for a in reports}
    story = {
        "schema_version": "1.0",
        "issue_id": issue,
        "title": "Last Week's Roundup",
        "edition_date": issue,
        "status": "draft",
        "articles": [lead] + reports,
        "unlisted_events": unlisted_event_names(table_events, covered),
        "needs_external": [a["event_id"] for a in reports if a.get("needs_external")],
        "enrichment": {
            slug: ((heroes or {}).get(slug) or {}).get("enrichment")
            for slug in (a.get("event_id") for a in reports)
        },
    }
    dest = root / "issues" / issue
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "sources").mkdir(parents=True, exist_ok=True)
    tools = ai_available()
    story["ai_tools"] = tools
    (dest / "issue.json").write_text(json.dumps(story, indent=2, ensure_ascii=False) + "\n")
    (dest / "sources" / "weekend-story.json").write_text(
        json.dumps(
            {
                "issue": issue,
                "scored": [a.get("event_id") for a in reports],
                "unlisted": story["unlisted_events"],
                "needs_external": story["needs_external"],
                "sorted_by": "entries",
                "ai_tools": tools,
                "ai_writer": [a.get("ai_writer") for a in reports],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    return story
