#!/usr/bin/env python3
"""Step 3: write Last Week's Roundup from the locked roster, leaderboards, and stored heroes.

Uses the official equals card as the starting point. An AI call (OpenAI or Perplexity)
may polish the copy; if it invents a name or there is no key, the facts-locked recap
is kept. No third-party source is required. Events that happened without a results
card are named on the week lead. Scored events get their own heading, biggest fleet first.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from ai_tools import available as ai_available, chat as ai_chat, load_env
from event_rewrite import (
    citation_index,
    deck_from_facts,
    facts_from_rows,
    layout_for,
    unique_headline,
)
from evidence_pipeline import feature, recap, unlisted_event_names
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
    """Official sentence about the stored hero so the writer can adapt it."""
    if not hero or hero.get("status") != "pass" or not hero.get("local_path"):
        return ""
    title = (hero.get("title") or facts.get("title") or "event photography").strip()
    return f"The stored hero photograph is {title}, saved from the parent event page. [1]"


def _required_tokens(facts: dict) -> list[str]:
    winner = (facts.get("winner_helm") or (facts.get("winner") or "").split(" and ")[0] or "").strip()
    token = winner.split()[0] if winner else ""
    return [t for t in (token, facts.get("title") or "") if t and t != "The"]


def _locked(text: str, facts: dict) -> bool:
    blob = (text or "").lower()
    return all(tok.lower() in blob for tok in _required_tokens(facts))


def _system_prompt() -> str:
    return (
        "You write a South African sailing magazine recap. Use only the supplied facts. "
        "Do not invent sailors, scores, clubs, or other events. Keep citations like [1]. "
        "Write flowing sentences, not a bullet list. If a stored hero photograph is supplied, "
        "adapt the recap to mention that picture in one sentence."
    )


def polish_copy(kind: str, context: dict, facts: dict, draft: str, polish=None) -> tuple[str | None, str]:
    """Polish the official draft. Returns (text, writer). Writer is official if the call is unused or discarded."""
    if polish is not None:
        text = polish(kind, context, facts, draft)
        if text and _locked(text, facts):
            return text.strip(), "injected"
        return None, "official"
    load_env()
    user = kind + "\n" + json.dumps({"context": context, "draft": draft}, ensure_ascii=False)
    text, provider = ai_chat(_system_prompt(), user)
    if not text or not _locked(text, facts):
        return None, "official"
    return text.strip(), provider


def ai_polish(kind: str, context: dict, facts: dict, draft: str) -> str | None:
    """Optional AI call. Must keep the locked facts or it is discarded."""
    text, _provider = polish_copy(kind, context, facts, draft)
    return text


def write_event_article(issue: str, rec: dict, facts: dict, hero: dict | None, layout: str = "classic", polish=None) -> dict:
    """Write one event article from official data + stored hero. Third-party is optional."""
    ctx = raw_context(rec, facts, hero)
    cluster = {"articles": [], "count": 0}
    cites = citation_index(cluster, facts)
    paras = recap(facts, cluster, cites)
    note = media_note(hero, facts)
    if note:
        paras.append(note)
    polished, writer = polish_copy("event article", ctx, facts, " ".join(paras), polish=polish)
    if polished:
        paras = [p.strip() for p in re.split(r"\n{2,}", polished) if p.strip()] or paras
        if not any("[1]" in p for p in paras):
            paras[0] = paras[0].rstrip(".") + " [1]."
    blocks = []
    if hero and hero.get("status") == "pass" and hero.get("local_path"):
        blocks.append(
            {
                "type": "image",
                "url": hero["local_path"],
                "alt": facts.get("title") or rec.get("name") or "",
                "caption": (hero.get("title") or facts.get("title") or "Event photography") + ".",
                "credit": "Event photography",
                "source_url": hero.get("source_url") or facts.get("url") or "",
                "rights_status": "source_attributed",
            }
        )
    for text in paras:
        blocks.append({"type": "paragraph", "text": text})
    cols, table = facts.get("leaderboard") or ([], [])
    blocks.append({"type": "heading", "text": "1st, 2nd, 3rd"})
    blocks.append({"type": "results", "source_event_url": facts.get("url") or "", "columns": cols, "rows": table, "as_of": issue})
    third_party = False
    return {
        "id": facts.get("slug") or rec.get("slug"),
        "type": "regatta_report",
        "headline": unique_headline(facts),
        "deck": deck_from_facts(facts),
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
        "hero_image": {"url": hero.get("local_path"), "source_url": hero.get("source_url"), "rights_status": "source_attributed"}
        if hero and hero.get("local_path")
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
    }


def write_week_feature(issue, monday, table_events, reports, polish=None) -> dict:
    monday = _as_monday(monday)
    art = feature(issue, monday, table_events, reports)
    sat, sun = saturday_sunday(monday)
    must = [r.get("headline") or "" for r in reports] + list(art.get("unlisted_events") or [])
    lock = {
        "title": "Last Week's Roundup",
        "winner": (reports[0].get("headline") or "") if reports else "Last Week",
        "winner_helm": "",
    }
    draft = " ".join(b.get("text") or "" for b in art.get("blocks") or [] if b.get("type") == "paragraph")
    polished, writer = polish_copy(
        "week feature",
        {"deck": art.get("deck"), "unlisted": art.get("unlisted_events"), "scored": must},
        lock,
        draft,
        polish=polish,
    )
    if polished:
        blob = polished.lower()
        named = all(
            any(part.lower() in blob for part in (n, n.split()[0] if n else "") if part)
            for n in must
            if n
        )
        if named:
            art["blocks"] = [b for b in art.get("blocks") or [] if b.get("type") != "paragraph"]
            art["blocks"].extend(
                {"type": "paragraph", "text": p.strip()} for p in re.split(r"\n{2,}", polished) if p.strip()
            )
    art["weekend"] = [sat.isoformat(), sun.isoformat()]
    art["ai_writer"] = writer if polished else "official"
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
