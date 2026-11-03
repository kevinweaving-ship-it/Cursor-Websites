"""R1 fact sheets, R2 conflict hold, R3 freshness, R7 class tags."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import date, datetime

from sailingsa.roundup.models import clean_spaces, format_nett, person_tokens
from sailingsa.roundup.week import parse_iso_date
from sailingsa.roundup.verbs import status_verb

SERIES_DATE_RE = re.compile(
    r"\s*[—–-]\s*Series overall\s*\(\d{1,2}\s+[A-Za-z]{3}[–-]\d{1,2}\s+[A-Za-z]{3}\)",
    re.I,
)
SERIES_OVERALL_RE = re.compile(r"\s*[—–-]\s*Series overall\b.*", re.I)
VENUE_CODE_RE = re.compile(r"\s+-\s+[A-Z]{2,5}$")
SCORE_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)")

PY_FLEET_NAMES = {"open", "py", "handicap", "mixed", "pursuit"}
HANDICAP_FLEETS = {"dinghy", "multihull", "keelboat", "yacht"}


def sanitize_label(value: str | None) -> str:
    text = clean_spaces(value or "")
    text = SERIES_DATE_RE.sub("", text)
    text = SERIES_OVERALL_RE.sub("", text)
    text = VENUE_CODE_RE.sub("", text)
    text = text.replace("Non Spinnaker", "Non-Spinnaker")
    return clean_spaces(text)


def display_event_name(event: dict) -> str:
    name = sanitize_label(event.get("event_name") or event.get("regatta_event_name") or "")
    name = re.sub(r"^2026\s+", "", name)
    name = name.replace("DF 95", "DF95")
    return clean_spaces(name)


def parse_score(raw) -> dict:
    text = clean_spaces(str(raw) if raw is not None else "")
    discarded = text.startswith("(") and text.endswith(")")
    inner = text.strip("()")
    codes = re.findall(r"[A-Z]{2,}", inner)
    match = SCORE_RE.search(inner)
    number = float(match.group(1)) if match else None
    return {
        "raw": raw,
        "points": number,
        "discarded": discarded,
        "codes": codes,
        "win": number == 1.0 and not codes,
    }


def race_analysis(scores: dict | None) -> dict:
    parsed = {}
    wins = []
    dns_like = []
    for key, raw in (scores or {}).items():
        item = parse_score(raw)
        parsed[key] = item
        if item["win"]:
            wins.append(key)
        if any(code in {"DNS", "DNC", "DNF", "RET"} for code in item["codes"]):
            dns_like.append(key)
    return {"races": parsed, "wins": wins, "dns_like": dns_like, "win_count": len(wins)}


def _scoring_fleet(row: dict) -> str:
    for key in ("class_canonical", "class_original", "fleet_label"):
        value = sanitize_label(row.get(key))
        if value:
            return value
    return sanitize_label(row.get("class_name")) or "Fleet"


def _boat_class(row: dict) -> str:
    return sanitize_label(row.get("class_name") or row.get("result_class_original") or "")


def _raced(row: dict) -> bool:
    raced = row.get("raced")
    if raced is False:
        return False
    return True


def _club(row: dict) -> str | None:
    return clean_spaces(row.get("club_abbrev") or row.get("club_fullname") or "") or None


def _place(row: dict) -> dict:
    analysis = race_analysis(row.get("race_scores") if isinstance(row.get("race_scores"), dict) else {})
    return {
        "rank": row.get("rank"),
        "helm": clean_spaces(row.get("helm_name") or ""),
        "crew": clean_spaces(row.get("crew_name") or "") or None,
        "boat": clean_spaces(row.get("boat_name") or "") or None,
        "sail_number": clean_spaces(str(row.get("sail_number") or "")) or None,
        "club": _club(row),
        "nation": clean_spaces(row.get("nationality") or "") or None,
        "nett": row.get("nett_points_raw"),
        "nett_display": format_nett(row.get("nett_points_raw")),
        "race_wins": analysis["wins"],
        "win_count": analysis["win_count"],
        "dns_like": analysis["dns_like"],
        "boat_class": _boat_class(row) or None,
    }


def _is_py_fleet(name: str, boat_classes: set[str]) -> bool:
    key = name.lower()
    if key in PY_FLEET_NAMES or "handicap" in key or key == "open":
        return True
    if key in HANDICAP_FLEETS:
        return True
    return len({c for c in boat_classes if c}) > 1


def _fleet_tags(name: str, boat_classes: set[str], py: bool) -> list[str]:
    if py and name.lower() in PY_FLEET_NAMES | {"open"}:
        return ["PY (handicap)"]
    if py and name.lower() in HANDICAP_FLEETS:
        return [name]
    if len(boat_classes) == 1:
        only = next(iter(boat_classes))
        return [only] if only else [name]
    return [name] if name else []


def _angles_for_fleet(places: list[dict], races_sailed: int) -> list[str]:
    angles: list[str] = []
    if not places:
        return angles
    winner = places[0]
    if len(places) > 1 and winner.get("nett") is not None and places[1].get("nett") is not None:
        try:
            margin = float(places[1]["nett"]) - float(winner["nett"])
            if margin == 0:
                angles.append("tie")
            elif margin <= 2:
                angles.append("close_finish")
        except (TypeError, ValueError):
            pass
    if winner.get("win_count") and races_sailed and winner["win_count"] == races_sailed:
        angles.append("sweep")
    others = [p for p in places[1:] if p.get("win_count", 0) > winner.get("win_count", 0)]
    if others:
        angles.append("consistency_over_race_wins")
    wins = winner.get("race_wins") or []
    if len(wins) >= 3:
        angles.append("race_win_streak")
    if winner.get("dns_like") and any(not p.get("dns_like") for p in places[1:3]):
        angles.append("split_weekend")
    if any(p.get("dns_like") for p in places[1:3]) and not winner.get("dns_like"):
        angles.append("split_weekend")
    for place in places:
        place_wins = set(place.get("race_wins") or [])
        late_dns = [
            r for r in (place.get("dns_like") or [])
            if r.startswith("R") and r[1:].isdigit() and int(r[1:]) >= 5
        ]
        if place_wins >= {"R1", "R2", "R3"} and late_dns:
            angles.append("saturday_streak_sunday_dns")
    return angles


def _detect_tier(name: str, category: str | None) -> tuple[str, int]:
    blob = f"{name} {category or ''}".lower()
    if any(word in blob for word in ("world", "global championship", "globals")):
        return "worlds", 40
    if "national" in blob:
        return "nationals", 30
    if any(word in blob for word in ("provincial", "regional", "regionals")):
        return "provincial", 20
    return "club", 5


def _series_final(event: dict, rows: list[dict], extra_sources: list[dict], event_id: str = "") -> bool:
    name = str(event.get("event_name") or "")
    if re.search(r"day\s*2\s+of\s*2", name, re.I):
        return True
    if re.search(r"day\s*2\b", name, re.I) and "series" in name.lower():
        return True
    labels = " ".join(
        str(row.get("fleet_label") or "") for row in rows
    )
    if "series overall" in labels.lower():
        return True
    for src in extra_sources:
        if event_id and src.get("event_id") and src.get("event_id") != event_id:
            continue
        facts = src.get("facts") or {}
        if facts.get("host_lists_overall") and (not event_id or src.get("event_id") == event_id):
            return True
    return False


def _collect_conflicts(event_id: str, sources: list[dict]) -> list[dict]:
    held: list[dict] = []
    for src in sources:
        if src.get("event_id") != event_id:
            continue
        for item in src.get("field_conflicts") or []:
            values = {entry.get("value") for entry in item.get("values") or []}
            if len(values) > 1:
                held.append(
                    {
                        "field": item["field"],
                        "values": item["values"],
                        "action": "hold",
                    }
                )
    return held


def _club_name(event: dict, rows: list[dict], summary: dict) -> tuple[str | None, str | None]:
    code = (
        summary.get("host_club_code")
        or (rows[0].get("host_club_code") if rows else None)
        or event.get("host_club_code")
    )
    name = (
        summary.get("host_club_name")
        or (rows[0].get("host_club_name") if rows else None)
    )
    return (clean_spaces(name) if name else None, clean_spaces(code) if code else None)


def _page_status(page: dict) -> str | None:
    title = str(page.get("title") or "")
    if re.search(r"final", title, re.I):
        return "final"
    if re.search(r"provisional", title, re.I):
        return "provisional"
    return None


def build_factsheet(item: dict, edition_date: date, extra_sources: list[dict] | None = None) -> dict:
    extra_sources = extra_sources or []
    event = item["event"]
    rows = [row for row in (item.get("results") or []) if row.get("helm_name") or row.get("rank")]
    raced_rows = [row for row in rows if _raced(row)]
    summary = item.get("summary") or {}
    page = item.get("page") or {}
    event_id = item["event_id"]
    name = display_event_name(event)
    start = parse_iso_date(event.get("start_date") or summary.get("start_date"))
    end = parse_iso_date(event.get("end_date") or summary.get("end_date"))
    club_name, club_code = _club_name(event, rows, summary)
    conflicts = _collect_conflicts(event_id, extra_sources)

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for row in raced_rows:
        key = (row.get("block_id"), _scoring_fleet(row))
        groups[key].append(row)

    fleets: list[dict] = []
    class_tags: list[str] = []
    all_angles: list[str] = []
    tokens: set[str] = set(person_tokens(name, club_name, club_code))

    for (_block, fleet_name), group in groups.items():
        group = sorted(group, key=lambda row: (row.get("rank") is None, row.get("rank") or 999))
        boat_classes = {_boat_class(row) for row in group if _boat_class(row)}
        py = _is_py_fleet(fleet_name, boat_classes)
        tags = _fleet_tags(fleet_name, boat_classes, py)
        for tag in tags:
            if tag not in class_tags:
                class_tags.append(tag)
        places = [_place(row) for row in group[:3]]
        races_sailed = int(group[0].get("races_sailed") or 0)
        discards = int(group[0].get("discard_count") or 0)
        angles = _angles_for_fleet(places, races_sailed)
        all_angles.extend(angles)
        margin = None
        if len(places) > 1 and places[0].get("nett") is not None and places[1].get("nett") is not None:
            try:
                margin = float(places[1]["nett"]) - float(places[0]["nett"])
            except (TypeError, ValueError):
                margin = None
        fleet = {
            "name": fleet_name,
            "py": py,
            "class_tags": tags,
            "entries": len(group),
            "races_sailed": races_sailed,
            "discards": discards,
            "top3": places,
            "margin": margin,
            "angles": angles,
        }
        fleets.append(fleet)
        tokens.add(fleet_name)
        tokens.update(tags)
        tokens.add(str(len(group)))
        if races_sailed:
            tokens.add(str(races_sailed))
        for place in places:
            tokens.update(person_tokens(place.get("helm"), place.get("crew"), place.get("boat"), place.get("sail_number"), place.get("club")))
            if place.get("nett_display"):
                tokens.add(place["nett_display"])
            tokens.update(place.get("race_wins") or [])

    # External-only facts (DF95): attach after event-URL-first gap.
    attached = [src for src in extra_sources if src.get("event_id") == event_id and src.get("facts")]
    if not fleets:
        for src in attached:
            facts = src["facts"]
            if facts.get("winner_helm"):
                places = []
                for rank, key in ((1, "winner"), (2, "second"), (3, "third")):
                    helm = facts.get(f"{key}_helm")
                    if not helm:
                        continue
                    place = {
                        "rank": rank,
                        "helm": helm,
                        "crew": None,
                        "boat": None,
                        "sail_number": None,
                        "club": None,
                        "nation": facts.get(f"{key}_nation"),
                        "nett": facts.get(f"{key}_nett"),
                        "nett_display": format_nett(facts.get(f"{key}_nett")),
                        "race_wins": [],
                        "win_count": facts.get("qualifier_wins") if rank == 1 else 0,
                        "dns_like": [],
                        "boat_class": "DF95" if "df95" in event_id else None,
                    }
                    places.append(place)
                    tokens.update(person_tokens(helm, facts.get(f"{key}_nation")))
                    if place["nett_display"]:
                        tokens.add(place["nett_display"])
                fleet = {
                    "name": "DF95",
                    "py": False,
                    "class_tags": ["DF95"],
                    "entries": None,
                    "races_sailed": None,
                    "discards": 0,
                    "top3": places,
                    "margin": None,
                    "angles": ["defending_champion"] if facts.get("defending_champion_retained") else [],
                    "from_external": True,
                    "external_source": src.get("url"),
                }
                if places and places[0].get("nett") is not None and len(places) > 1 and places[1].get("nett") is not None:
                    fleet["margin"] = float(places[1]["nett"]) - float(places[0]["nett"])
                fleets.append(fleet)
                class_tags = ["DF95"]
                all_angles.extend(fleet["angles"])
                if facts.get("qualifier_wins"):
                    tokens.add(str(facts["qualifier_wins"]))
                if facts.get("qualifier_races_mentioned"):
                    tokens.add(str(facts["qualifier_races_mentioned"]))
                if facts.get("gold_final_wins"):
                    tokens.add(str(facts["gold_final_wins"]))
                break

    db_status = clean_spaces(
        summary.get("result_status")
        or (rows[0].get("result_status") if rows else "")
        or _page_status(page)
        or ""
    ).lower()
    as_at = summary.get("as_at_time") or (rows[0].get("as_at_time") if rows else None)
    flags: list[str] = []
    status = "unknown"
    if not raced_rows and not fleets:
        status = "awaiting"
    elif conflicts and not fleets:
        status = "under_review"
        flags.append("conflict_hold")
    elif _series_final(event, rows, extra_sources, event_id):
        status = "series_final"
        flags.append("series_final_from_host_or_label")
    elif db_status.startswith("final"):
        status = "final"
    elif db_status.startswith("provisional"):
        status = "provisional"
    elif fleets and any(f.get("from_external") for f in fleets):
        status = "final"
    if end and as_at:
        try:
            updated = datetime.fromisoformat(str(as_at).replace("Z", "+00:00")).date()
            if updated < end and status in {"provisional", "final", "unknown"}:
                status = "partial"
                flags.append("freshness_last_updated_before_end")
        except ValueError:
            pass

    official = next((src for src in attached if src.get("facts", {}).get("competitors_entered")), None)
    if official and official["facts"].get("start_date"):
        start = parse_iso_date(official["facts"]["start_date"]) or start
        tokens.add("16")
    if official and official["facts"].get("end_date"):
        end = parse_iso_date(official["facts"]["end_date"]) or end
    if official:
        facts = official["facts"]
        if facts.get("competitors_entered") and not any(c["field"] == "entries" and not official for c in conflicts):
            entries_from_official = int(facts["competitors_entered"])
        else:
            entries_from_official = facts.get("competitors_entered")
        tokens.add(str(facts.get("competitors_entered")))
        tokens.add(str(facts.get("scored_results") or ""))
        tokens.add(str(facts.get("races_completed") or ""))
        for key in ("sa_best", "sa_silver"):
            person = facts.get(key) or {}
            if person.get("helm"):
                tokens.add(person["helm"])
                tokens.add(str(person.get("overall_rank") or ""))
                tokens.add(str(person.get("fleet_pos") or ""))
                tokens.add(person.get("fleet") or "")
        if conflicts:
            flags.append("count_conflict_noted")
            flags.append("reconciled_official_msr")
    else:
        entries_from_official = None
        if conflicts:
            flags.append("entries_and_races_held")

    sources = _sources_for(item, extra_sources, event_id)
    if attached and any(f.get("from_external") for f in fleets):
        flags.append("external_after_event_url_gap")

    entries_total = sum(f["entries"] or 0 for f in fleets) if any(f.get("entries") for f in fleets) else None
    if entries_from_official:
        entries_total = int(entries_from_official)
    elif any(c["field"] == "entries" for c in conflicts):
        entries_total = None
        flags.append("entries_held")
    races_held = any(c["field"] == "races_sailed" for c in conflicts) and not official

    venue = None
    if "theewater" in name.lower() or "df95" in event_id:
        venue = "Theewater Sports Club"
        tokens.add(venue)
        tokens.add("Theewater")
    elif club_name:
        venue = club_name

    tokens.update(person_tokens(status, club_code, venue))
    if entries_total:
        tokens.add(str(entries_total))

    sheet = {
        "event_id": event_id,
        "name": name,
        "start_date": start.isoformat() if start else None,
        "end_date": end.isoformat() if end else None,
        "venue": venue,
        "club": club_name,
        "club_code": club_code,
        "event_url": item.get("event_url"),
        "category": event.get("category"),
        "tier": _detect_tier(name, event.get("category"))[0],
        "tier_points": _detect_tier(name, event.get("category"))[1],
        "fleets": fleets,
        "class_tags": class_tags,
        "status": {
            "status": status,
            "source": "event_url_first" if rows else ("external" if fleets else "none"),
            "timestamp": str(as_at) if as_at else None,
            "verb": status_verb(status),
            "flags": flags,
        },
        "sources": sources,
        "entries_total": entries_total,
        "races_held": races_held,
        "conflicts": conflicts,
        "angles": sorted(set(all_angles)),
        "late": bool(item.get("late")),
        "tokens": sorted(t for t in tokens if t),
        "page_images": (page.get("images") or []),
        "page_title": page.get("title"),
    }
    return sheet


def _sources_for(item: dict, extra_sources: list[dict], event_id: str) -> list[dict]:
    sources: list[dict] = []
    if item.get("event_url"):
        sources.append(
            {
                "url": item["event_url"],
                "label": "SailingSA results",
                "kind": "official_results",
            }
        )
    for src in extra_sources:
        if src.get("event_id") != event_id:
            continue
        url = src.get("url")
        if not url:
            continue
        kind = "gallery" if "gallery" in (url or "") else "article"
        if "get_results.php" in url or "/results/" in url:
            kind = "official_results"
        sources.append(
            {
                "url": url,
                "label": src.get("outlet") or src.get("title") or url,
                "kind": kind,
                "facts": src.get("facts") or {},
            }
        )
    # stable unique
    seen = set()
    unique = []
    for src in sources:
        if src["url"] in seen:
            continue
        seen.add(src["url"])
        unique.append(src)
    return unique


def log_entries_points(entries: int | None) -> float:
    if not entries:
        return 0.0
    return min(20.0, math.log(1 + entries) * 5.0)
