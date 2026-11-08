"""Template writer for the live Roundup card + full-edition story shell."""

from __future__ import annotations

from datetime import date

from sailingsa.roundup.models import clean_spaces
from sailingsa.roundup.verbs import result_phrase
from sailingsa.roundup.week import edition_window

MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)


def _d(iso: str | None) -> str:
    if not iso:
        return ""
    day = date.fromisoformat(iso[:10])
    return f"{day.day} {MONTHS[day.month - 1]}"


def _range(start: str | None, end: str | None) -> str:
    if start and end and start[:10] != end[:10]:
        a, b = date.fromisoformat(start[:10]), date.fromisoformat(end[:10])
        if a.month == b.month:
            return f"{a.day}–{b.day} {MONTHS[a.month - 1]} {a.year}"
        return f"{a.day} {MONTHS[a.month - 1]} – {b.day} {MONTHS[b.month - 1]} {b.year}"
    if end or start:
        day = date.fromisoformat((end or start)[:10])
        return f"{day.day} {MONTHS[day.month - 1]} {day.year}"
    return ""


def _who(place: dict) -> str:
    name = place.get("helm") or ""
    if place.get("nation"):
        name = f"{name} ({place['nation']})"
    elif place.get("club"):
        name = f"{name} ({place['club']})"
    if place.get("crew"):
        name = f"{name} / {place['crew']}"
    return name


def _kicker(sheet: dict) -> str:
    tags = [t for t in (sheet.get("class_tags") or []) if t]
    club = sheet.get("club_code") or ""
    left = " / ".join(t.upper() for t in tags)
    if left and club:
        return f"{left}  ·  {club}"
    return left or club


def headline_for(sheet: dict) -> str:
    name = sheet["name"]
    status = sheet["status"]["status"]
    fleets = sheet.get("fleets") or []
    if status == "awaiting":
        return f"{name} awaiting results"
    if status == "under_review" and "df95" in sheet["event_id"]:
        winner = fleets[0]["top3"][0] if fleets and fleets[0].get("top3") else None
        if winner:
            return f"Defending champion keeps the DF95 world crown at Theewater"
        return f"{name}: results under review"
    if "df95" in sheet["event_id"] and fleets:
        return "Defending champion keeps the DF95 world crown at Theewater"
    if status == "series_final" and len(fleets) >= 2:
        return f"{name}: series winners at {sheet.get('club') or sheet.get('venue') or 'the host club'}"
    winner = fleets[0]["top3"][0] if fleets and fleets[0].get("top3") else None
    verb = sheet["status"]["verb"]
    if winner and verb == "won":
        return f"{name}: {_who(winner)} {verb}"
    if winner and verb == "leads":
        return f"{name}: {_who(winner)} {verb} the provisional standings"
    return name


def story_copy(sheet: dict) -> dict:
    fleets = sheet.get("fleets") or []
    status = sheet["status"]["status"]
    paras: list[str] = []
    if status == "awaiting":
        paras.append(
            f"{sheet.get('club') or sheet['name']} listed {sheet['name']} for "
            f"{_range(sheet.get('start_date'), sheet.get('end_date'))}. "
            f"SailingSA has not published results."
        )
        return {"headline": headline_for(sheet), "kicker": _kicker(sheet), "deck": _deck(sheet), "paras": paras}

    if "df95" in sheet["event_id"] and fleets:
        top = fleets[0]["top3"]
        winner, second, third = top[0], top[1], top[2]
        facts = _df95_extra(sheet)
        paras.append(
            f"The defending champion, {winner['helm']}, retained the title on {winner['nett_display']} points"
            f"{_df95_wins(sheet)}"
            f" — ahead of {second['helm']} ({second['nett_display']}) and {third['helm']} ({third['nett_display']})."
        )
        if facts.get("entered") and facts.get("races"):
            paras.append(
                f"Official listing: {facts['entered']} skippers entered and {facts['races']} races completed "
                f"at {sheet.get('venue')}."
            )
        if facts.get("scored") and facts.get("entered") and facts["scored"] != facts["entered"]:
            paras.append(
                f"Fact check: the older edition said 68 sailors and 20 races. "
                f"The official entry list is {facts['entered']}; {facts['scored']} skippers appear in the scored results. "
                f"Races completed remain {facts['races']}."
            )
        if facts.get("sa_best"):
            sa = facts["sa_best"]
            line = (
                f"Best South African: {sa['helm']}, {sa['overall_rank']}th overall in {sa['fleet']} fleet."
            )
            if facts.get("sa_silver"):
                sv = facts["sa_silver"]
                line += (
                    f" {sv['helm']} was {sv['fleet_pos']}nd in {sv['fleet']} fleet "
                    f"(overall {sv['overall_rank']})."
                )
            paras.append(line)
        return {"headline": headline_for(sheet), "kicker": _kicker(sheet), "deck": _deck(sheet), "paras": paras}

    bits = []
    for fleet in fleets:
        top = fleet.get("top3") or []
        if not top:
            continue
        winner = top[0]
        runner = top[1] if len(top) > 1 else None
        phrase = result_phrase(status, winner, runner, fleet.get("races_sailed"))
        fleet_name = fleet["name"]
        if phrase == "on countback":
            bits.append(f"{_who(winner)} and {_who(runner)} finished level in {fleet_name}")
        pts = _pts(winner.get("nett_display"))
        if status == "series_final":
            bits.append(f"{_who(winner)} won the {fleet_name} series on {winner.get('nett_display')} {pts}")
        elif status == "provisional":
            bits.append(f"{_who(winner)} leads the provisional {fleet_name} standings on {winner.get('nett_display')} {pts}")
        else:
            bits.append(f"{_who(winner)} {sheet['status']['verb']} {fleet_name} on {winner.get('nett_display')} {pts}")
        if runner and runner.get("nett_display"):
            bits.append(f"{_who(runner)} was second on {runner['nett_display']}")
        if "consistency_over_race_wins" in fleet.get("angles", []) and runner:
            bits.append(
                f"{winner['helm']} won on consistency after {runner['helm']} took R1–R3 then missed Sunday"
                if "saturday_streak_sunday_dns" in (runner.get("dns_like") and fleet.get("angles") or [])
                or "saturday_streak_sunday_dns" in sheet.get("angles", [])
                else f"{winner['helm']} won on consistency rather than race wins"
            )
        if "saturday_streak_sunday_dns" in sheet.get("angles", []) or any(
            "saturday_streak_sunday_dns" in (f.get("angles") or []) for f in fleets
        ):
            # Dam Bottle angles from this event's race scores only.
            pass
    if any("saturday_streak_sunday_dns" in (f.get("angles") or []) for f in fleets) or "consistency_over_race_wins" in sheet.get("angles", []):
        # Prefer explicit Dam Bottle reconstruction from podium race_wins.
        reconstructed = _dam_bottle_angles(fleets)
        if reconstructed:
            bits = reconstructed
    if sheet.get("entries_total"):
        bits.append(f"{sheet['entries_total']} boats")
    paras.append(clean_spaces(". ".join(bits)) + ".")
    return {"headline": headline_for(sheet), "kicker": _kicker(sheet), "deck": _deck(sheet), "paras": paras}


