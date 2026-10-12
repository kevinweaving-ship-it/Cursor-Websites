"""TSL championship schedule — 28-match RR and 16-match flights + sail-offs.

Pure functions. Does not invent teams or results. Used by tsl_team_racing.
"""
from __future__ import annotations

from typing import Iterable, Optional

FORMAT_RR28 = "rr28"
FORMAT_FLIGHTS16 = "flights16"
SAILOFF_SLOTS = (
    (1, "1st vs 1st — Regional Champion / 2nd"),
    (2, "2nd vs 2nd — 3rd / 4th"),
    (3, "3rd vs 3rd — 5th / 6th"),
    (4, "4th vs 4th — 7th / 8th"),
)


def _ids(team_ids: Iterable) -> list[int]:
    return [int(t) for t in team_ids]


def all_unique_pairings(team_ids: Iterable) -> list[frozenset]:
    ids = _ids(team_ids)
    return [frozenset((ids[i], ids[j])) for i in range(len(ids)) for j in range(i + 1, len(ids))]


def _other(pair: frozenset, team_id: int) -> int:
    a, b = tuple(pair)
    return b if a == team_id else a


def color_counts(matches: list[dict], team_ids: Iterable) -> dict[int, dict]:
    out = {int(t): {"blue": 0, "green": 0} for t in team_ids}
    for m in matches:
        b = m.get("blue_team_id") or m.get("team_a_id")
        g = m.get("green_team_id") or m.get("team_b_id")
        if b in out:
            out[b]["blue"] += 1
        if g in out:
            out[g]["green"] += 1
    return out


def changeover_stays(matches: list[dict]) -> int:
    """How many consecutive match pairs share a team (stay-on-boats)."""
    stays = 0
    prev = None
    for m in matches:
        cur = {m.get("blue_team_id") or m.get("team_a_id"), m.get("green_team_id") or m.get("team_b_id")}
        cur.discard(None)
        if prev and (prev & cur):
            stays += 1
        prev = cur
    return stays


def _balance_colors(matches: list[dict], team_ids: list[int]) -> list[dict]:
    """Flip Blue/Green on later matches so each team is 4/3 or 3/4 when possible."""
    ids = list(team_ids)
    target = None
    if matches and len(ids) >= 2:
        played = {}
        for m in matches:
            for t in (m.get("blue_team_id"), m.get("green_team_id")):
                if t:
                    played[t] = played.get(t, 0) + 1
        # 7 games → 4/3; 3 games → 2/1
        target = max(played.values()) if played else 0

    def score():
        c = color_counts(matches, ids)
        bad = 0
        for t in ids:
            d = abs(c[t]["blue"] - c[t]["green"])
            if target and target % 2 == 1:
                if d != 1:
                    bad += abs(d - 1)
            elif d > 1:
                bad += d - 1
        return bad

    # Greedy flips that reduce imbalance without creating a 5–2.
    improved = True
    while improved:
        improved = False
        base = score()
        if base == 0:
            break
        for i, m in enumerate(matches):
            b, g = m.get("blue_team_id"), m.get("green_team_id")
            if not b or not g:
                continue
            m["blue_team_id"], m["green_team_id"] = g, b
            if score() < base:
                improved = True
                break
            m["blue_team_id"], m["green_team_id"] = b, g
    return matches


def generate_rr_matches(team_ids: Iterable, *, phase: str = "rr", flight: str = "") -> list[dict]:
    """All unique pairings, stay-on-boats first, then fair Blue/Green."""
    ids = _ids(team_ids)
    remaining = set(all_unique_pairings(ids))
    blue_n = {t: 0 for t in ids}
    green_n = {t: 0 for t in ids}
    last_blue = last_green = None
    out: list[dict] = []

    while remaining:
        chosen = None
        blue = green = None
        if last_blue is not None:
            cands = [p for p in remaining if last_blue in p]
            if cands:
                chosen = min(
                    cands,
                    key=lambda p: (
                        green_n[_other(p, last_blue)],
                        blue_n[last_blue] - green_n[last_blue],
                        _other(p, last_blue),
                    ),
                )
                blue, green = last_blue, _other(chosen, last_blue)
        if chosen is None and last_green is not None:
            cands = [p for p in remaining if last_green in p]
            if cands:
                chosen = min(
                    cands,
                    key=lambda p: (
                        blue_n[_other(p, last_green)],
                        green_n[last_green] - blue_n[last_green],
                        _other(p, last_green),
                    ),
                )
                green, blue = last_green, _other(chosen, last_green)
        if chosen is None:
            chosen = min(
                remaining,
                key=lambda p: (
                    sum(blue_n[t] + green_n[t] for t in p),
                    min(p),
                    max(p),
                ),
            )
            a, b = tuple(chosen)
            if blue_n[a] <= blue_n[b]:
                blue, green = a, b
            else:
                blue, green = b, a
        remaining.remove(chosen)
        blue_n[blue] += 1
        green_n[green] += 1
        out.append(
            {
                "blue_team_id": blue,
                "green_team_id": green,
                "phase": phase,
                "flight": flight,
                "round_label": flight.upper() if flight else "RR",
                "sailoff_slot": None,
            }
        )
        last_blue, last_green = blue, green

    out = _balance_colors(out, ids)
    for i, m in enumerate(out, start=1):
        m["match_no"] = i
        m["label"] = f"M{i}"
    return out


