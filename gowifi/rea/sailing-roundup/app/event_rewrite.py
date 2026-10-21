#!/usr/bin/env python3
"""Cluster same-event coverage and rewrite one unique magazine article.

Reverse-engineered from Perplexity Discover / RAG news synthesis, plus
Ground News clustering, Artifact de-baited headlines, Monok stored articles,
and Sportradar/United Robots box-score recaps:

  scrape the event's own primary sources (club, class, host Facebook, local
  news) → keep only items about THIS event → write one article locked to
  those texts and the results card (RAG: no fact that is not in a source) →
  inline citations → photographs from those same sources (podium and on the
  water are both valid; more than one photo is allowed) → one official
  leaderboard per class. External media is kept only when named leaders
  checksum against those results.

Wikimedia / Wikipedia is never a source. A 1954 stock boat is not a source.
Paid APIs are optional. No login-wall bypass.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = {
    "User-Agent": "Mozilla/5.0 (compatible; SailingRoundupResearch/1.0; +https://sailingsa.co.za/sailing-roundup)"
}
FB_UA = {"User-Agent": "facebookexternalhit/1.1"}
LEADERBOARD_LIMIT = 3
LEADERBOARD_COLS = ["Pos", "Helm", "Crew", "Club", "Sail No", "Nett"]
GOLD_BOARD_LABEL = "1st, 2nd, 3rd"
WRONG_CLASS = {
    "420": ("505", "dart 18", "dabchick", "hobie", "optimist"),
    "505": ("420", "dart 18", "dabchick", "hobie", "optimist"),
    "Dart 18": ("420", "505", "dabchick", "hobie", "optimist"),
    "Dabchick": ("420", "505", "dart", "hobie", "505er"),
}
SEED_URLS = {
    "2026-09-25-tsc-420-nationals": [
        "https://www.facebook.com/420nationalssouthafrica/",
        "https://novanews.co.za/school/hermanus-high-schools-sailors-crowned-national-champions/",
        "https://www.facebook.com/theewatersportsclub/",
        "https://www.facebook.com/share/g/1Jh51CDMew/",
        "https://www.theewater.co.za/",
    ],
    "2026-09-24-hmyc-dart-18-nationals": [
        "https://www.facebook.com/share/p/1PGpY1pGh1/",
        "https://www.facebook.com/share/g/19VLSkGHBk/",
        "https://www.facebook.com/henleymidmaryachtclub",
        "https://www.hmyc.org.za/events/367984",
        "https://www.hmyc.org.za/",
    ],
    "2026-09-24-ayc-505-nationals": [
        "https://rsa505.org.za/index.php?option=com_content&view=article&id=338:505-nationals-2026-great-event-at-aeolians&catid=11&Itemid=101",
        "https://rsa505.org.za/",
        "https://www.facebook.com/share/g/1MHJNWcFSM/",
        "https://www.facebook.com/AeoliansClub/",
        "https://aeolians.co.za/",
    ],
    "2026-09-24-ayc-dabchick-gauteng-regionals": [
        "https://www.revolutionise.com.au/dabchickca/events/358939",
        "https://www.revolutionise.com.au/dabchickca/",
        "https://www.revolutionise.com.au/dabchickca/gallery",
        "https://www.facebook.com/dabchicksailingrsa",
        "https://www.facebook.com/AeoliansClub/",
    ],
}
SEED_MEDIA = ROOT / "app" / "seed_media"
SEED_PHOTOS = {
    "2026-10-17-pyc-kzn-mirror-regionals": [
        {
            "file": "2026-10-17-pyc-kzn-mirror-regionals.jpg",
            "kind": "admin_seed",
            "score": 80,
            "credit": "KZN Mirror / event administration",
            "source_url": "https://sailingsa.co.za/regatta/2026-10-17-pyc-kzn-mirror-regionals",
            "title": "KZN Mirror Regionals on the water at Point Yacht Club",
        }
    ],
}
LAYOUTS = ("photo-led", "split", "classic", "compact")
HOST_FALLBACK = {
    "TSC": "Theewater Sports Club",
    "HMYC": "Henley Midmar Yacht Club",
    "AYC": "Aeolians Yacht Club",
    "LDYC": "Lake Deneys Yacht Club",
    "MAC": "Milnerton Aquatic Club",
    "PYC": "Point Yacht Club",
}
DATE_PREFIX = re.compile(r"^(?:20\d{2}-\d{2}-\d{2}|20\d{2})\s+")
TITLE_STOP = {
    "the", "and", "for", "with", "from", "that", "this", "sa", "sas", "inc",
    "sailing", "event", "open", "championship", "championships", "champs",
    "champ", "provincial", "regionals", "regional", "national", "nationals",
    "youth", "south", "african", "africa", "incorporating",
}
JUNK_CLUSTER = (
    "dart.dev",
    "dartpad.dev",
    "dart.org",
    "dartcontainer.com",
    "wikipedia.org",
    "wikimedia.org",
    "upload.wikimedia",
    "commons.wikimedia",
    "instagram.com/accounts/login",
    "music.youtube",
    "tiktok.com/@",
    "tiktok.com/api",
)
PLACE_LINE = re.compile(
    r"(?P<place>\d+)(?:st|nd|rd|th)\s*[–\-]\s*(?P<name>[A-Za-z][A-Za-z \-']+?)"
    r"(?:\s*\((?P<club>[A-Z0-9]{2,8})\))?\s*[–\-]\s*Sail\s+(?P<sail>\S+)",
    re.I,
)
SPECIAL_MENTION = re.compile(
    r"special mention to ([A-Za-z][A-Za-z \-']+), finishing (\d+)(?:st|nd|rd|th)?",
    re.I,
)


def _club_name(code: str, explicit: str = "") -> str:
    code = (code or "").strip()
    explicit = (explicit or "").strip()
    if explicit and len(explicit) > len(code):
        return explicit
    path = ROOT / "app" / "club_sources.json"
    if path.exists() and code:
        clubs = json.loads(path.read_text()).get("clubs") or {}
        rec = clubs.get(code.upper()) or clubs.get(code) or {}
        if rec.get("name"):
            return rec["name"]
    return HOST_FALLBACK.get(code.upper(), explicit or code or "the host club")


def _split_people(raw: str) -> list[str]:
    return [p.strip() for p in re.split(r"\s*;\s*|\s+and\s+", raw or "") if p.strip()]


def _readable_list(names: list[str]) -> str:
    names = [n for n in names if n]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + " and " + names[-1]


def is_team_row(row: dict) -> bool:
    klass = (row.get("class_name") or row.get("class_canonical") or "").upper()
    if klass in {"TSL", "TEAM SAILING"} or "TEAM SAILING" in klass:
        return True
    boat = (row.get("boat_name") or row.get("team_name") or "").strip()
    helm = (row.get("helm_name") or "")
    return bool(boat and (";" in helm or not helm.strip()))


def _team_name(row: dict) -> str:
    raw = (row.get("boat_name") or row.get("team_name") or "").strip()
    if not raw:
        return (row.get("club_abbrev") or row.get("club_raw") or "").strip()
    if raw.isupper() or re.fullmatch(r"[A-Z0-9]+(?:\s+[A-Z0-9]+)*", raw):
        return raw
    if raw.lower() == raw:
        return raw[:1].upper() + raw[1:]
    return raw


def _names(row: dict) -> str:
    if is_team_row(row):
        return _team_name(row) or "The leader"
    helm = (row.get("helm_name") or "").strip()
    crew = (row.get("crew_name") or "").strip()
    if helm and crew:
        return f"{helm} and {crew}"
    return helm or crew or "The leader"


def is_team_event(facts: dict) -> bool:
    if facts.get("team_event"):
        return True
    klass = (facts.get("class_name") or "").upper()
    if klass in {"TSL", "TEAM SAILING"} or "team sailing" in (facts.get("title") or "").lower():
        return True
    rows = facts.get("ranked_rows") or []
    return bool(rows) and all(is_team_row(row) for row in rows)


def result_sailor_names(facts: dict) -> list[str]:
    """Sailor cells on the overall results table — not official identity for TSL."""
    names = []
    for row in facts.get("ranked_rows") or []:
        for raw in ((row.get("helm_name") or ""), (row.get("crew_name") or ""), (row.get("crew2_name") or ""), (row.get("crew3_name") or "")):
            names.extend(_split_people(raw))
    return list(dict.fromkeys(n for n in names if n))


def clean_event_title(title: str, slug: str = "") -> str:
    title = (title or slug or "").strip()
    title = DATE_PREFIX.sub("", title)
    title = re.sub(r"\s+incorporating\b.*$", "", title, flags=re.I).strip()
    if re.search(r"\bChamp$", title) and not title.lower().endswith("championship"):
        title += "s"
    return title


def title_tokens(title: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", (title or "").lower()) if t not in TITLE_STOP and len(t) >= 4]


def board_label(klass: str = "", multi: bool = False, official: bool = True) -> str:
    klass = (klass or "").strip()
    heading = GOLD_BOARD_LABEL if official else "Entered teams"
    if multi and klass:
        return f"{klass} · {heading}"
    return heading


def _surname(name: str) -> str:
    parts = [p for p in (name or "").split() if p]
    return parts[-1] if parts else name


def _intish(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return None


def _has_official_place(row: dict) -> bool:
    return str(row.get("rank") or "").isdigit() or _intish(row.get("nett_points_raw")) is not None


def _ranked(rows: list[dict]) -> list[dict]:
    copied = [dict(row) for row in rows]
    numeric = [r for r in copied if str(r.get("rank") or "").isdigit()]
    ranks = [str(r.get("rank")) for r in numeric]
    if numeric and len(set(ranks)) == len(numeric):
        numeric.sort(key=lambda r: int(r["rank"]))
        return numeric
    scored = [r for r in copied if _intish(r.get("nett_points_raw")) is not None]
    if scored:
        scored.sort(key=lambda r: _intish(r.get("nett_points_raw")) or 999)
        for i, row in enumerate(scored, 1):
            if not str(row.get("rank") or "").isdigit():
                row["rank"] = i
        return scored
    for row in copied:
        row["rank"] = None
    return copied


def _win_count(scores) -> int:
    if not isinstance(scores, dict):
        return 0
    wins = 0
    for raw in scores.values():
        token = re.sub(r"[^0-9.]", "", str(raw).split()[0] if raw else "")
        try:
            if token and float(token) == 1.0:
                wins += 1
        except ValueError:
            continue
    return wins


def _class_key(row: dict) -> str:
    return (row.get("class_name") or row.get("class_canonical") or "").strip()


def _row_people(row: dict) -> list[str]:
    if is_team_row(row):
        team = _team_name(row)
        return [team] if team else []
    out = []
    for raw in ((row.get("helm_name") or "").strip(), (row.get("crew_name") or "").strip()):
        out.extend(_split_people(raw) if raw else [])
    return out


def _nett(value) -> str:
    return "" if value in (None, "") else str(value).replace(".0", "")


def _fleet_from_rows(rows: list[dict]) -> dict:
    ranked = _ranked(rows)
    official = any(_has_official_place(r) for r in ranked)
    winner = ranked[0] if official and ranked else {}
    second = ranked[1] if official and len(ranked) > 1 else {}
    third = ranked[2] if official and len(ranked) > 2 else {}
    first = rows[0] if rows else {}
    races = _intish(first.get("races_sailed")) or len(winner.get("race_scores") or {})
    listed = _intish(first.get("entries_total"))
    entries = listed if listed and listed <= len(rows) + 1 else len(rows)
    return {
        "class_name": _class_key(first),
        "entries": entries,
        "races": races,
        "winner": _names(winner) if winner else "",
        "winner_helm": (winner.get("helm_name") or "").strip(),
        "winner_crew": (winner.get("crew_name") or "").strip(),
        "winner_club": (winner.get("club_abbrev") or winner.get("club_raw") or "").strip(),
        "winner_nett": _nett(winner.get("nett_points_raw")),
        "winner_wins": _win_count(winner.get("race_scores")),
        "winner_scores": winner.get("race_scores") or {},
        "second": _names(second) if second else "",
        "second_nett": _nett(second.get("nett_points_raw")),
        "second_scores": second.get("race_scores") or {},
        "second_wins": _win_count(second.get("race_scores")),
        "third": _names(third) if third else "",
        "third_nett": _nett(third.get("nett_points_raw")),
        "tied_first": official and str(winner.get("nett_points_raw")) == str(second.get("nett_points_raw")) and winner.get("nett_points_raw") not in (None, ""),
        "official_order": official,
        "leaderboard": leaderboard(ranked, official=official),
        "ranked_rows": ranked,
        "names": [n for r in ranked for n in _row_people(r)],
        "team_event": bool(ranked) and all(is_team_row(r) for r in ranked),
    }


def _primary_fleet(fleets: list[dict], title: str) -> dict:
    if not fleets:
        return _fleet_from_rows([])
    if len(fleets) == 1:
        return fleets[0]
    ones = []
    for fleet in fleets:
        if any(str(row.get("rank")) == "1" for row in fleet.get("ranked_rows") or []):
            ones.append(fleet)
    if len(ones) == 1:
        return ones[0]
    title_l = (title or "").lower()
    for fleet in fleets:
        klass = (fleet.get("class_name") or "").lower()
        if klass and klass in title_l:
            return fleet
    return max(fleets, key=lambda item: item.get("entries") or 0)


def facts_from_rows(slug: str, rows: list[dict]) -> dict:
    first = rows[0]
    named = [key for key in (_class_key(row) for row in rows) if key]
    only = named[0] if len(set(named)) == 1 else ""
    grouped: list[list[dict]] = []
    index: dict[str, int] = {}
    prev = only
    for row in rows:
        key = _class_key(row) or prev or only
        if _class_key(row):
            prev = _class_key(row)
        if key not in index:
            index[key] = len(grouped)
            grouped.append([])
        grouped[index[key]].append(row)
    fleets = [_fleet_from_rows(group) for group in grouped]
    club = (first.get("host_club_code") or first.get("host_club_name") or "").strip()
    title = clean_event_title(first.get("event_name") or slug, slug)
    primary = _primary_fleet(fleets, title)
    start = str(first.get("start_date") or slug[:10])[:10]
    end = str(first.get("end_date") or start)[:10]
    all_rows = [row for fleet in fleets for row in fleet.get("ranked_rows") or []]
    all_names = [n for fleet in fleets for n in fleet.get("names") or []]
    entries = sum(len(fleet.get("ranked_rows") or []) for fleet in fleets)
    if len(fleets) == 1:
        entries = _intish(first.get("entries_total")) or entries
    return {
        "slug": slug,
        "title": title,
        "class_name": primary.get("class_name") or "",
        "class_names": [fleet.get("class_name") or "" for fleet in fleets],
        "multi_class": len(fleets) > 1,
        "fleets": fleets,
        "club": club,
        "club_name": _club_name(club, first.get("host_club_name") or ""),
        "host_club_slug": first.get("host_club_slug") or club.lower(),
        "start": start,
        "end": end,
        "entries": entries,
        "races": primary.get("races") or 0,
        "status": (first.get("result_status") or "Published").strip(),
        "winner": primary.get("winner") or "",
        "winner_helm": primary.get("winner_helm") or "",
        "winner_crew": primary.get("winner_crew") or "",
        "winner_club": primary.get("winner_club") or "",
        "winner_nett": primary.get("winner_nett") or "",
        "winner_wins": primary.get("winner_wins") or 0,
        "winner_scores": primary.get("winner_scores") or {},
        "second_scores": primary.get("second_scores") or {},
        "second_wins": primary.get("second_wins") or 0,
        "second": primary.get("second") or "",
        "second_nett": primary.get("second_nett") or "",
        "third": primary.get("third") or "",
        "third_nett": primary.get("third_nett") or "",
        "tied_first": bool(primary.get("tied_first")),
        "official_order": all(bool(fleet.get("official_order")) for fleet in fleets) if fleets else False,
        "team_event": bool(primary.get("team_event")) or is_team_event({"class_name": primary.get("class_name"), "title": title, "ranked_rows": all_rows}),
        "names": list(dict.fromkeys(all_names)),
        "url": "https://sailingsa.co.za/regatta/" + slug,
        "leaderboard": primary.get("leaderboard") or leaderboard([]),
        "ranked_rows": all_rows,
    }


def _official_results_card(facts: dict) -> dict:
    """SailingSA results are already live by the Monday publisher. Always source [1]."""
    bits = [
        f"Official SAS-sanctioned {facts.get('title') or 'event'} at {facts.get('club_name') or facts.get('club') or 'the host club'}.",
    ]
    fleets = facts.get("fleets") or []
    if len(fleets) > 1:
        for fleet in fleets:
            klass = fleet.get("class_name") or "Open"
            podium = []
            if fleet.get("winner"):
                podium.append(f"1st {fleet['winner']}")
            if fleet.get("second"):
                podium.append(f"2nd {fleet['second']}")
            if fleet.get("third"):
                podium.append(f"3rd {fleet['third']}")
            size = fleet.get("entries") or len(fleet.get("ranked_rows") or [])
            bits.append(f"{klass} ({size} boats): " + "; ".join(podium) + ".")
    else:
        if facts.get("winner"):
            bits.append(f"1st {facts['winner']}.")
        if facts.get("second"):
            bits.append(f"2nd {facts['second']}.")
        if facts.get("third"):
            bits.append(f"3rd {facts['third']}.")
    if facts.get("entries") or facts.get("races"):
        bits.append(f"{facts.get('entries') or 0} entries, {facts.get('races') or 0} races.")
    if facts.get("status"):
        bits.append(f"Results are {facts['status']}.")
    return {
        "url": facts.get("url") or "",
        "title": f"{facts.get('title') or 'Event'} — SailingSA results",
        "description": " ".join(bits),
        "snippet": " ".join(bits),
        "engine": "sailingsa",
        "role": "official_results",
        "published": facts.get("end") or "",
    }


def leaderboard(rows: list[dict], limit: int | None = LEADERBOARD_LIMIT, official: bool = True) -> tuple[list[str], list[list[str]]]:
    table = []
    selected = list(rows) if (limit is None or not official) else rows[:limit]
    team = bool(selected) and all(is_team_row(row) for row in selected)
    if team:
        cols = ["Team", "Club"] if not official else ["Pos", "Team", "Club"]
        if any(_nett(row.get("nett_points_raw")) for row in selected):
            cols.append("Nett")
        for i, row in enumerate(selected, 1):
            line = [_team_name(row), str(row.get("club_abbrev") or row.get("club_raw") or "")]
            if official:
                line = [str(i)] + line
            if "Nett" in cols:
                line.append(_nett(row.get("nett_points_raw")))
            table.append(line)
        return cols, table
    for i, row in enumerate(selected, 1):
        table.append(
            [
                str(i),
                str(row.get("helm_name") or ""),
                str(row.get("crew_name") or ""),
                str(row.get("club_abbrev") or row.get("club_raw") or ""),
                str(row.get("sail_number") or ""),
                "" if row.get("nett_points_raw") in (None, "") else str(row.get("nett_points_raw")).replace(".0", ""),
            ]
        )
    return list(LEADERBOARD_COLS), table


def _agree(winner: str, plural: str, singular: str) -> str:
    return plural if (" and " in (winner or "") or "," in (winner or "")) else singular


def event_finished(facts: dict, issue: str | None = None) -> bool:
    """Monday magazine is written after racing. Live tense only if the issue date is still inside the event."""
    if "finished" in facts:
        return bool(facts["finished"])
    try:
        start = __import__("datetime").date.fromisoformat(str(facts.get("start") or "")[:10])
        end = __import__("datetime").date.fromisoformat(str(facts.get("end") or "")[:10])
    except ValueError:
        return True
    if not issue:
        return True
    try:
        day = __import__("datetime").date.fromisoformat(str(issue)[:10])
    except ValueError:
        return True
    return not (start <= day <= end)


def unique_headline(facts: dict, cluster: dict | None = None) -> str:
    winner = facts["winner"]
    title = facts["title"]
    venue = facts["club_name"]
    short_venue = re.sub(r"\s+(Yacht Club|Sports Club|Aquatic Club|Club)$", "", venue or "", flags=re.I).strip() or venue
    finished = event_finished(facts)
    if is_team_event(facts) and not facts.get("winner"):
        n = int(facts.get("entries") or 0)
        if n:
            return f"{n} teams contest {title} at {short_venue}"
        return f"{title} at {short_venue}"
    if is_team_event(facts):
        team = facts.get("winner") or facts.get("winner_club") or facts.get("club") or "The host club"
        return f"{team} win {title} at {short_venue}"
    if facts.get("tied_first") and facts.get("second"):
        return f"{winner} {_agree(winner, 'take', 'takes')} {title} after a points tie at {short_venue}"
    if facts.get("winner_wins") and facts["winner_wins"] >= max(3, int(facts.get("races") or 0) // 2):
        if facts["winner_wins"] == int(facts.get("races") or 0) and (facts.get("races") or 0) >= 6:
            return f"{winner} {_agree(winner, 'sweep', 'sweeps')} {title} at {short_venue}"
        return f"{winner} {_agree(winner, 'dominate', 'dominates')} {title} at {short_venue}"
    # Live "leads" only while the event is still racing. After it ends, they won.
    if (facts.get("status") or "").lower() == "provisional" and not finished:
        fleet = f"{facts['entries']}-boat " if facts.get("entries") else ""
        return f"{winner} {_agree(winner, 'lead', 'leads')} {fleet}{title} at {short_venue}"
    return f"{winner} {_agree(winner, 'win', 'wins')} {title} at {short_venue}"


def _date_span(start: str, end: str) -> str:
    try:
        s = __import__("datetime").date.fromisoformat(start)
        e = __import__("datetime").date.fromisoformat(end)
    except ValueError:
        return start
    if s == e:
        return s.strftime("%-d %B")
    if s.month == e.month:
        return f"{s.day}–{e.day} {e.strftime('%B')}"
    return f"{s.strftime('%-d %B')}–{e.strftime('%-d %B')}"


def _cluster_text(item):
    from evidence_pipeline import text_of
    return text_of(item)


def _keep_cluster_item(item, facts):
    from evidence_pipeline import verify
    return verify(item,facts)["accepted"]


def _host_source(cluster: dict | None) -> dict | None:
    best = None
    best_len = 0
    for item in (cluster or {}).get("articles") or []:
        text = _cluster_text(item)
        score = len(text)
        url = (item.get("url") or "") + " " + (item.get("share_url") or "")
        if "1PGpY1pGh1" in url or "host_club" in (item.get("engine") or "") + (item.get("provenance") or ""):
            score += 1000
        if "facebook.com" in url.lower() and "henleymidmaryachtclub" in url.lower():
            score += 500
        if score > best_len:
            best = dict(item, text=text)
            best_len = score
    return best if best and best_len >= 40 else None


def citation_index(cluster: dict | None, facts: dict | None = None) -> list[dict]:
    """Numbered primary sources. [1] is always the SailingSA results card."""
    out = []
    seen = set()

    def add(url: str, title: str = "", text: str = ""):
        url = (url or "").split("#")[0].strip()
        if not url or url in seen or _wiki_url(url):
            return
        seen.add(url)
        out.append({"n": len(out) + 1, "url": url, "title": title or url, "text": text or ""})

    if facts:
        add(facts.get("url") or "", facts.get("title") or "SailingSA results")
    for item in (cluster or {}).get("articles") or []:
        add(
            item.get("url") or item.get("share_url") or item.get("source_url") or "",
            item.get("title") or "",
            _cluster_text(item),
        )
    return out


def _cite(n: int) -> str:
    return f"[{int(n)}]"


def _source_for_url(index: list[dict], url: str) -> dict | None:
    url = (url or "").split("#")[0]
    for item in index:
        if item["url"] == url or url and url in item["url"]:
            return item
    return None


def _cluster_color(cluster, facts=None, index=None):
    from evidence_pipeline import source_notes
    return source_notes(cluster,facts or {},index or citation_index(cluster,facts))


def _heats(scores) -> list[dict]:
    out = []
    if not isinstance(scores, dict):
        return out
    for key, raw in scores.items():
        token = re.sub(r"[^0-9.]", "", str(raw).split()[0] if raw else "")
        try:
            pts = float(token) if token else None
        except ValueError:
            pts = None
        out.append({"race": key, "pts": pts, "raw": str(raw), "win": pts == 1.0})
    return out


def rewrite_paragraphs(facts, cluster=None, index=None):
    from evidence_pipeline import recap
    index = index or citation_index(cluster, facts)
    fallback = recap(facts, cluster or {}, index)
    try:
        from ai_assist import polish
        return polish(facts, cluster or {}, index, fallback)
    except Exception:
        return fallback


def deck_from_facts(facts: dict) -> str:
    bits = [facts.get("club_name") or facts.get("club") or ""]
    if facts.get("winner_nett"):
        bits.append(f"{facts['winner_nett']} nett")
    if facts.get("entries"):
        bits.append(f"{facts['entries']} entries")
    return " · ".join(x for x in bits if x)


def _request_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(urllib.parse.unquote(parsed.path), safe="/")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))


def _http_get(url: str, headers: dict | None = None, timeout: int = 18) -> tuple[bytes, str]:
    req = urllib.request.Request(_request_url(url), headers=headers or UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.headers.get_content_type() or ""


def extract_article(url):
    from evidence_pipeline import extract
    return extract(url)


def _try_paid_clusters(query: str) -> list[dict]:
    items = []
    perigon = os.getenv("PERIGON_API_KEY")
    if perigon:
        try:
            url = "https://api.perigon.io/v1/stories/all?" + urllib.parse.urlencode(
                {"q": query, "size": 3, "sortBy": "count"}
            )
            req = urllib.request.Request(url, headers={**UA, "Authorization": f"Bearer {perigon}"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            for story in data.get("results") or []:
                items.append(
                    {
                        "url": story.get("url") or "",
                        "title": story.get("name") or "",
                        "description": story.get("summary") or story.get("shortSummary") or "",
                        "image": story.get("imageUrl") or "",
                        "engine": "perigon",
                    }
                )
        except Exception:
            pass
    newsapi = os.getenv("NEWSAPI_AI_KEY")
    if newsapi:
        try:
            payload = json.dumps(
                {
                    "apiKey": newsapi,
                    "resultType": "events",
                    "keyword": query,
                    "eventsCount": 3,
                    "eventsSortBy": "size",
                }
            ).encode()
            req = urllib.request.Request(
                "https://eventregistry.org/api/v1/event/getEvents",
                data=payload,
                headers={**UA, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            for ev in ((data.get("events") or {}).get("results") or []):
                items.append(
                    {
                        "url": ev.get("eventUri") or "",
                        "title": ((ev.get("title") or {}).get("eng") if isinstance(ev.get("title"), dict) else ev.get("title")) or "",
                        "description": ((ev.get("summary") or {}).get("eng") if isinstance(ev.get("summary"), dict) else ev.get("summary")) or "",
                        "image": ev.get("images")[0] if ev.get("images") else "",
                        "engine": "newsapi_ai",
                    }
                )
        except Exception:
            pass
    perplexity = os.getenv("PERPLEXITY_API_KEY")
    if perplexity:
        try:
            payload = json.dumps(
                {
                    "model": "sonar",
                    "messages": [
                        {
                            "role": "system",
                            "content": "Return only South African sailing sources for this event. No Wikipedia.",
                        },
                        {
                            "role": "user",
                            "content": "Primary club, class Facebook, and news URLs for: " + query,
                        },
                    ],
                }
            ).encode()
            req = urllib.request.Request(
                "https://api.perplexity.ai/chat/completions",
                data=payload,
                headers={**UA, "Authorization": "Bearer " + perplexity, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            citations = (((data.get("choices") or [{}])[0].get("message") or {}).get("citations")) or data.get("citations") or []
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            urls = list(citations) + re.findall(r"https?://[^\s)>\]]+", text)
            for link in urls:
                if _wiki_url(link):
                    continue
                items.append({"url": link, "title": "", "description": text[:400], "engine": "perplexity"})
        except Exception:
            pass
    monok = os.getenv("MONOK_API_KEY")
    if monok:
        try:
            url = "https://www.monok.com/api/v1/clusters/?" + urllib.parse.urlencode({"q": query, "s": 3})
            req = urllib.request.Request(url, headers={**UA, "x-api-token": monok})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8", "replace"))
            for ev in data if isinstance(data, list) else data.get("results") or data.get("clusters") or []:
                items.append(
                    {
                        "url": ev.get("url") or ev.get("id") or "",
                        "title": ev.get("title") or ev.get("name") or "",
                        "description": ev.get("summary") or ev.get("shortTitle") or "",
                        "image": ev.get("thumbnail") or ev.get("image") or "",
                        "engine": "monok",
                    }
                )
        except Exception:
            pass
    return items


def cluster_coverage(facts, pack=None, fetch=True):
    from evidence_pipeline import verified_cluster
    official=_official_results_card(facts)
    if fetch:
        artwork=official_event_images(facts)
        if artwork:
            official["images"]=artwork
            official["image"]=artwork[0]["url"]
    candidates=[official]
    for post in (pack or {}).get("verified_posts") or (pack or {}).get("posts") or []:
        candidates.append(dict(post))
    for item in ((pack or {}).get("sailor_mentions") or {}).get("matched") or []:
        candidates.append(
            {
                "url": item.get("url"),
                "title": item.get("headline") or item.get("title") or "",
                "description": item.get("snippet") or item.get("description") or "",
                "body": item.get("snippet") or item.get("description") or item.get("headline") or "",
                "published": item.get("published_at") or item.get("date_iso") or "",
                "engine": "sailor_public_mentions",
                "role": "sailor_media",
            }
        )
    # Previously retrieved source text is evidence, never a trusted identity label.
    issue=str((pack or {}).get("issue") or "2026-09-28")
    old=ROOT/"data"/("reference-"+issue+".json")
    if not old.exists():old=ROOT/"issues"/issue/"issue.json"
    if old.exists():
        data=json.loads(old.read_text())
        for article in data.get("articles",[]):
            if article.get("event_id")!=facts["slug"]:continue
            for cite in article.get("citations",[]):
                candidates.append({"url":cite["url"],"title":cite.get("title",""),"body":cite.get("text",""),"engine":"cached_evidence"})
    candidates += [{"url":u,"engine":"seed"} for u in SEED_URLS.get(facts["slug"],[])]
    try:
        from search_everywhere import catalog_local_urls
        candidates.extend(catalog_local_urls(dict(facts, id=facts["slug"], event_url=facts.get("url"))))
    except Exception:
        pass
    try:
        from social_collect import known_club_posts
        candidates.extend(known_club_posts(facts.get("club") or "", dict(facts, id=facts["slug"], title=facts.get("title"))))
    except Exception:
        pass
    if fetch:
        query = " ".join(x for x in (facts.get("title"), str(facts.get("end") or "")[:4], facts.get("club_name"), "sailing") if x)
        candidates.extend(_try_paid_clusters(query))
    if fetch:
        from search_everywhere import discovery_queries,google_news,web_hits
        import concurrent.futures
        ctx=dict(facts,id=facts["slug"],event_url=facts["url"])
        queries=discovery_queries(ctx)[:4]
        def query(q):
            return google_news(q,limit=4)+web_hits(q,limit=5)
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for hits in pool.map(query,queries):candidates.extend(hits)
    seen=set();unique=[]
    for item in candidates:
        from evidence_pipeline import canonical
        key=canonical(item.get("url") or item.get("source_url"))
        if key and key not in seen:
            seen.add(key);unique.append(item)
    cluster=verified_cluster(facts,unique,fetch=fetch)
    # extract() replaces og:image with the results card; keep this event's own artwork.
    if fetch:
        artwork=official_event_images(facts)
        if artwork:
            for article in cluster.get("articles") or []:
                if (article.get("verification") or {}).get("reason")!="official_results":
                    continue
                existing=list(article.get("images") or [])
                seen={x.get("url") for x in existing}
                for item in artwork:
                    if item["url"] not in seen:
                        existing.append(item)
                article["images"]=existing
                image=article.get("image") or ""
                if not image or "api/og" in image or _is_official_event_artwork(image):
                    article["image"]=artwork[0]["url"]
                break
    # The official record needs no network extraction and is always citation 1.
    cluster["articles"].sort(key=lambda a:a["verification"]["reason"]!="official_results")
    return cluster


def _wiki_url(url: str) -> bool:
    low = (url or "").lower()
    return any(token in low for token in ("wikipedia.org", "wikimedia.org", "upload.wikimedia", "commons.wikimedia"))


def _page_avatar_media(url: str) -> bool:
    match = re.search(r"media_id=(\d+)", url or "")
    if not match:
        return False
    mid = match.group(1)
    return mid.startswith("1000") and len(mid) == 15


def _facebook_page_chrome(url: str, image: str = "") -> bool:
    """Facebook page/profile OG images are logos. Posts and group albums can be photographs."""
    img = (image or "").lower()
    if "lookaside.fbsbx.com" in img or "/t39.30808-6/" in img:
        return False
    low = (url or "").lower()
    if "facebook.com" not in low:
        return False
    if any(
        token in low
        for token in ("/posts/", "/share/p/", "/share/g/", "/groups/", "/permalink", "/photo.php", "/photo/")
    ):
        return False
    path = urllib.parse.urlparse(low).path.strip("/")
    if path.endswith("/photos") or "/photos/" in low:
        return True
    return bool(path)


def _is_official_event_artwork(url: str) -> bool:
    path = urllib.parse.unquote(urllib.parse.urlparse(url or "").path).lower()
    return "/artwork/event logo/" in path


def _artwork_tokens(url: str) -> list[str]:
    name = urllib.parse.unquote(urllib.parse.urlparse(url or "").path.split("/")[-1])
    name = re.sub(r"\.[a-z0-9]+$", "", name, flags=re.I)
    name = re.sub(r"[-_]?(class[-_]?logo|event[-_]?logo|logo)$", "", name, flags=re.I)
    return [t for t in re.findall(r"[a-z0-9]+", name.lower()) if len(t) >= 3]


def artwork_matches_event(url: str, facts: dict) -> bool:
    """Keep Event Logo files that belong to this event. Drop rival-class artwork."""
    tokens = _artwork_tokens(url)
    if not tokens:
        return False
    title = (facts.get("title") or "").lower()
    slug = (facts.get("slug") or "").lower()
    classes = {
        str(c).lower()
        for c in ([facts.get("class_name")] + list(facts.get("class_names") or []))
        if c
    }
    hay = " ".join(
        x
        for x in (
            title,
            slug.replace("-", " "),
            " ".join(classes),
            (facts.get("club") or ""),
            (facts.get("club_name") or ""),
        )
        if x
    ).lower()
    hits = [t for t in tokens if t in hay]
    if len(hits) < 2:
        return False
    rivals = ("ilca", "laser", "dart", "505", "420", "j22", "hobie", "optimist", "dabchick", "mirror")
    for rival in rivals:
        if rival in tokens and rival not in hay and not any(rival in c for c in classes):
            return False
    return True


def official_event_images(facts: dict, html: str | None = None) -> list[dict]:
    """Photographs and this event's own artwork from the official event URL."""
    url = facts.get("url") or ""
    if html is None:
        if not url.startswith("http"):
            return []
        try:
            raw, _ = _http_get(url, UA, timeout=20)
            html = raw.decode("utf-8", "replace")
        except Exception:
            return []
    found = []
    seen = set()
    for src in re.findall(r'(?:src|content)=["\']([^"\']+)["\']', html or "", re.I):
        link = urllib.parse.urljoin(url or "https://sailingsa.co.za/", src)
        parsed = urllib.parse.urlsplit(link)
        link = urllib.parse.urlunsplit(
            (parsed.scheme, parsed.netloc, urllib.parse.unquote(parsed.path), "", "")
        )
        key = link
        if key in seen:
            continue
        if _is_official_event_artwork(link):
            if not artwork_matches_event(link, facts):
                continue
            seen.add(key)
            found.append(
                {
                    "url": key,
                    "source_url": url,
                    "title": facts.get("title") or "",
                    "credit": "SailingSA",
                    "kind": "official_event_artwork",
                }
            )
            continue
        if _bad_image_url(link) or _wiki_url(link):
            continue
        if not re.search(r"\.(jpe?g|png|webp)(\?|$)", link, re.I):
            continue
        if "sailingsa.co.za" in link.lower() and "/artwork/" in urllib.parse.unquote(link).lower():
            continue
        seen.add(key)
        found.append(
            {
                "url": link,
                "source_url": url,
                "title": facts.get("title") or "",
                "credit": "SailingSA",
                "kind": "event_page_photo",
            }
        )
    return found[:6]