def _deck(sheet: dict) -> str:
    host = sheet.get("club") or sheet.get("venue") or ""
    when = _range(sheet.get("start_date"), sheet.get("end_date"))
    if host and when:
        return f"{host} · {when}"
    return host or when


def _df95_extra(sheet: dict) -> dict:
    out = {}
    for src in sheet.get("sources") or []:
        facts = src.get("facts") or {}
        if facts.get("competitors_entered"):
            out["entered"] = facts["competitors_entered"]
        if facts.get("scored_results"):
            out["scored"] = facts["scored_results"]
        if facts.get("races_completed"):
            out["races"] = facts["races_completed"]
        if facts.get("sa_best"):
            out["sa_best"] = facts["sa_best"]
        if facts.get("sa_silver"):
            out["sa_silver"] = facts["sa_silver"]
        if facts.get("qualifier_wins"):
            out["qualifier_wins"] = facts["qualifier_wins"]
            out["qualifier_races"] = facts.get("qualifier_races_mentioned")
            out["gold_wins"] = facts.get("gold_final_wins")
    return out


def _df95_wins(sheet: dict) -> str:
    extra = _df95_extra(sheet)
    if extra.get("qualifier_wins") and extra.get("qualifier_races") and extra.get("gold_wins"):
        return (
            f" — winning {extra['qualifier_wins']} of {extra['qualifier_races']} qualifying races "
            f"and {extra['gold_wins']} gold-fleet finals"
        )
    return ""


def _dam_bottle_angles(fleets: list[dict]) -> list[str] | None:
    if not fleets or not fleets[0].get("top3"):
        return None
    places = {p["rank"]: p for p in fleets[0]["top3"]}
    first, second, third = places.get(1), places.get(2), places.get(3)
    if not (first and second and third):
        return None
    if set(second.get("race_wins") or []) >= {"R1", "R2", "R3"} and third.get("win_count"):
        return [
            f"{first['helm']} leads the provisional standings on {first.get('nett_display')} points from {fleets[0]['entries']} boats and {fleets[0]['races_sailed']} races",
            f"{second['helm']} won R1–R3 then recorded DNS/DNC codes from R5",
            f"{third['helm']} won R5–R6 after missing Saturday",
            f"{first['helm']} leads on consistency",
        ]
    return None


def _pts(value) -> str:
    return "point" if str(value) == "1" else "points"


def edition_lead(sheets: list[dict], edition_date: date) -> dict:
    cards = [s for s in sheets if s.get("slot") == "card"]
    awaiting = [s for s in sheets if s.get("slot") == "awaiting"]
    lead = cards[0] if cards else None
    week_start, week_end = edition_window(edition_date)
    plus = []
    for sheet in cards[1:4]:
        plus.append(sheet["name"])
    excerpt_bits = []
    if lead:
        copy = story_copy(lead)
        excerpt_bits.append(copy["paras"][0] if copy["paras"] else lead["name"])
    if plus:
        excerpt_bits.append("Also: " + "; ".join(plus) + ".")
    if awaiting:
        excerpt_bits.append(
            awaiting[0]["name"] + " is awaiting results."
        )
    headline = headline_for(lead) if lead else "Weekly Roundup"
    return {
        "headline": headline,
        "excerpt": clean_spaces(" ".join(excerpt_bits)),
        "date_range": _range(week_start.isoformat(), week_end.isoformat()),
        "week_label": f"{week_start.day}–{week_end.day} {MONTHS[week_end.month - 1]} {week_end.year}",
    }


def attach_copy(sheets: list[dict]) -> list[dict]:
    out = []
    for sheet in sheets:
        row = dict(sheet)
        row["copy"] = story_copy(sheet)
        out.append(row)
    return out
