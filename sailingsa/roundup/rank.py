"""R5 story score: Worlds/Nationals always card; no-results events never get a slot."""

from __future__ import annotations

from sailingsa.roundup.factsheet import log_entries_points


def story_score(sheet: dict) -> dict:
    status = sheet["status"]["status"]
    if status == "awaiting":
        return {"score": 0, "why": ["no_results_awaiting"], "slot": "awaiting"}

    score = float(sheet.get("tier_points") or 0)
    why = [f"tier:{sheet.get('tier')}={sheet.get('tier_points')}"]
    entries = sheet.get("entries_total")
    entry_pts = log_entries_points(entries)
    if entry_pts:
        score += entry_pts
        why.append(f"entries:{entries}={entry_pts:.1f}")

    if "close_finish" in sheet.get("angles", []) or "tie" in sheet.get("angles", []):
        score += 8
        why.append("closeness+8")
    if "sweep" in sheet.get("angles", []):
        score += 6
        why.append("sweep+6")
    if "defending_champion" in sheet.get("angles", []):
        score += 10
        why.append("defending_champion+10")
    if "consistency_over_race_wins" in sheet.get("angles", []):
        score += 6
        why.append("consistency+6")
    if "split_weekend" in sheet.get("angles", []) or "saturday_streak_sunday_dns" in sheet.get("angles", []):
        score += 6
        why.append("split_weekend+6")

    articles = [s for s in sheet.get("sources", []) if s.get("kind") in {"article", "gallery"}]
    if articles:
        score += min(12, 6 * len(articles))
        why.append(f"external+{min(12, 6 * len(articles))}")

    if sheet.get("page_images"):
        score += 2
        why.append("event_page_media+2")

    if status == "under_review":
        score += 0
        why.append("conflict_hold_no_bonus")

    tier = sheet.get("tier")
    always_card = tier in {"worlds", "nationals"}
    slot = "card" if always_card or score >= 12 else "brief"
    if always_card:
        why.append("hard_rule:nationals_or_worlds_always_card")
    return {"score": round(score, 2), "why": why, "slot": slot}


def rank_sheets(sheets: list[dict]) -> list[dict]:
    scored = []
    for sheet in sheets:
        extra = story_score(sheet)
        row = dict(sheet)
        row["story_score"] = extra["score"]
        row["story_why"] = extra["why"]
        row["slot"] = extra["slot"]
        scored.append(row)
    cards = [s for s in scored if s["slot"] == "card"]
    awaiting = [s for s in scored if s["slot"] == "awaiting"]
    briefs = [s for s in scored if s["slot"] == "brief"]
    cards.sort(key=lambda s: (-s["story_score"], s["name"]))
    # Top 3–5 cards; Worlds/Nationals already forced into cards.
    featured = cards[:5]
    overflow = cards[5:]
    featured.sort(key=lambda s: (-s["story_score"], s["name"]))
    return featured + briefs + overflow + awaiting