def _bad_image_url(url: str) -> bool:
    if _is_official_event_artwork(url):
        return False
    low = (url or "").lower()
    if _wiki_url(low):
        return True
    if _page_avatar_media(low):
        return True
    if "/t39.30808-1/" in low:
        return True
    if "sailingsa.co.za/api/og" in low:
        return True
    return any(
        token in low
        for token in (
            "logo",
            "flogo",
            "reel",
            "badge",
            "burgee",
            "flag",
            "banner",
            "enternow",
            "enter-now",
            "enter_now",
            ".svg",
            "icon",
            "avatar",
            "profile",
            "sprite",
            "placeholder",
            "default-user",
            "favicon",
            "ytimg.com/vi",
            "youtube.com/img",
            "yt_1200",
            "sailingsa.co.za/static",
            "sailingsa.co.za/assets",
        )
    )


def crop_center_hero(src: pathlib.Path, dest: pathlib.Path, aspect: float = 16 / 9) -> pathlib.Path | None:
    """Clip top/bottom of a tall photo so the busiest band (boats) stays in a gold 16:9 frame."""
    try:
        from PIL import Image, ImageFilter
    except ImportError:
        return None
    if not src.is_file():
        return None
    im = Image.open(src).convert("RGB")
    w, h = im.size
    target_h = max(1, int(round(w / aspect)))
    if target_h >= h:
        dest.parent.mkdir(parents=True, exist_ok=True)
        im.save(dest, quality=88)
        return dest
    edges = im.convert("L").filter(ImageFilter.FIND_EDGES)
    energy = []
    pix = edges.load()
    for y in range(h):
        energy.append(sum(pix[x, y] for x in range(w)) / w)
    center_y = (h - target_h) // 2
    best_y = center_y
    best = sum(energy[center_y : center_y + target_h])
    run = best
    for y in range(1, h - target_h + 1):
        run += energy[y + target_h - 1] - energy[y - 1]
        if run > best:
            best = run
            best_y = y
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.crop((0, best_y, w, best_y + target_h)).save(dest, quality=88)
    return dest


