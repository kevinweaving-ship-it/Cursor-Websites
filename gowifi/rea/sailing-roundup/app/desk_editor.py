#!/usr/bin/env python3
"""Sports-desk editor. United Robots / Wordsmith / Sportradar style.

Every sentence is a data point from the locked results card or the stored
hero. No web search. No chat model. The angle comes from the box score
(sweep, tie, consistency, provisional, win). That is what works first time.
"""
from __future__ import annotations

import re

from event_rewrite import _agree, _date_span, _heats, entry_label

GENERIC = re.compile(
    r"exciting weekend|took to the water|action[- ]packed|thrilling display|"
    r"showcased their skills|weekend to remember|in a display of|"
    r"sailors gathered|nature of the sport|lovely weekend|"
    r"it was a (?:great|fantastic|amazing)|the sailing community|"
    r"stored hero photograph|generic ai",
    re.I,
)
PHOTO_DETAIL = re.compile(
    r"prize|giving|water|podium|fleet|start|finish|racing|boat|crew|helm",
    re.I,
)


def is_generic(text: str) -> bool:
    return bool(GENERIC.search(text or ""))


def angle(facts: dict) -> str:
    races = int(facts.get("races") or 0)
    wins = int(facts.get("winner_wins") or 0)
    heats = _heats(facts.get("winner_scores"))
    if heats and races and len(heats) == races:
        wins = sum(1 for h in heats if h.get("win"))
    if (facts.get("status") or "").lower() == "provisional":
        return "provisional"
    if facts.get("tied_first"):
        return "tie"
    if races and wins == races:
        return "sweep"
    if wins and wins >= max(3, races // 2):
        return "dominate"
    if heats and races and len(heats) == races and wins == 0:
        return "consistency"
    return "win"


def _nett(value) -> str:
    if value in (None, ""):
        return ""
    return str(value).replace(".0", "")


def _margin(facts: dict) -> str:
    try:
        win = float(facts.get("winner_nett"))
        second = float(facts.get("second_nett"))
    except (TypeError, ValueError):
        return ""
    gap = second - win
    if gap <= 0:
        return ""
    points = int(gap) if gap == int(gap) else gap
    word = "point" if points == 1 else "points"
    return f"{points} {word}"


def photo_caption(hero: dict | None, facts: dict) -> str:
    if not hero or not (hero.get("local_path") or hero.get("url")):
        return ""
    title = (hero.get("title") or "").strip().rstrip(".")
    event = (facts.get("title") or "").strip()
    venue = (facts.get("club_name") or "").strip()
    if title and title.lower() not in {event.lower(), "event photography"}:
        return title + "."
    if event and venue:
        return f"{event} at {venue}."
    return (event or "Event photography") + "."


def photo_line(hero: dict | None, facts: dict) -> str:
    """Body mention only when the stored photo has a real caption."""
    if not hero or hero.get("status") != "pass" or not hero.get("local_path"):
        return ""
    title = (hero.get("title") or "").strip()
    event = (facts.get("title") or "").strip()
    if not title or title.lower() == event.lower():
        return ""
    if not PHOTO_DETAIL.search(title):
        return ""
    return f"The photograph with this report is {title.rstrip('.')}. [1]"


def edit_event(facts: dict, hero: dict | None = None) -> list[str]:
    """Newsroom recap locked to the results card and stored hero."""
    mark = "[1]"
    winner = facts.get("winner") or "The leader"
    title = facts.get("title") or "the event"
    venue = facts.get("club_name") or facts.get("club") or "the host club"
    entries = facts.get("entries") or 0
    races = facts.get("races") or 0
    klass = facts.get("winner_class") or facts.get("class_name") or ""
    classes = [c for c in (facts.get("classes") or []) if c]
    dates = _date_span(facts.get("start") or "", facts.get("end") or "")
    nett = _nett(facts.get("winner_nett"))
    chosen = angle(facts)
    verb = _agree(winner, "won", "won")
    lead = ""
    if chosen == "provisional":
        lead = f"{winner} finished first in the published {title} standings at {venue}"
    elif chosen == "sweep":
        lead = f"{winner} swept the {title} at {venue}, winning all {races} races"
    elif chosen == "dominate":
        lead = f"{winner} dominated the {title} at {venue}"
    elif chosen == "tie":
        lead = f"{winner} {_agree(winner, 'take', 'takes')} the {title} at {venue} after a points tie"
    elif chosen == "consistency":
        lead = f"{winner} topped the {title} at {venue} without winning a race"
    else:
        lead = f"{winner} {verb} the {title} at {venue}"
    if dates:
        lead += f" over {dates}"
    if facts.get("mixed_class") and classes and not facts.get("overall"):
        lead += f", taking the {klass or classes[0]} fleet"
        if nett:
            lead += f" on {nett} nett points"
        if races:
            lead += f" across {races} races"
        lead += f". {entries} boats raced in {', '.join(classes)}. {mark}"
    else:
        bits = []
        identity = facts.get("identity") or ("team" if facts.get("team_racing") else "")
        time = (facts.get("winner_time") or "").strip()
        if nett and identity not in ("team", "boat"):
            bits.append(f"{nett} nett points")
        elif time:
            bits.append(time)
        if races and chosen != "sweep":
            bits.append(f"{races} races")
        if identity == "team" and entries:
            article = "an" if str(entries)[:1] == "8" or str(entries) in {"11", "18"} else "a"
            fleet = f" in {article} {entries}-team{(' ' + klass) if klass else ''} field"
        else:
            if facts.get("overall"):
                scoring = str(facts.get("scoring_system") or "")
                if re.search(r"py|portsmouth", scoring, re.I):
                    klass = "PY"
                elif scoring and not klass:
                    klass = scoring
            fleet = f" in a {entries}-boat{(' ' + klass) if klass else ''} fleet" if entries else ""
        if bits:
            lead += ", scoring " + " across ".join(bits) + fleet + f". {mark}"
        else:
            lead += f"{fleet}. {mark}" if fleet else f". {mark}"
    paragraphs = [lead]
    if chosen == "tie":
        paragraphs.append(
            f"The top two crews were level on nett points; the official results rank {winner} first. {mark}"
        )
    if facts.get("mixed_class") and facts.get("ranked_rows") and not facts.get("overall"):
        by = {}
        for row in facts["ranked_rows"]:
            key = (row.get("class_name") or row.get("class_canonical") or "").strip()
            if key:
                by.setdefault(key, []).append(row)
        bits = []
        for key, rows in by.items():
            names = [entry_label(r) for r in rows[:3] if entry_label(r) not in ("", "The leader")]
            if names:
                bits.append(f"{key} 1–{len(names)} {', '.join(names)}")
        if bits:
            paragraphs.append("; ".join(bits) + f" {mark}")
    else:
        podium = []
        gap = _margin(facts)
        identity = facts.get("identity") or ("team" if facts.get("team_racing") else "")
        points = identity not in ("team", "boat")
        if facts.get("second"):
            second = f"{facts['second']} finished second"
            nett2 = _nett(facts.get("second_nett"))
            if nett2 and points:
                second += f" on {nett2} nett points"
            if gap and chosen != "tie" and points:
                second += f", {gap} behind"
            podium.append(second + ".")
        if facts.get("third"):
            third = f"{facts['third']} finished third"
            nett3 = _nett(facts.get("third_nett"))
            if nett3 and points:
                third += f" on {nett3} nett points"
            podium.append(third + ".")
        if podium:
            paragraphs.append(" ".join(podium) + " " + mark)
    if (facts.get("status") or "").lower() == "provisional":
        paragraphs.append(f"The published results remain provisional. {mark}")
    extra = photo_line(hero, facts)
    if extra:
        paragraphs.append(extra)
    return [p for p in paragraphs if p and not is_generic(p)]


def _and_join(parts: list[str]) -> str:
    parts = [p for p in parts if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def edit_week(date_line: str, reports: list[dict], unlisted: list[str]) -> list[str]:
    """Week lead: name every scored event and the same-period events still without results."""
    if not reports:
        return [f"No scored results were published for the weekend of {date_line}."]
    if len(reports) == 1:
        lead = reports[0]
        text = (lead.get("headline") or "Weekend racing").rstrip(".")
        deck = (lead.get("deck") or "").strip()
        if deck and deck.lower() not in text.lower():
            text += ". " + deck.rstrip(".")
        text += f". The result was posted for {date_line}."
        paragraphs = [text]
    else:
        biggest = reports[0]
        others = [r.get("headline") or r.get("event_id") or "another event" for r in reports[1:]]
        text = f"The weekend of {date_line} was led by {(biggest.get('headline') or 'the largest scored fleet').rstrip('.')}"
        if others:
            text += ", with " + _and_join(others) + " also posting results"
        text += "."
        paragraphs = [text]
    if unlisted:
        paragraphs.append(
            _and_join(unlisted)
            + " also took place in the same period; "
            + ("that event does" if len(unlisted) == 1 else "those events do")
            + " not yet have a published results card."
        )
    return paragraphs


def qa(text: str, facts: dict) -> list[str]:
    """Fail closed: generic filler or a missing locked fact is a fuckup."""
    errors = []
    blob = (text or "").lower()
    if is_generic(text):
        errors.append("generic filler — not desk copy")
    winner = (facts.get("winner_helm") or (facts.get("winner") or "").split(" and ")[0] or "").strip()
    token = winner.split()[0] if winner else ""
    if token and token != "The" and token.lower() not in blob:
        errors.append(f"winner {winner!r} missing")
    title = facts.get("title") or ""
    if title and title.lower() not in blob:
        errors.append(f"event {title!r} missing")
    return errors
