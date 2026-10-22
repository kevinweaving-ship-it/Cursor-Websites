#!/usr/bin/env python3
"""Sports-desk editor. United Robots / Wordsmith / Sportradar style.

Every sentence is a data point from the locked results card or the stored
hero. No web search. No chat model. The angle comes from the box score
(sweep, tie, consistency, provisional, win). That is what works first time.
"""
from __future__ import annotations

import re

from event_rewrite import _agree, _date_span, _heats, _is_roster, entry_label, ranked_winner, strip_cite_marks

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
    return f"The photograph with this report is {title.rstrip('.')}."


def edit_event(facts: dict, hero: dict | None = None) -> list[str]:
    """Newsroom recap locked to the results card and stored hero."""
    winner = ranked_winner(facts) or (facts.get("winner") or "The leader")
    if (facts.get("identity") == "team" or facts.get("team_racing")) and _is_roster(winner):
        raise ValueError("team racing copy must use the team name, not a sailor roster")
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
        lead += f". {entries} boats raced in {', '.join(classes)}."
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
        wins = facts.get("winner_wins")
        if identity == "team" and wins:
            bits = [f"{wins} race {'win' if int(wins) == 1 else 'wins'}"] + [b for b in bits if "races" not in b]
        if bits:
            lead += ", scoring " + " across ".join(bits) + fleet + "."
        else:
            lead += f"{fleet}." if fleet else "."
    paragraphs = [lead]
    if chosen == "tie":
        paragraphs.append(
            f"The top two crews were level on nett points; the official results rank {winner} first."
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
            paragraphs.append("; ".join(bits))
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
            paragraphs.append(" ".join(podium))
    if (facts.get("status") or "").lower() == "provisional":
        paragraphs.append("The published results remain provisional.")
    extra = photo_line(hero, facts)
    if extra:
        paragraphs.append(extra)
    return [strip_cite_marks(p) for p in paragraphs if p and not is_generic(p)]


def _and_join(parts: list[str]) -> str:
    parts = [p for p in parts if p]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return ", ".join(parts[:-1]) + " and " + parts[-1]


TALLY_COPY = re.compile(
    r"\b\d+\s+scored events?\b|the weekend was led by|also posting results",
    re.I,
)
HYPE_COPY = re.compile(
    r"\b(heartbreak|miracle|unbelievable|thriller|dramatic finish|fairy[- ]tale)\b",
    re.I,
)
HEADLINE_TAKEN = re.compile(
    r"^(.+?)\s+(?:won by|dominated by|swept by|taken by|led by)\s+(.+)$",
    re.I,
)
HEADLINE_WINS = re.compile(
    r"^(.+?)\s+(?:wins?|won|dominates?|dominated|sweeps?|swept|takes?)\s+(.+)$",
    re.I,
)
SWEEP_CLAIM = re.compile(r"won all (\d+) races", re.I)


def _short_venue(venue: str) -> str:
    return (
        (venue or "")
        .replace(" Yacht Club", "")
        .replace(" Sports Club", "")
        .replace(" Club", "")
        .strip()
    )


def week_fact_card(facts: dict, rec: dict | None = None) -> dict:
    """Structured, source-backed card for the week lead. Not a headline string."""
    chosen = angle(facts)
    winner = ranked_winner(facts) or (facts.get("winner") or "").strip()
    title = (facts.get("title") or (rec or {}).get("name") or "").strip()
    venue = (facts.get("club_name") or facts.get("club") or "").strip()
    races = int(facts.get("races") or 0)
    wins = int(facts.get("winner_wins") or 0)
    heats = _heats(facts.get("winner_scores"))
    if heats and races and len(heats) == races:
        wins = sum(1 for h in heats if h.get("win"))
    provisional = chosen == "provisional" or (facts.get("status") or "").lower() == "provisional"
    sweep = bool(races and wins == races)
    return {
        "id": facts.get("slug") or (rec or {}).get("slug") or "",
        "name": title,
        "class_name": facts.get("class_name") or "",
        "venue": venue,
        "short_venue": _short_venue(venue) or (facts.get("club") or "").strip(),
        "club": facts.get("club") or "",
        "start": facts.get("start") or "",
        "end": facts.get("end") or "",
        "winner": winner,
        "status": "provisional" if provisional else "final",
        "tied_first": bool(facts.get("tied_first")),
        "winner_wins": wins,
        "races": races,
        "sweep": sweep,
        "angle": chosen,
        "entries": facts.get("entries") or 0,
    }


def week_fact_from_report(report: dict) -> dict:
    if isinstance(report.get("week_fact"), dict) and report["week_fact"].get("name"):
        return dict(report["week_fact"])
    headline = (report.get("headline") or "").strip().rstrip(".")
    name = (report.get("event_title") or "").strip()
    winner = ""
    venue = ""
    deck = report.get("deck") or ""
    if " @ " in deck:
        venue = deck.split(" @ ", 1)[1].split("·")[0].strip()
    elif deck:
        for bit in (p.strip() for p in deck.split("·")):
            if re.search(r"club|lake|yacht|midmar|aeolians|theewater|deneys|henley", bit, re.I):
                venue = bit
                break
    taken = HEADLINE_TAKEN.match(headline)
    wins = HEADLINE_WINS.match(headline)
    if taken:
        name = name or taken.group(1).strip()
        winner = taken.group(2).strip()
    elif wins:
        winner = wins.group(1).strip()
        name = name or wins.group(2).strip()
    name = re.sub(r"\s+20\d{2}\b", "", name).strip()
    name = re.sub(r"\s+at\s+.+$", "", name).strip()
    winner = re.sub(r"\s+after a points tie.*$", "", winner, flags=re.I).strip()
    winner = re.sub(r"\s+at\s+.+$", "", winner).strip()
    winner = re.sub(r"\s+-\s+[A-Z0-9]{2,6}$", "", winner).strip()
    if not name:
        name = headline or "the event"
    return {
        "id": report.get("event_id") or report.get("id") or "",
        "name": name,
        "class_name": report.get("class_name") or "",
        "venue": venue,
        "short_venue": _short_venue(venue),
        "club": report.get("club") or "",
        "start": report.get("start_date") or "",
        "end": report.get("end_date") or "",
        "winner": winner,
        "status": "final",
        "tied_first": "tie" in headline.lower(),
        "winner_wins": 0,
        "races": 0,
        "sweep": "sweep" in headline.lower(),
        "angle": "win",
        "entries": report.get("entries") or 0,
    }


def _significance(card: dict) -> tuple:
    order = {"tie": 0, "sweep": 1, "dominate": 2, "win": 3, "consistency": 4, "provisional": 5}
    return (order.get(card.get("angle") or "", 9), -int(card.get("entries") or 0))


def _event_phrase(card: dict, *, include_venue: bool = True, also: bool = False) -> str:
    name = card.get("name") or "the event"
    winner = (card.get("winner") or "").strip()
    venue = (card.get("short_venue") or card.get("venue") or "").strip()
    at = f" at {venue}" if include_venue and venue else ""
    if (card.get("status") or "") == "provisional":
        if winner:
            return f"{winner} led the provisional {name} standings{at}"
        return f"the published {name} standings remained provisional{at}"
    if card.get("tied_first"):
        if also and winner:
            return f"{winner} also took the {name} after a points tie"
        return f"A points tie settled the {name}{at}"
    if card.get("sweep") and card.get("races"):
        verb = "also won" if also else "won"
        return f"{winner} {verb} all {card['races']} races in the {name}" + ("" if also else at)
    if card.get("sweep") and winner:
        return f"{winner} {'also swept' if also else 'swept'} the {name}" + ("" if also else at)
    if winner:
        return f"{winner} {'also won' if also else 'won'} the {name}{at}"
    return f"the {name} was decided{at}"


def _group_sentence(cards: list[dict]) -> str:
    cards = list(cards)
    venue = (cards[0].get("short_venue") or cards[0].get("venue") or "").strip()
    if len(cards) == 1:
        return _event_phrase(cards[0], include_venue=True).rstrip(".") + "."
    first, rest = cards[0], cards[1:]
    if first.get("tied_first"):
        extras = [_event_phrase(card, include_venue=False, also=True) for card in rest]
        return (
            f"A points tie settled the {first.get('name')} at {venue}, where "
            + _and_join(extras)
            + "."
        )
    head = _event_phrase(first, include_venue=True)
    extras = [_event_phrase(card, include_venue=False, also=True) for card in rest]
    return head + ", where " + _and_join(extras) + "."


def week_lead_errors(text: str, cards: list[dict], unlisted: list[str] | None = None) -> list[str]:
    """Accept a week lead only if it stays inside the locked event facts."""
    errors = []
    blob = text or ""
    low = blob.lower()
    if is_generic(blob) or HYPE_COPY.search(blob):
        errors.append("generic filler or invented drama")
    if TALLY_COPY.search(blob):
        errors.append("tally or headline-list copy")
    parts = re.split(r"(?=Other events in the past week were)", blob, flags=re.I)
    scored_blob = (parts[0] if parts else blob).strip()
    unlisted_blob = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
    for card in cards or []:
        name = (card.get("name") or "").strip()
        if name and name.lower() not in low:
            errors.append(f"missing exact event name {name!r}")
        if (card.get("status") or "") == "provisional":
            if "provisional" not in low:
                errors.append(f"{name} is provisional but the lead is not")
            if name and re.search(rf"\bwon the {re.escape(name)}\b", scored_blob, re.I):
                errors.append(f"{name} treated as a final win")
    for raw in unlisted or []:
        name = (raw or "").strip()
        if name and name.lower() not in low:
            errors.append(f"unlisted event {name!r} missing")
        if name and name.lower() in scored_blob.lower() and re.search(
            rf"{re.escape(name)}.{{0,40}}\b(won|results|leaderboard)\b", scored_blob, re.I
        ):
            errors.append(f"unlisted event {name!r} implied to have results")
    if (unlisted or []) and not unlisted_blob:
        errors.append("unlisted events must stay in a separate paragraph")
    for match in SWEEP_CLAIM.finditer(blob):
        claimed = int(match.group(1))
        if not any(card.get("sweep") and int(card.get("races") or 0) == claimed for card in cards or []):
            errors.append(f"unsupported sweep of {claimed} races")
    return errors


def edit_week(date_line: str, reports: list[dict], unlisted: list[str]) -> list[str]:
    """Week lead from structured facts. Never a tally of headlines.

    Weekend dates live in the feature deck. Do not repeat them here.
    Lead order may follow venue / sporting significance, not fleet size.
    """
    del date_line
    cards = [week_fact_from_report(report) for report in reports or []]
    cards = [card for card in cards if card.get("name")]
    if not cards:
        return ["No scored results were published."]
    groups: dict[str, list[dict]] = {}
    for card in cards:
        key = (card.get("short_venue") or card.get("venue") or card.get("id") or card.get("name") or "").strip()
        groups.setdefault(key or card.get("name") or "event", []).append(card)
    for group in groups.values():
        group.sort(key=_significance)
    ordered = sorted(groups.items(), key=lambda item: _significance(item[1][0]))
    sentences = [_group_sentence(group) for _, group in ordered]
    if len(sentences) >= 2 and (ordered[-1][1][0].get("status") == "provisional"):
        last = sentences.pop().rstrip(".")
        if last[:2] in {"A ", "a "} or last.startswith("The ") or last.startswith("the "):
            last = last[0].lower() + last[1:]
        sentences[-1] = sentences[-1].rstrip(".") + ", while " + last + "."
    paragraphs = [" ".join(sentences)]
    if unlisted:
        paragraphs.append("Other events in the past week were " + _and_join(unlisted) + ".")
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