def _image_size(raw: bytes) -> tuple[int, int] | None:
    if raw[:2] == b"\xff\xd8":
        i = 2
        while i < len(raw) - 8:
            if raw[i] != 0xFF:
                i += 1
                continue
            marker = raw[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h = int.from_bytes(raw[i + 5 : i + 7], "big")
                w = int.from_bytes(raw[i + 7 : i + 9], "big")
                return w, h
            if marker == 0xD8:
                i += 2
                continue
            if i + 4 > len(raw):
                break
            seglen = int.from_bytes(raw[i + 2 : i + 4], "big")
            i += 2 + seglen
        return None
    if raw[:8] == b"\x89PNG\r\n\x1a\n" and len(raw) >= 24:
        w = int.from_bytes(raw[16:20], "big")
        h = int.from_bytes(raw[20:24], "big")
        return w, h
    return None


def _flat_block_ratio(raw: bytes) -> float:
    try:
        from io import BytesIO

        from PIL import Image
    except ImportError:
        return 0.0
    try:
        im = Image.open(BytesIO(raw)).convert("RGB")
    except Exception:
        return 0.0
    block = 16
    w, h = im.size
    flats = total = 0
    for y in range(0, h - block + 1, block):
        for x in range(0, w - block + 1, block):
            crop = im.crop((x, y, x + block, y + block))
            total += 1
            if len(set(crop.getdata())) <= 6:
                flats += 1
    return flats / total if total else 0.0


def _is_event_photograph(raw: bytes) -> bool:
    """Keep prizegiving and on-water shots. Drop flags, logos, and 'enter now' posters."""
    if not raw or len(raw) < 12000:
        return False
    size = _image_size(raw)
    if not size:
        return False
    w, h = size
    if min(w, h) < 320:
        return False
    aspect = w / h if h else 0
    if aspect < 0.62 or aspect > 1.85:
        return False
    if 0.92 <= aspect <= 1.08 and min(w, h) >= 600:
        return False
    if _flat_block_ratio(raw) >= 0.55:
        return False
    return True


def _wrong_class(blob: str, klass: str) -> bool:
    blob = (blob or "").lower()
    klass = (klass or "").strip()
    for token in WRONG_CLASS.get(klass, ()):
        if re.search(r"(?<![a-z0-9])" + re.escape(token) + r"(?![a-z0-9])", blob):
            return True
    return False


LOOKASIDE_RE = re.compile(r"https://lookaside\.fbsbx\.com/lookaside/crawler/media/\?media_id=\d+")
CLASS_GALLERIES = {
    "Dabchick": "https://www.revolutionise.com.au/dabchickca/",
    "505": "https://rsa505.org.za/",
    "420": "https://www.facebook.com/420nationalssouthafrica/",
    "Dart 18": "https://www.facebook.com/henleymidmaryachtclub",
}


def harvest_source_images(url: str) -> list[dict]:
    """Pull photographs from the event's own page. Never wiki."""
    if not url or not url.startswith("http") or _wiki_url(url):
        return []
    if "facebook.com" in url:
        return facebook_source_images(url)
    return website_source_images(url)


def facebook_source_images(url: str) -> list[dict]:
    try:
        from facebook_cross_share import resolve_facebook_url

        resolved = resolve_facebook_url(url)
    except Exception:
        resolved = {"canonical_url": url, "title": "", "image": ""}
    out = []
    source = resolved.get("canonical_url") or url
    credit = _credit_from_url(source)
    if resolved.get("image") and not _bad_image_url(resolved["image"]):
        out.append(
            {
                "url": resolved["image"],
                "source_url": source,
                "title": resolved.get("title") or "",
                "credit": credit,
            }
        )
    html = ""
    for headers in (FB_UA, {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15", "Accept": "text/html"}):
        try:
            raw, _ = _http_get(resolved.get("canonical_url") or url, headers, timeout=20)
            html = raw.decode("utf-8", "replace")
            if "og:title" in html.lower() or "og:image" in html.lower():
                break
        except Exception:
            continue
    seen = {item["url"] for item in out}
    for link in LOOKASIDE_RE.findall(html):
        if link in seen or _bad_image_url(link):
            continue
        seen.add(link)
        out.append({"url": link, "source_url": source, "title": resolved.get("title") or "", "credit": credit})
        if len(out) >= 12:
            break
    return out


def website_source_images(url: str) -> list[dict]:
    try:
        from bs4 import BeautifulSoup

        raw, _ = _http_get(url, UA, timeout=20)
        soup = BeautifulSoup(raw, "html.parser")
    except Exception:
        return None if False else []
    credit = _credit_from_url(url)
    title = ""
    if soup.title:
        title = soup.title.get_text(" ", strip=True)
    found = []
    for tag in soup.select('meta[property="og:image"], meta[name="twitter:image"], article img, main img, .gallery img, img'):
        src = tag.get("content") or tag.get("src") or tag.get("data-src") or ""
        if not src:
            continue
        link = urllib.parse.urljoin(url, src)
        if _bad_image_url(link) or _wiki_url(link):
            continue
        if not re.search(r"\.(jpe?g|png|webp)(\?|$)", link, re.I):
            continue
        alt = (tag.get("alt") or title or "").strip()
        found.append({"url": link, "source_url": url, "title": alt, "credit": credit})
    # Class homepages often lead with a team lineup; keep later gallery shots.
    gallery = [item for item in found if "gallery" in (item.get("url") or "").lower()]
    if len(gallery) >= 3:
        skip = gallery[0]["url"]
        found = [item for item in found if item["url"] != skip]
    uniq = []
    seen = set()
    for item in found:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        uniq.append(item)
    return uniq[:16]


def class_gallery_photo(klass: str) -> dict | None:
    page = CLASS_GALLERIES.get((klass or "").strip())
    if not page:
        return None
    images = harvest_source_images(page)
    for item in images:
        if not _bad_image_url(item.get("url") or ""):
            return item
    return None


def admin_seed_images(facts: dict) -> list[dict]:
    """Admin-valid local photographs (WhatsApp / race office). Portrait is allowed."""
    found = []
    for item in SEED_PHOTOS.get(facts.get("slug") or "", []):
        name = pathlib.Path(item.get("file") or "").name
        if not name:
            continue
        path = SEED_MEDIA / name
        if not path.is_file():
            continue
        found.append(
            {
                "url": path.resolve().as_uri(),
                "file": name,
                "source_url": item.get("source_url") or "",
                "title": item.get("title") or facts.get("title") or "",
                "credit": item.get("credit") or "event administration",
                "kind": item.get("kind") or "admin_seed",
                "score": int(item.get("score") or 80),
            }
        )
    return found


def _event_photo_score(item: dict, facts: dict) -> int:
    """Score only photographs that belong to this event. Wiki and stock boats lose."""
    if (item.get("kind") or "") == "admin_seed":
        return int(item.get("score") or 80)
    klass = (facts.get("class_name") or "").strip()
    blob = " ".join((item.get("url") or "", item.get("source_url") or "", item.get("title") or "")).lower()
    photo = (item.get("url") or "").lower()
    source = (item.get("source_url") or "").lower()
    n = 0
    if _wiki_url(blob) or _wiki_url(photo) or _wiki_url(source):
        return -10000
    if _is_official_event_artwork(photo):
        return 45 if artwork_matches_event(photo, facts) else -90
    if _bad_image_url(photo) or _wrong_class(blob, klass):
        return -100
    if _facebook_page_chrome(source, photo) and "facebook.com" in source:
        return -80
    if klass and klass.lower() in blob:
        n += 30
    if "1pgpy1pgh1" in blob or "1633819895206118" in blob:
        n += 220
    if "1MHJNWcFSM".lower() in blob or "230542873685522" in blob:
        n += 140
    if "19VLSkGHBk".lower() in blob or "310727125653436" in blob:
        n += 140
    if "420nationalssouthafrica" in blob and klass == "420":
        n += 160
    if "id=338" in source or "505-nationals-2026" in blob:
        n += 180
    if "rsa505.org.za" in blob and klass == "505":
        n += 80
    if "20261013" in photo:
        n += 60
    if "dabchickca/events/358939" in blob and klass == "Dabchick":
        n += 180
    if "novanews" in blob and "hermanus-high-schools-sailors" in blob:
        n += 90
    if "hmyc.org.za/events/367984" in blob:
        n += 80
    if any(k in blob for k in ("prize", "trophy", "podium", "final result")):
        n += 50
    if "lookaside.fbsbx.com" in photo or "scontent" in photo:
        n += 70
    if "cdn.revolutionise.com.au/events/" in photo:
        n += 40
    if "wp-content/uploads/2026/09" in photo:
        n += 40
    if photo.endswith(".jpg") or photo.endswith(".jpeg") or "lookaside" in photo:
        n += 15
    path = urllib.parse.urlparse(source).path.strip("/")
    host = urllib.parse.urlparse(source).netloc.lower()
    if path in ("", "home") and "facebook.com" not in host and "rsa505.org.za" not in host:
        n -= 80
    if "enter now" in blob:
        n -= 10
    return n


def pick_images(facts: dict, cluster: dict, pack: dict | None = None, limit: int = 2) -> list[dict]:
    """Prizegiving and on-the-water shots from this event's sources. Never wiki or logos."""
    candidates = []
    seen = set()
    from evidence_pipeline import canonical, MEDIA_EXCLUSIONS
    accepted_sources = {canonical(x.get("url")) for x in cluster.get("articles", [])}

    def add(item: dict):
        url = (item.get("url") or "").split("#")[0]
        source = item.get("source_url") or ""
        admin = (item.get("kind") or "") == "admin_seed"
        if admin:
            key = item.get("file") or url
            if not key or key in seen:
                return
            seen.add(key)
            candidates.append(item)
            return
        if cluster.get("schema_version") == "verified-evidence-1" and canonical(source) not in accepted_sources:
            return
        if not url or url in seen or _wiki_url(url) or _bad_image_url(url) or canonical(url) in MEDIA_EXCLUSIONS:
            return
        if _facebook_page_chrome(source, url) and _event_photo_score(item, facts) < 40:
            return
        seen.add(url)
        candidates.append(item)

    for item in admin_seed_images(facts):
        add(item)

    for item in (cluster or {}).get("articles") or []:
        if item.get("image"):
            add(
                {
                    "url": item["image"],
                    "source_url": item.get("url") or item.get("share_url") or "",
                    "title": item.get("title") or facts["title"],
                    "credit": _credit_from_url(item.get("url") or item["image"]),
                    "kind": "official_event_artwork" if _is_official_event_artwork(item["image"]) else "",
                }
            )
    for document in (cluster or {}).get("articles") or []:
        for attachment in document.get("images") or []:
            add({"url":attachment["url"],"source_url":document.get("url") or "",
                 "title":attachment.get("title") or facts["title"],"credit":_credit_from_url(document.get("url") or ""),
                 "kind":attachment.get("kind") or ("official_event_artwork" if _is_official_event_artwork(attachment.get("url") or "") else "")})
    for img in (pack or {}).get("images") or []:
        if img.get("image_url"):
            add(
                {
                    "url": img["image_url"],
                    "source_url": img.get("source_url") or "",
                    "title": img.get("source_title") or facts["title"],
                    "credit": pretty_credit(img.get("platform") or "", img.get("source_url") or img.get("image_url") or ""),
                    "kind": img.get("kind") or "",
                }
            )
    ranked = [item for item in candidates if _event_photo_score(item, facts) >= 40]
    ranked.sort(key=lambda item: _event_photo_score(item, facts), reverse=True)
    return ranked[:limit]


def pick_image(facts: dict, cluster: dict, pack: dict | None = None) -> dict | None:
    chosen = pick_images(facts, cluster, pack, limit=1)
    return chosen[0] if chosen else None


def pretty_credit(raw: str, url: str = "") -> str:
    credit = (raw or "").strip()
    if credit and "event administration" in credit.lower():
        return credit
    blob = f"{raw or ''} {url or ''}".lower()
    if "novanews" in blob:
        return "NovaNews"
    if "artwork/event logo" in blob or "sailingsa.co.za/regatta/" in blob:
        return "SailingSA"
    if "420nationalssouthafrica" in blob:
        return "420 Sailing South Africa"
    if "rsa505" in blob:
        return "RSA 505"
    if "dabchick" in blob or "revolutionise.com.au/dabchickca" in blob:
        return "Dabchick Class Association"
    if "henleymidmar" in blob or "hmyc" in blob:
        return "Henley Midmar Yacht Club"
    if "theewater" in blob:
        return "Theewater Sports Club"
    if "aeolians" in blob:
        return "Aeolians Yacht Club"
    if "ldyclub" in blob or "lake deneys" in blob or "ldyc" in blob:
        return "Lake Deneys Yacht Club"
    if "milnertonaquatic" in blob or "milnerton aquatic" in blob:
        return "Milnerton Aquatic Club"
    if "youtube" in blob or "youtu.be" in blob:
        return "YouTube"
    if "facebook" in blob or "fbcdn" in blob or "lookaside.fbsbx" in blob:
        return "Facebook / host club"
    host = urllib.parse.urlparse(url or raw or "").netloc.lower().removeprefix("www.")
    return host or (raw or "source").strip()


def _credit_from_url(url: str) -> str:
    return pretty_credit("", url)


def _local_seed_path(image: dict) -> pathlib.Path | None:
    name = pathlib.Path((image or {}).get("file") or "").name
    if name:
        path = SEED_MEDIA / name
        if path.is_file():
            return path
    url = (image or {}).get("url") or ""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme == "file" and parsed.path:
        path = pathlib.Path(urllib.parse.unquote(parsed.path))
        if path.is_file():
            return path
    return None


def download_image(image: dict, issue: str, slug: str, index: int = 0) -> dict | None:
    url = (image or {}).get("url") or ""
    admin = (image or {}).get("kind") == "admin_seed"
    seed = _local_seed_path(image) if admin or (image or {}).get("file") else None
    if not admin and (not url or _wiki_url(url)):
        return None
    dest_dir = ROOT / "public" / "issues" / issue / "media"
    dest_dir.mkdir(parents=True, exist_ok=True)
    source_dir = ROOT / "issues" / issue / "media"
    source_dir.mkdir(parents=True, exist_ok=True)
    ext = ".jpg"
    path = urllib.parse.urlparse(url).path.lower()
    if seed:
        path = seed.name.lower()
    for cand in (".png", ".webp", ".jpeg", ".jpg"):
        if path.endswith(cand):
            ext = ".jpg" if cand == ".jpeg" else cand
            break
    if "lookaside.fbsbx" in url or "fbcdn" in url:
        ext = ".jpg"
    suffix = "" if index == 0 else f"-{index + 1}"
    filename = slug + suffix + ext
    dest = dest_dir / filename
    if seed:
        raw = seed.read_bytes()
        ctype = "image/jpeg"
    else:
        headers = dict(
            FB_UA
            if any(token in url for token in ("fbcdn", "facebook.com", "lookaside.fbsbx"))
            else UA
        )
        headers["Accept"] = "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
        try:
            raw, ctype = _http_get(url, headers, timeout=25)
        except Exception:
            return None
    if len(raw) < 8000 or (ctype and not str(ctype).startswith("image") and raw[:3] not in (b"\xff\xd8\xff", b"\x89PN")):
        return None
    official = _is_official_event_artwork(url) or image.get("kind") == "official_event_artwork"
    if not official and not admin and not _is_event_photograph(raw):
        return None
    dest.write_bytes(raw)
    (source_dir / filename).write_bytes(raw)
    if admin:
        hero_name = pathlib.Path(filename).stem + "-hero.jpg"
        hero_dest = dest_dir / hero_name
        if crop_center_hero(dest, hero_dest):
            dest.write_bytes(hero_dest.read_bytes())
            (source_dir / filename).write_bytes(hero_dest.read_bytes())
            raw = dest.read_bytes()
    out = dict(image)
    out["url"] = "media/" + filename
    out["local_path"] = str(dest)
    out["bytes"] = len(raw)
    out["digest"] = hashlib.md5(raw).hexdigest()
    return out


def layout_for(index: int, article_type: str) -> str:
    if article_type == "feature":
        return "lead"
    return LAYOUTS[index % len(LAYOUTS)]


def rewrite_event(issue: str, facts: dict, pack: dict | None = None, cluster: dict | None = None, layout: str = "classic") -> dict:
    facts = dict(facts)
    facts["finished"] = event_finished(facts, issue)
    fetched_cluster = cluster is None
    cluster = cluster or cluster_coverage(facts, pack, fetch=True)
    cites = citation_index(cluster, facts)
    paras = rewrite_paragraphs(facts, cluster, cites)
    headline = unique_headline(facts, cluster)
    fleets = facts.get("fleets") or [
        {"class_name": facts.get("class_name") or "", "leaderboard": facts.get("leaderboard") or leaderboard([])}
    ]
    images = pick_images(facts, cluster, pack, limit=2)
    locals = []
    seen_hash = set()
    for idx, image in enumerate(images):
        local = download_image(image, issue, facts["slug"], index=idx)
        if not local:
            continue
        digest = local.get("digest") or local.get("url")
        if digest in seen_hash:
            continue
        seen_hash.add(digest)
        locals.append(local)
    blocks = []
    from evidence_pipeline import photo_caption
    for local in locals:
        credit = pretty_credit(local.get("credit") or "", local.get("source_url") or local.get("url") or "")
        blocks.append(
            {
                "type": "image",
                "url": local["url"],
                "alt": local.get("title") or facts["title"],
                "caption": photo_caption(local,facts,cluster) + f" Photo: {credit}.",
                "credit": credit,
                "source_url": local.get("source_url") or facts["url"],
                "rights_status": "source_attributed",
                "kind": local.get("kind") or "",
            }
        )
    if any((local.get("kind") or "") == "admin_seed" for local in locals):
        layout = "photo-led"
    for text in paras:
        blocks.append({"type": "paragraph", "text": text})
    multi = bool(facts.get("multi_class"))
    official = bool(facts.get("official_order"))
    for fleet in fleets:
        cols, table = fleet.get("leaderboard") or leaderboard([], official=official)
        klass = (fleet.get("class_name") or "").strip()
        blocks.append({"type": "heading", "text": board_label(klass, multi, official)})
        blocks.append(
            {
                "type": "results",
                "source_event_url": facts["url"],
                "class_name": klass,
                "columns": cols,
                "rows": table,
                "as_of": issue,
            }
        )
    sources = [item["url"] for item in cites]
    for item in cluster.get("articles") or []:
        if item.get("url") and item["url"] not in sources and not _wiki_url(item["url"]):
            sources.append(item["url"])
    hero = locals[0] if locals else None
    article = {
        "id": facts["slug"],
        "type": "regatta_report",
        "headline": headline,
        "deck": deck_from_facts(facts),
        "byline": "SailingSA",
        "kicker": (
            " / ".join(c for c in (facts.get("class_names") or [facts.get("class_name")]) if c) or "Regatta"
        ).upper()
        + "  ·  "
        + facts["club"],
        "published_at": issue,
        "event_id": facts["slug"],
        "layout": layout,
        "hero_image": {"url": hero["url"], "source_url": hero.get("source_url"), "rights_status": "source_attributed"} if hero else None,
        "blocks": blocks,
        "sources": sources,
        "citations": cites,
        "review_status": "rewritten",
        "club": facts["club"],
        "class_name": facts["class_name"],
        "class_names": facts.get("class_names") or [facts.get("class_name") or ""],
        "host_club_slug": facts.get("host_club_slug") or "",
        "start_date": facts["start"],
        "end_date": facts["end"],
        "cluster_count": cluster.get("count") or 0,
    }
    dest = ROOT / "issues" / issue / "sources"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{facts['slug']}-cluster.json").write_text(json.dumps(cluster, indent=2, ensure_ascii=False))
    return article


def _seed_event_images(facts: dict) -> list[dict]:
    """Last resort: scrape this event's seed URLs. Never wiki or a club homepage stock shot."""
    found = []
    for url in SEED_URLS.get(facts.get("slug") or "", []):
        if _wiki_url(url):
            continue
        for item in harvest_source_images(url):
            if _event_photo_score(item, facts) >= 40:
                found.append(item)
    found.sort(key=lambda item: _event_photo_score(item, facts), reverse=True)
    uniq = []
    seen = set()
    for item in found:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        uniq.append(item)
    return uniq[:2]


def _image_as_hero(block: dict) -> dict:
    return {
        "url": block.get("url") or "",
        "source_url": block.get("source_url") or "",
        "rights_status": block.get("rights_status") or "source_attributed",
    }


def weekend_hero_block(articles: list[dict]) -> dict | None:
    """Edition hero: admin-seed photograph first, then a real photo, never a logo dump."""
    reports = [a for a in articles if a.get("type") == "regatta_report"]
    images = []
    for article in reports:
        for block in article.get("blocks") or []:
            if block.get("type") == "image" and block.get("url"):
                images.append(block)
        hero = article.get("hero_image") or {}
        if hero.get("url") and not any(b.get("url") == hero["url"] for b in images):
            images.append(
                {
                    "type": "image",
                    "url": hero["url"],
                    "source_url": hero.get("source_url") or "",
                    "rights_status": hero.get("rights_status") or "source_attributed",
                    "kind": hero.get("kind") or "",
                    "credit": hero.get("credit") or "",
                    "alt": article.get("headline") or "",
                    "caption": "",
                }
            )
    for block in images:
        if (block.get("kind") or "") == "admin_seed":
            return block
    for block in images:
        kind = block.get("kind") or ""
        url = (block.get("url") or "").lower()
        if kind == "official_event_artwork" or url.endswith(".png"):
            continue
        return block
    return images[0] if images else None


def attach_weekend_hero(feature: dict, articles: list[dict]) -> dict:
    """Put the weekend photograph on the edition lead, landing, and NewsArticle image."""
    block = weekend_hero_block(articles)
    if not block:
        return feature
    feature["hero_image"] = _image_as_hero(block)
    blocks = list(feature.get("blocks") or [])
    if not any(b.get("type") == "image" and b.get("url") == block.get("url") for b in blocks):
        feature["blocks"] = [
            {
                "type": "image",
                "url": block.get("url") or "",
                "alt": block.get("alt") or "Weekend sailing",
                "caption": block.get("caption") or "",
                "credit": block.get("credit") or "",
                "source_url": block.get("source_url") or "",
                "rights_status": block.get("rights_status") or "source_attributed",
                "kind": block.get("kind") or "",
            }
        ] + blocks
    return feature


def apply_admin_seed_to_article(issue: str, article: dict) -> dict:
    """Attach a seeded photograph to an already-written report (rebuild without a full scrape)."""
    slug = article.get("event_id") or article.get("id") or ""
    facts = {
        "slug": slug,
        "title": article.get("headline") or slug,
        "class_name": article.get("class_name") or "",
        "url": f"https://sailingsa.co.za/regatta/{slug}" if slug else "",
    }
    locals = []
    for idx, image in enumerate(admin_seed_images(facts)):
        local = download_image(image, issue, slug, index=idx)
        if local:
            locals.append(local)
    if not locals:
        return article
    existing = {b.get("url") for b in article.get("blocks") or []}
    new_blocks = []
    for local in locals:
        if local["url"] in existing:
            continue
        credit = pretty_credit(local.get("credit") or "", local.get("source_url") or "")
        new_blocks.append(
            {
                "type": "image",
                "url": local["url"],
                "alt": local.get("title") or article.get("headline") or slug,
                "caption": f"{article.get('headline') or slug}. Photo: {credit}.",
                "credit": credit,
                "source_url": local.get("source_url") or facts["url"],
                "rights_status": "source_attributed",
                "kind": local.get("kind") or "admin_seed",
            }
        )
    article["blocks"] = new_blocks + list(article.get("blocks") or [])
    hero = locals[0]
    article["hero_image"] = {
        "url": hero["url"],
        "source_url": hero.get("source_url") or facts["url"],
        "rights_status": "source_attributed",
    }
    article["layout"] = "photo-led"
    return article


def rewrite_weekend_feature(issue,monday,events,articles):
    from evidence_pipeline import feature
    return attach_weekend_hero(feature(issue,monday,events,articles), articles)
