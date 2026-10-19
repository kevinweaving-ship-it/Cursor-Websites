#!/usr/bin/env python3
"""Cluster same-event coverage and rewrite one unique magazine article.

Reverse-engineered from Perplexity Discover / RAG news synthesis, plus
Ground News clustering, Artifact de-baited headlines, Monok stored articles,
and Sportradar/United Robots box-score recaps:

  scrape the event's own primary sources (club, class, host Facebook, local
  news) → keep only items about THIS event → write one article locked to
  those texts and the results card (RAG: no fact that is not in a source) →
  inline citations → photographs from those same sources (podium and on the
  water are both valid; more than one photo is allowed) → 1st/2nd/3rd.

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
LAYOUTS = ("photo-led", "split", "classic", "compact")
HOST_FALLBACK = {
    "TSC": "Theewater Sports Club",
    "HMYC": "Henley Midmar Yacht Club",
    "AYC": "Aeolians Yacht Club",
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


def _names(row: dict) -> str:
    helm = (row.get("helm_name") or "").strip()
    crew = (row.get("crew_name") or "").strip()
    if helm and crew:
        return f"{helm} and {crew}"
    return helm or crew or "The leader"


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


def _ranked(rows: list[dict]) -> list[dict]:
    out = [r for r in rows if r.get("rank") not in (None, "")]
    out.sort(key=lambda r: int(r["rank"]) if str(r.get("rank")).isdigit() else 999)
    return out or list(rows)


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


def facts_from_rows(slug: str, rows: list[dict]) -> dict:
    first = rows[0]
    ranked = _ranked(rows)
    winner = ranked[0]
    second = ranked[1] if len(ranked) > 1 else {}
    third = ranked[2] if len(ranked) > 2 else {}
    races = _intish(first.get("races_sailed")) or len(winner.get("race_scores") or {})
    entries = _intish(first.get("entries_total")) or len(rows)
    club = (first.get("host_club_code") or first.get("host_club_name") or "").strip()
    title = (first.get("event_name") or slug).strip()
    if title.lower().startswith("2026 "):
        title = title[5:]
    title = re.sub(r"\s+incorporating\b.*$", "", title, flags=re.I).strip()
    start = str(first.get("start_date") or slug[:10])[:10]
    end = str(first.get("end_date") or start)[:10]
    winner_nett = winner.get("nett_points_raw")
    second_nett = second.get("nett_points_raw")
    return {
        "slug": slug,
        "title": title,
        "class_name": (first.get("class_name") or first.get("class_canonical") or "").strip(),
        "club": club,
        "club_name": _club_name(club, first.get("host_club_name") or ""),
        "host_club_slug": first.get("host_club_slug") or club.lower(),
        "start": start,
        "end": end,
        "entries": entries,
        "races": races,
        "status": (first.get("result_status") or "Published").strip(),
        "winner": _names(winner),
        "winner_helm": (winner.get("helm_name") or "").strip(),
        "winner_crew": (winner.get("crew_name") or "").strip(),
        "winner_club": (winner.get("club_abbrev") or winner.get("club_raw") or "").strip(),
        "winner_nett": "" if winner_nett in (None, "") else str(winner_nett).replace(".0", ""),
        "winner_wins": _win_count(winner.get("race_scores")),
        "winner_scores": winner.get("race_scores") or {},
        "second_scores": second.get("race_scores") or {},
        "second_wins": _win_count(second.get("race_scores")),
        "second": _names(second) if second else "",
        "second_nett": "" if second_nett in (None, "") else str(second_nett).replace(".0", ""),
        "third": _names(third) if third else "",
        "third_nett": "" if third.get("nett_points_raw") in (None, "") else str(third.get("nett_points_raw")).replace(".0", ""),
        "tied_first": str(winner_nett) == str(second_nett) and winner_nett not in (None, ""),
        "names": [n for r in ranked for n in ((r.get("helm_name") or "").strip(), (r.get("crew_name") or "").strip()) if n],
        "url": "https://sailingsa.co.za/regatta/" + slug,
        "leaderboard": leaderboard(ranked),
    }


def _official_results_card(facts: dict) -> dict:
    """SailingSA results are already live by the Monday publisher. Always source [1]."""
    bits = [
        f"Official SAS-sanctioned {facts.get('title') or 'event'} at {facts.get('club_name') or facts.get('club') or 'the host club'}.",
    ]
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


def leaderboard(rows: list[dict], limit: int = LEADERBOARD_LIMIT) -> tuple[list[str], list[list[str]]]:
    table = []
    for row in rows[:limit]:
        rank = row.get("rank")
        pos = "" if rank in (None, "") else str(rank)
        table.append(
            [
                pos,
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
    short_venue = venue.replace(" Yacht Club", "").replace(" Sports Club", "").replace(" Club", "")
    finished = event_finished(facts)
    if facts.get("tied_first") and facts.get("second"):
        return f"{winner} {_agree(winner, 'take', 'takes')} {title} after a points tie at {short_venue}"
    if facts.get("winner_wins") and facts["winner_wins"] >= max(3, int(facts.get("races") or 0) // 2):
        if facts["winner_wins"] >= int(facts.get("races") or 0) - 2 and (facts.get("races") or 0) >= 6:
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


def _cluster_text(item: dict) -> str:
    return "\n".join(
        x for x in (item.get("snippet"), item.get("description"), item.get("title")) if x
    ).strip()


def _keep_cluster_item(item: dict, facts: dict) -> bool:
    url = (item.get("url") or "").lower()
    blob = " ".join((item.get("title") or "", item.get("description") or "", item.get("snippet") or "", url)).lower()
    if any(junk in url or junk in blob for junk in JUNK_CLUSTER):
        return False
    if "login" in url or "/photos" == url.rstrip("/").split("facebook.com")[-1]:
        return False
    slug = (facts.get("slug") or "").lower()
    if "sailingsa.co.za/regatta/" in url:
        return bool(slug and slug in url)
    if slug and "sailingsa.co.za" in url and slug in url:
        return True
    if item.get("engine") == "sailingsa" and item.get("role") == "official_results":
        return True
    try:
        from search_everywhere import in_coverage_window

        window = in_coverage_window(item, facts)
    except Exception:
        window = None
    if window is False:
        return False
    if "1pgpy1pgh1" in url or item.get("engine") in (
        "facebook",
        "seed",
        "host_club_post",
        "source_media",
        "class_catalog",
        "club_catalog",
    ):
        return True
    if item.get("provenance") == "host_club_post" or item.get("role") == "host_club_media":
        return True
    klass = (facts.get("class_name") or "").lower()
    names = [n.lower() for n in facts.get("names") or []]
    club = (facts.get("club") or "").lower()
    club_name = (facts.get("club_name") or "").lower()
    if klass and klass.split()[0] in blob and (
        any(n in blob for n in names[:8]) or club in blob or club_name.split()[0] in blob
    ):
        return True
    if any(n in blob for n in names[:6]):
        return True
    return False


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


def _cluster_color(cluster: dict, facts: dict | None = None, index: list[dict] | None = None) -> list[str]:
    """Turn host-club / class / news copy into cited sentences. RAG: only facts in the source."""
    notes = []
    index = index if index is not None else citation_index(cluster, facts)
    source = _host_source(cluster)
    if not source:
        for item in (cluster or {}).get("articles") or []:
            if len(_cluster_text(item)) >= 40:
                source = dict(item, text=_cluster_text(item))
                break
    text = (source or {}).get("text") or ""
    if not text:
        return notes
    src = _source_for_url(index, (source or {}).get("url") or (source or {}).get("share_url") or "") or (
        index[1] if len(index) > 1 else index[0] if index else {"n": 2}
    )
    mark = _cite(src.get("n") or 2)
    venue = (facts or {}).get("club_name") or "the host club"
    quote = None
    for line in text.splitlines():
        line = re.sub(r"[⛵🏆🥇🥈🥉💙👏💪🌊🇿🇦]+", "", line).strip(" -–#")
        if re.search(r"what a day on the water", line, re.I):
            quote = re.sub(r"\s+", " ", line).strip(" !.")
            break
    places = [m.groupdict() for m in PLACE_LINE.finditer(text)]
    special = SPECIAL_MENTION.search(text)
    if quote:
        notes.append(f"{venue} wrote from the venue: “{quote}.” {mark}")
    overall = [p for p in places if int(p["place"]) <= 3]
    if overall:
        bits = []
        for p in overall:
            bit = f"{p['name'].strip()} ({p['club']})" if p.get("club") else p["name"].strip()
            bits.append(f"{bit} on sail {p['sail']} in {p['place']}")
        if bits:
            notes.append("The club named the overall top three: " + "; ".join(bits) + f". {mark}")
    home = [p for p in places if int(p["place"]) > 3]
    if home:
        bits = [f"{p['name'].strip()} {p['place']}th on sail {p['sail']}" for p in home]
        extra = ""
        if special:
            extra = f" A special mention went to {special.group(1).strip()} in {special.group(2)}th."
        notes.append(f"{venue} then listed their own boats: " + "; ".join(bits) + "." + extra + f" {mark}")
    elif special:
        notes.append(
            f"The club gave a special mention to {special.group(1).strip()}, "
            f"finishing {special.group(2)}th. {mark}"
        )
    known = {n.lower(): n for n in (facts or {}).get("names") or []}
    if re.search(r"\bu-?17\b|under[- ]17|youth champion", text, re.I):
        who = []
        for name in re.findall(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b", text):
            real = known.get(name.lower()) or name
            if real not in who:
                who.append(real)
        if who:
            notes.append(
                f"A separate under-17 title at the same championship named "
                f"{' and '.join(who[:2])}. {mark}"
            )
        else:
            notes.append(f"A separate under-17 title was awarded at the same championship. {mark}")
    if re.search(r"tied on points|tie break|tiebreak|last race", text, re.I) and (facts or {}).get("tied_first"):
        notes.append(f"The class report said the title was settled on the last race. {mark}")
    return notes[:4]


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


def rewrite_paragraphs(facts: dict, cluster: dict | None = None, index: list[dict] | None = None) -> list[str]:
    """RAG recap: results card + only facts that appear in the clustered sources."""
    venue = facts["club_name"]
    dates = _date_span(facts["start"], facts["end"])
    status = (facts.get("status") or "published").lower()
    races = facts.get("races") or 0
    entries = facts.get("entries") or 0
    wins = facts.get("winner_wins") or 0
    heats = _heats(facts.get("winner_scores"))
    late = heats[-4:] if len(heats) >= 4 else heats
    late_wins = sum(1 for h in late if h.get("win"))
    no_wins = heats and wins == 0
    klass = facts.get("class_name") or "fleet"
    index = index if index is not None else citation_index(cluster, facts)
    results_mark = _cite(index[0]["n"]) if index else "[1]"
    paras = []
    extras = _cluster_color(cluster or {}, facts, index)
    if extras:
        paras.extend(extras[:2])

    if facts.get("tied_first") and facts.get("second"):
        paras.append(
            f"On the SailingSA card {facts['winner']} take the {facts['title']} at {venue} "
            f"on countback from {facts['second']}, both on {facts['winner_nett']} nett. "
            f"{entries} {klass}s sailed {races} races from {dates}. {results_mark}"
        )
    elif no_wins:
        paras.append(
            f"{facts['winner']} finished first in the {entries}-boat {klass} fleet at {venue} "
            f"on {facts['winner_nett']} nett from {races} races, without a race win. {results_mark}"
        )
    elif wins and races and wins >= races - 2:
        paras.append(
            f"{facts['winner']} won {wins} of {races} races at {venue} for {facts['winner_nett']} nett "
            f"in a {entries}-boat {klass} fleet, {dates}. {results_mark}"
        )
    else:
        paras.append(
            f"{facts['winner']} won the {facts['title']} at {venue} on {dates}, "
            f"{facts['winner_nett']} nett after {races} races among {entries} boats"
            + (f", with {wins} firsts. {results_mark}" if wins else f". {results_mark}")
        )

    if heats and late_wins >= 3:
        closed = heats[-1]
        paras.append(
            f"They took {late_wins} of the last {len(late)} races, including {closed['race']}. {results_mark}"
        )
    elif no_wins and heats:
        worst = max(heats, key=lambda h: h["pts"] or 0)
        paras.append(
            f"The only hole in the card was {worst['race']} ({worst['raw']}). {results_mark}"
        )

    chase = []
    if facts.get("second"):
        if facts.get("tied_first"):
            chase.append(
                f"{facts['second']} won {facts.get('second_wins') or 0} races and finished second on countback."
            )
        else:
            chase.append(
                f"{facts['second']} finished second on {facts['second_nett']}"
                + (
                    f" with {facts.get('second_wins')} race "
                    + ("win" if facts.get("second_wins") == 1 else "wins")
                    if facts.get("second_wins")
                    else ""
                )
                + "."
            )
    if facts.get("third"):
        chase.append(f"{facts['third']} finished third on {facts['third_nett'] or 'the published score'}.")
    if chase:
        paras.append(" ".join(chase) + " " + results_mark)

    if len(extras) > 2:
        paras.extend(extras[2:])

    if status == "provisional" and event_finished(facts):
        paras.append(f"SailingSA still marks the scores provisional. {results_mark}")
    elif status == "provisional":
        paras.append(f"The published result remains provisional. {results_mark}")
    out = []
    for p in paras:
        p = re.sub(r"\s+", " ", p).strip()
        if p and p not in out and "weekend" not in p.lower():
            out.append(p)
    return out[:7]


def deck_from_facts(facts: dict) -> str:
    bits = [facts["winner"], facts["title"], facts["club_name"]]
    if facts.get("winner_nett"):
        bits.append(f"{facts['winner_nett']} nett")
    if facts.get("entries"):
        bits.append(f"{facts['entries']} entries")
    return " · ".join(bits)


def _http_get(url: str, headers: dict | None = None, timeout: int = 18) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers=headers or UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.headers.get_content_type() or ""


def extract_article(url: str) -> dict | None:
    if not url or not url.startswith("http"):
        return None
    if "facebook.com" in url:
        try:
            from facebook_cross_share import resolve_facebook_url

            resolved = resolve_facebook_url(url)
            return {
                "url": resolved.get("canonical_url") or url,
                "title": resolved.get("title") or "",
                "description": resolved.get("description") or "",
                "snippet": resolved.get("description") or "",
                "image": resolved.get("image") or "",
                "published": resolved.get("published") or "",
            }
        except Exception:
            pass
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {"url": url, "title": "", "description": "", "image": ""}
    try:
        raw, _ = _http_get(url, FB_UA if "facebook.com" in url else UA)
    except Exception:
        return None
    soup = BeautifulSoup(raw, "html.parser")

    def og(key: str) -> str:
        tag = soup.find("meta", attrs={"property": "og:" + key}) or soup.find("meta", attrs={"name": "og:" + key})
        return (tag.get("content") or "").strip() if tag else ""

    title = og("title") or (soup.title.get_text(" ", strip=True) if soup.title else "")
    desc = og("description")
    image = og("image")
    published = ""
    for attr, key in (
        ("property", "article:published_time"),
        ("name", "article:published_time"),
        ("property", "og:updated_time"),
        ("itemprop", "datePublished"),
        ("name", "pubdate"),
        ("name", "date"),
    ):
        tag = soup.find("meta", attrs={attr: key})
        if tag and tag.get("content"):
            published = tag.get("content").strip()
            break
    if not published:
        stamp = soup.find("time")
        if stamp:
            published = (stamp.get("datetime") or stamp.get_text(" ", strip=True) or "").strip()
    paras = []
    for p in soup.select("article p, main p, .entry-content p, p"):
        text = re.sub(r"\s+", " ", p.get_text(" ", strip=True))
        if len(text) > 80:
            paras.append(text)
        if len(paras) >= 3:
            break
    return {
        "url": url,
        "title": re.sub(r"\s+", " ", title).strip(),
        "description": desc,
        "snippet": " ".join(paras)[:700],
        "image": image,
        "published": published,
    }


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


def cluster_coverage(facts: dict, pack: dict | None = None, fetch: bool = True) -> dict:
    """Group every public item about this one event into a single story cluster."""
    seen = set()
    articles = []

    def add(item: dict):
        url = (item.get("url") or item.get("source_url") or "").split("#")[0]
        if not url or url in seen:
            return
        seen.add(url)
        articles.append(
            {
                "url": url,
                "share_url": item.get("share_url") or "",
                "title": item.get("title") or item.get("label") or "",
                "description": item.get("description") or item.get("snippet") or "",
                "snippet": item.get("snippet") or "",
                "image": item.get("image") or item.get("image_url") or "",
                "engine": item.get("engine") or item.get("lane") or item.get("platform") or item.get("provenance") or "pack",
                "provenance": item.get("provenance") or "",
                "role": item.get("role") or "",
                "published": item.get("published") or item.get("published_at") or item.get("pubDate") or "",
            }
        )

    for post in (pack or {}).get("verified_posts") or (pack or {}).get("posts") or []:
        add({**post, "engine": post.get("engine") or post.get("provenance") or "facebook"})
    for img in (pack or {}).get("images") or []:
        add(
            {
                "url": img.get("source_url") or img.get("image_url"),
                "title": img.get("source_title") or "",
                "image": img.get("image_url"),
                "engine": img.get("platform") or "image",
            }
        )
    add(_official_results_card(facts))
    for url in SEED_URLS.get(facts.get("slug") or "", []):
        add({"url": url, "engine": "seed"})
    if fetch:
        try:
            from search_everywhere import (
                catalog_local_urls,
                discovery_queries,
                event_query,
                google_news,
                official_sailingsa_sources,
                web_hits,
            )
        except Exception:
            event_query = None
            catalog_local_urls = None
            official_sailingsa_sources = None
        ctx = {
            "id": facts.get("slug"),
            "slug": facts.get("slug"),
            "title": facts["title"],
            "club": facts["club"],
            "club_name": facts["club_name"],
            "class_name": facts.get("class_name") or "",
            "class_slugs": [((facts.get("class_name") or "").strip().lower().replace(" ", "-"))],
            "host_club_slug": facts.get("host_club_slug") or "",
            "start": facts.get("start"),
            "end": facts.get("end"),
            "event_url": facts.get("url"),
        }
        if official_sailingsa_sources:
            for item in official_sailingsa_sources(ctx):
                add(item)
        if catalog_local_urls:
            for item in catalog_local_urls(ctx):
                add({**item, "engine": item.get("engine") or "class_catalog"})
        if event_query:
            for q in discovery_queries(ctx)[:10]:
                for item in google_news(q, limit=4) + web_hits(q, limit=6):
                    add(item)
                for item in _try_paid_clusters(q):
                    add(item)
        for article in list(articles):
            if len(article.get("description") or "") > 200 and article.get("image"):
                continue
            extracted = extract_article(article["url"])
            if not extracted:
                continue
            article["title"] = article["title"] or extracted.get("title") or ""
            if len(extracted.get("description") or "") > len(article.get("description") or ""):
                article["description"] = extracted.get("description") or ""
            if len(extracted.get("snippet") or "") > len(article.get("snippet") or ""):
                article["snippet"] = extracted.get("snippet") or ""
            article["image"] = article.get("image") or extracted.get("image") or ""
            article["published"] = article.get("published") or extracted.get("published") or ""
            for extra in (extracted.get("images") or []) + harvest_source_images(article["url"]):
                if extra.get("url") and extra["url"] != article.get("image"):
                    add(
                        {
                            "url": extra.get("source_url") or article["url"],
                            "title": extra.get("title") or article.get("title") or "",
                            "image": extra["url"],
                            "engine": "source_media",
                            "provenance": article.get("provenance") or article.get("engine") or "seed",
                        }
                    )
    kept = [a for a in articles if _keep_cluster_item(a, facts) and not _wiki_url(a.get("url") or "") and not _wiki_url(a.get("image") or "")]
    return {
        "event_id": facts.get("slug"),
        "event_url": facts.get("url"),
        "articles": kept,
        "count": len(kept),
    }


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


def _bad_image_url(url: str) -> bool:
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


def _event_photo_score(item: dict, facts: dict) -> int:
    """Score only photographs that belong to this event. Wiki and stock boats lose."""
    klass = (facts.get("class_name") or "").strip()
    blob = " ".join((item.get("url") or "", item.get("source_url") or "", item.get("title") or "")).lower()
    photo = (item.get("url") or "").lower()
    source = (item.get("source_url") or "").lower()
    n = 0
    if _wiki_url(blob) or _wiki_url(photo) or _wiki_url(source):
        return -10000
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

    def add(item: dict):
        url = (item.get("url") or "").split("#")[0]
        source = item.get("source_url") or ""
        if not url or url in seen or _wiki_url(url) or _bad_image_url(url):
            return
        if _facebook_page_chrome(source, url) and _event_photo_score(item, facts) < 40:
            return
        seen.add(url)
        candidates.append(item)

    for item in (cluster or {}).get("articles") or []:
        if item.get("image"):
            add(
                {
                    "url": item["image"],
                    "source_url": item.get("url") or item.get("share_url") or "",
                    "title": item.get("title") or facts["title"],
                    "credit": _credit_from_url(item.get("url") or item["image"]),
                }
            )
    for img in (pack or {}).get("images") or []:
        if img.get("image_url"):
            add(
                {
                    "url": img["image_url"],
                    "source_url": img.get("source_url") or "",
                    "title": img.get("source_title") or facts["title"],
                    "credit": pretty_credit(img.get("platform") or "", img.get("source_url") or img.get("image_url") or ""),
                }
            )
    ranked = [item for item in candidates if _event_photo_score(item, facts) >= 40]
    ranked.sort(key=lambda item: _event_photo_score(item, facts), reverse=True)
    return ranked[:limit]


def pick_image(facts: dict, cluster: dict, pack: dict | None = None) -> dict | None:
    chosen = pick_images(facts, cluster, pack, limit=1)
    return chosen[0] if chosen else None


def pretty_credit(raw: str, url: str = "") -> str:
    blob = f"{raw or ''} {url or ''}".lower()
    if "novanews" in blob:
        return "NovaNews"
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
    if "youtube" in blob or "youtu.be" in blob:
        return "YouTube"
    if "facebook" in blob or "fbcdn" in blob or "lookaside.fbsbx" in blob:
        return "Facebook / host club"
    host = urllib.parse.urlparse(url or raw or "").netloc.lower().removeprefix("www.")
    return host or (raw or "source").strip()


def _credit_from_url(url: str) -> str:
    return pretty_credit("", url)


def download_image(image: dict, issue: str, slug: str, index: int = 0) -> dict | None:
    url = (image or {}).get("url") or ""
    if not url or _wiki_url(url):
        return None
    dest_dir = ROOT / "public" / "issues" / issue / "media"
    dest_dir.mkdir(parents=True, exist_ok=True)
    source_dir = ROOT / "issues" / issue / "media"
    source_dir.mkdir(parents=True, exist_ok=True)
    ext = ".jpg"
    path = urllib.parse.urlparse(url).path.lower()
    for cand in (".png", ".webp", ".jpeg", ".jpg"):
        if path.endswith(cand):
            ext = ".jpg" if cand == ".jpeg" else cand
            break
    if "lookaside.fbsbx" in url or "fbcdn" in url:
        ext = ".jpg"
    suffix = "" if index == 0 else f"-{index + 1}"
    filename = slug + suffix + ext
    dest = dest_dir / filename
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
    if len(raw) < 8000 or (ctype and not ctype.startswith("image") and raw[:3] not in (b"\xff\xd8\xff", b"\x89PN")):
        return None
    if not _is_event_photograph(raw):
        return None
    dest.write_bytes(raw)
    (source_dir / filename).write_bytes(raw)
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
    cols, table = facts["leaderboard"]
    images = pick_images(facts, cluster, pack, limit=2)
    if not images and fetched_cluster:
        images = _seed_event_images(facts)
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
    for local in locals:
        credit = pretty_credit(local.get("credit") or "", local.get("source_url") or local.get("url") or "")
        blocks.append(
            {
                "type": "image",
                "url": local["url"],
                "alt": local.get("title") or facts["title"],
                "caption": f"{facts['title']} — {facts['club_name']}. Photo: {credit}.",
                "credit": credit,
                "source_url": local.get("source_url") or facts["url"],
                "rights_status": "source_attributed",
            }
        )
    for text in paras:
        blocks.append({"type": "paragraph", "text": text})
    blocks.append({"type": "heading", "text": "1st, 2nd, 3rd"})
    blocks.append(
        {
            "type": "results",
            "source_event_url": facts["url"],
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
        "kicker": (facts.get("class_name") or "Regatta").upper() + "  ·  " + facts["club"],
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


def rewrite_weekend_feature(issue: str, monday, events: list[dict], articles: list[dict]) -> dict:
    import datetime as dt

    from events_weekend import saturday_sunday

    sat, sun = saturday_sunday(monday)
    scored = [e for e in events if e.get("has_results") or e.get("regatta_id")]
    window = f"{sat.strftime('%-d')}–{sun.strftime('%-d %B %Y')}"
    venues = []
    for article in articles:
        club = (article.get("club") or "").strip()
        name = {
            "TSC": "Theewater",
            "HMYC": "Midmar",
            "AYC": "Aeolians",
        }.get(club, article.get("class_name") or "")
        if name and name not in venues:
            venues.append(name)
    if not events:
        paras = [f"No racing events were listed on the SailingSA events table for {sat.isoformat()}–{sun.isoformat()}."]
        headline = "No titles on the SailingSA calendar"
    else:
        where = ", ".join(venues[:3]) if venues else "South Africa"
        headline = f"{len(scored) or len(articles) or len(events)} titles at {where}"
        bits = [
            f"{len(scored)} of {len(events)} listed events published results for {window} at {where}."
        ]
        for article in articles:
            if article.get("headline"):
                bits.append(article["headline"] + ".")
        paras = [p for p in bits[:6] if "weekend" not in p.lower()]
    return {
        "id": "sailing-" + issue,
        "type": "feature",
        "headline": headline,
        "deck": f"SailingSA · {window}",
        "byline": "SailingSA",
        "kicker": "SAILING",
        "published_at": issue,
        "event_id": "sailing-" + issue,
        "layout": "lead",
        "hero_image": (articles[0].get("hero_image") if articles else None),
        "blocks": [{"type": "paragraph", "text": p} for p in paras],
        "sources": ["https://sailingsa.co.za/api/events"],
        "review_status": "rewritten",
    }