def generate_flights16(flight_a: Iterable, flight_b: Iterable) -> list[dict]:
    a = _ids(flight_a)
    b = _ids(flight_b)
    if len(a) != 4 or len(b) != 4:
        raise ValueError("Each flight needs exactly four teams")
    if set(a) & set(b):
        raise ValueError("A team cannot be in both flights")
    fa = generate_rr_matches(a, phase="flight_a", flight="A")
    fb = generate_rr_matches(b, phase="flight_b", flight="B")
    for m in fb:
        m["match_no"] = m["match_no"] + 6
        m["label"] = f"M{m['match_no']}"
    sailoffs = []
    for i, (slot, note) in enumerate(SAILOFF_SLOTS, start=13):
        sailoffs.append(
            {
                "match_no": i,
                "label": f"M{i}",
                "blue_team_id": None,
                "green_team_id": None,
                "phase": "sailoff",
                "flight": "",
                "round_label": f"SO{slot}",
                "sailoff_slot": slot,
                "note": note,
            }
        )
    return fa + fb + sailoffs


def validate_schedule(matches: list[dict], team_ids: Iterable, fmt: str) -> list[str]:
    warnings = []
    ids = _ids(team_ids)
    pairs = []
    for m in matches:
        if m.get("phase") == "sailoff":
            continue
        b, g = m.get("blue_team_id"), m.get("green_team_id")
        if b and g:
            if b == g:
                warnings.append(f"{m.get('label')}: same team on Blue and Green")
            pairs.append(frozenset((int(b), int(g))))
    if fmt == FORMAT_RR28:
        want = set(all_unique_pairings(ids))
        have = set(pairs)
        missing = want - have
        extra = have - want
        if missing:
            warnings.append(f"Missing {len(missing)} unique pairing(s)")
        if extra:
            warnings.append(f"{len(extra)} pairing(s) are not in the championship set")
        if len(pairs) != len(set(pairs)):
            warnings.append("Duplicate pairing in the schedule")
        if len(ids) == 8 and len(pairs) != 28:
            warnings.append(f"Full RR needs 28 matches, have {len(pairs)}")
    elif fmt == FORMAT_FLIGHTS16:
        phases = [m.get("phase") for m in matches]
        if phases.count("flight_a") != 6:
            warnings.append("Flight A must have six matches")
        if phases.count("flight_b") != 6:
            warnings.append("Flight B must have six matches")
        if phases.count("sailoff") != 4:
            warnings.append("Need four sail-off matches M13–M16")
        for m in matches:
            if m.get("phase") == "sailoff" and m.get("sailoff_slot") and not (m.get("blue_team_id") and m.get("green_team_id")):
                warnings.append(f"{m.get('label')}: sail-off participant not yet determined")
    counts = color_counts(matches, ids)
    for t, c in counts.items():
        played = c["blue"] + c["green"]
        if played and abs(c["blue"] - c["green"]) > 1:
            warnings.append(f"Team {t} Blue/Green imbalance {c['blue']}/{c['green']}")
    return warnings


def resolve_sailoff_teams(flight_standings_a: list[dict], flight_standings_b: list[dict]) -> dict[int, tuple]:
    """slot -> (a_team_id, b_team_id) from completed flight ranks. Empty if unresolved."""
    if len(flight_standings_a) < 4 or len(flight_standings_b) < 4:
        return {}
    out = {}
    for slot, _note in SAILOFF_SLOTS:
        ta = flight_standings_a[slot - 1].get("team_id")
        tb = flight_standings_b[slot - 1].get("team_id")
        if ta and tb:
            out[slot] = (int(ta), int(tb))
    return out


def championship_from_sailoffs(sailoffs: list[dict]) -> dict[int, int]:
    """team_id -> championship place 1–8 from M13–M16. Incomplete sail-offs omitted."""
    place = {}
    slot_places = {1: (1, 2), 2: (3, 4), 3: (5, 6), 4: (7, 8)}
    for m in sailoffs:
        if m.get("status") != "complete":
            continue
        slot = int(m.get("sailoff_slot") or 0)
        if slot not in slot_places:
            continue
        w, l = m.get("winner_team_id"), m.get("loser_team_id")
        if w and l:
            place[int(w)] = slot_places[slot][0]
            place[int(l)] = slot_places[slot][1]
    return place


def preview_format_switch(existing: list[dict], incoming: list[dict]) -> dict:
    """Keep completed matches; never silently drop official results."""
    keep = []
    blocked = []
    for m in existing:
        if str(m.get("status") or "") == "complete":
            keep.append(m)
            pair = frozenset(
                (
                    int(m.get("team_a_id") or m.get("blue_team_id") or 0),
                    int(m.get("team_b_id") or m.get("green_team_id") or 0),
                )
            )
            in_new = any(
                frozenset((int(n.get("blue_team_id") or 0), int(n.get("green_team_id") or 0))) == pair
                for n in incoming
                if n.get("blue_team_id") and n.get("green_team_id")
            )
            if not in_new:
                blocked.append(m.get("label") or f"M{m.get('match_no')}")
    open_n = len([m for m in existing if str(m.get("status") or "") != "complete"])
    return {
        "keep_completed": len(keep),
        "replace_open": open_n,
        "create": len(incoming),
        "blocked_completed_not_in_new_format": blocked,
        "needs_confirm": bool(keep or open_n),
    }
