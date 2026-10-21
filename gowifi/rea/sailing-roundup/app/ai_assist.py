#!/usr/bin/env python3
"""AI assist for gold-style magazine copy.

REA writes from official results plus verified cluster texts (RAG).
When OPENAI_API_KEY, ANTHROPIC_API_KEY, or PERPLEXITY_API_KEY is set,
the model redrafts the recap in the 2026-09-28 voice. Every sentence
must stay inside those sources. No key → the gold recap is used as-is.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

from evidence_pipeline import official_names, text_of

UA = {"User-Agent": "SailingRoundupResearch/1.0", "Content-Type": "application/json"}
GOLD_STYLE = """Write a South African sailing magazine recap in the voice of
https://sailingsa.co.za/sailing-roundup/issues/2026-09-28/

Rules:
- Magazine paragraphs, not a results dump or box score.
- First sentence: winners won Event at Venue, scoring N nett across R races in an E-boat fleet. [1]
- Then race-win colour only from the official box score. [1]
- Then 2nd and 3rd. [1]
- Then only facts that appear in a numbered source (age titles, conditions, host mentions).
- No invented names, venues, photos, or scores.
- Every paragraph ends with a citation like [1] or [2].
- Return JSON: {"paragraphs": ["...", "..."]}
"""


def _cage(facts: dict, cluster: dict, index: list[dict], fallback: list[str]) -> str:
    sources = []
    for item in index:
        body = (item.get("text") or "")[:900]
        sources.append(f"[{item.get('n')}] {item.get('title') or ''} {item.get('url') or ''}\n{body}")
    for item in (cluster or {}).get("articles") or []:
        sources.append(text_of(item)[:900])
    return json.dumps(
        {
            "facts": {
                "title": facts.get("title"),
                "venue": facts.get("club_name"),
                "winner": facts.get("winner"),
                "second": facts.get("second"),
                "third": facts.get("third"),
                "nett": facts.get("winner_nett"),
                "races": facts.get("races"),
                "entries": facts.get("entries"),
                "classes": facts.get("class_names"),
                "official_names": official_names(facts)[:40],
            },
            "fallback": fallback,
            "sources": sources[:8],
        },
        ensure_ascii=False,
    )


def _post(url: str, payload: dict, headers: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={**UA, **headers})
    with urllib.request.urlopen(req, timeout=35) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def _llm(prompt: str) -> str:
    openai = os.getenv("OPENAI_API_KEY")
    if openai:
        data = _post(
            "https://api.openai.com/v1/chat/completions",
            {
                "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {"role": "system", "content": GOLD_STYLE},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
            {"Authorization": "Bearer " + openai},
        )
        return ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    anthropic = os.getenv("ANTHROPIC_API_KEY")
    if anthropic:
        data = _post(
            "https://api.anthropic.com/v1/messages",
            {
                "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
                "max_tokens": 1200,
                "system": GOLD_STYLE,
                "messages": [{"role": "user", "content": prompt}],
            },
            {"x-api-key": anthropic, "anthropic-version": "2023-06-01"},
        )
        return "".join(part.get("text") or "" for part in data.get("content") or [])
    perplexity = os.getenv("PERPLEXITY_API_KEY")
    if perplexity:
        data = _post(
            "https://api.perplexity.ai/chat/completions",
            {
                "model": "sonar",
                "messages": [
                    {"role": "system", "content": GOLD_STYLE},
                    {"role": "user", "content": prompt},
                ],
            },
            {"Authorization": "Bearer " + perplexity},
        )
        return ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    return ""


def _parse(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        data = json.loads(raw[start : end + 1] if start >= 0 else raw)
        paras = data.get("paragraphs") if isinstance(data, dict) else data
        return [str(p).strip() for p in paras or [] if str(p).strip()]
    except (ValueError, TypeError):
        return [p.strip() for p in re.split(r"\n{2,}", raw) if p.strip()]


def valid(paragraphs: list[str], facts: dict, index: list[dict]) -> bool:
    if len(paragraphs) < 2:
        return False
    cites = {int(item["n"]) for item in index if item.get("n")}
    official = {n.lower() for n in official_names(facts)}
    blob = " ".join(paragraphs)
    if facts.get("winner") and facts["winner"].split(";")[0].strip().split(" and ")[0] not in blob:
        if (facts.get("club") or "") not in blob and (facts.get("title") or "") not in blob:
            return False
    for para in paragraphs:
        refs = [int(x) for x in re.findall(r"\[(\d+)\]", para)]
        if not refs or not set(refs) <= cites:
            return False
    for match in re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z'\-]+){1,2})\b", blob):
        if match.lower() in official or match in (facts.get("club_name") or "") or match in (facts.get("title") or ""):
            continue
        if match.split()[0] in {"The", "Lake", "Henley", "Aeolians", "Theewater", "Milnerton", "Free"}:
            continue
    return True


def polish(facts: dict, cluster: dict, index: list[dict], fallback: list[str]) -> list[str]:
    if not any(os.getenv(k) for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "PERPLEXITY_API_KEY")):
        return fallback
    try:
        drafted = _parse(_llm(_cage(facts, cluster, index, fallback)))
    except Exception:
        return fallback
    if drafted and valid(drafted, facts, index):
        return drafted
    return fallback
