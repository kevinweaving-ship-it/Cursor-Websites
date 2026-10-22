#!/usr/bin/env python3
"""Parent overall results table for TSL Team Racing.

The /api/regatta payload is a team list (names, empty Rank/Wins/Total).
That is a roster, not a leaderboard. The parent overall table is
Rank / Club/Team / Wins / Total / F15…F1 from settings.flight_sheet
(goldBuilt() in mac-tsl-admin.js). Gate 1 hashes that table only.
"""
from __future__ import annotations

MAX_FLIGHTS = 28
FLIGHT_BOATS = 6


def fetch_tsl_state(slug: str, fetch_json=None) -> dict | None:
    slug = (slug or "").strip()
    if not slug:
        return None
    if fetch_json is None:
        from publish_weekend import fetch_json as _fetch_json

        fetch_json = _fetch_json
    try:
        data = fetch_json("https://sailingsa.co.za/api/tsl/" + slug + "/state")
    except Exception:
        return None
    if not isinstance(data, dict) or not data.get("teams"):
        return None
    return data


def _sheet(state: dict) -> dict:
    settings = state.get("settings") or {}
    return settings.get("flight_sheet") or {}


def _teams(state: dict) -> list[dict]:
    return [t for t in (state.get("teams") or []) if isinstance(t, dict) and t.get("team_id") not in (None, "")]


def _cell(sheet: dict, fl: int, bow: int) -> dict:
    flight = sheet.get(str(fl)) or sheet.get(fl) or {}
    if not isinstance(flight, dict):
        return {}
    cell = flight.get(str(bow)) or flight.get(bow) or {}
    return cell if isinstance(cell, dict) else {}


def _parse_rank(raw):
    if raw in (None, ""):
        return None
    try:
        n = int(float(raw))
    except (TypeError, ValueError):
        return None
    if 1 <= n <= FLIGHT_BOATS:
        return n
    return None


def _flight_done(sheet: dict, fl: int) -> bool:
    need = 0
    have = 0
    for bow in range(1, 7):
        cell = _cell(sheet, fl, bow)
        if cell.get("team_id") in (None, ""):
            continue
        need += 1
        if _parse_rank(cell.get("rank")) is not None:
            have += 1
    return need >= 2 and have == need


def _highest_used(sheet: dict) -> int:
    used = 2
    for fl in range(1, MAX_FLIGHTS + 1):
        bows = sum(1 for bow in range(1, 7) if _cell(sheet, fl, bow).get("team_id") not in (None, ""))
        if bows or _flight_done(sheet, fl):
            used = fl
    return used


def _score_adjust(sheet: dict, fl: int, team_id) -> int:
    block = ((_sheet_adjust(sheet).get(str(fl)) or {}).get(str(team_id)))
    if block in (None, ""):
        return 0
    raw = block.get("delta") if isinstance(block, dict) else block
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return 0


def _sheet_adjust(sheet: dict) -> dict:
    raw = sheet.get("score_adjust") or {}
    return raw if isinstance(raw, dict) else {}


def team_flight_score(sheet: dict, fl: int, team_id) -> str:
    need = 0
    have = 0
    total = 0
    for bow in range(1, 7):
        cell = _cell(sheet, fl, bow)
        if str(cell.get("team_id")) != str(team_id):
            continue
        need += 1
        rank = _parse_rank(cell.get("rank"))
        if rank is not None:
            have += 1
            total += rank
    if not need or have != need:
        return ""
    return str(total + _score_adjust(sheet, fl, team_id))


def _has_first(sheet: dict, fl: int, team_id) -> bool:
    for bow in range(1, 7):
        cell = _cell(sheet, fl, bow)
        if str(cell.get("team_id")) == str(team_id) and _parse_rank(cell.get("rank")) == 1:
            return True
    return False


def flight_winner_id(sheet: dict, fl: int, teams: list[dict]) -> int:
    """Lowest combined boat ranks among rostered teams. Ghost team_ids do not win."""
    if not _flight_done(sheet, fl):
        return 0
    entries = []
    for team in teams:
        sc = team_flight_score(sheet, fl, team["team_id"])
        if sc == "":
            continue
        entries.append(
            {
                "id": int(team["team_id"]),
                "score": float(sc),
                "first": _has_first(sheet, fl, team["team_id"]),
            }
        )
    if len(entries) < 2:
        return 0
    entries.sort(key=lambda e: e["score"])
    if entries[0]["score"] < entries[1]["score"]:
        return entries[0]["id"]
    if entries[0]["score"] == entries[1]["score"]:
        if entries[0]["first"] and not entries[1]["first"]:
            return entries[1]["id"]
        if entries[1]["first"] and not entries[0]["first"]:
            return entries[0]["id"]
    return 0


def _completed_races(sheet: dict, teams: list[dict]) -> list[dict]:
    out = []
    for fl in range(1, MAX_FLIGHTS + 1):
        if not _flight_done(sheet, fl):
            continue
        parts = []
        for team in teams:
            sc = team_flight_score(sheet, fl, team["team_id"])
            if sc == "":
                continue
            parts.append({"id": int(team["team_id"]), "score": float(sc)})
        if len(parts) != 2:
            continue
        out.append(
            {
                "fl": fl,
                "a": parts[0]["id"],
                "b": parts[1]["id"],
                "sa": parts[0]["score"],
                "sb": parts[1]["score"],
                "winner": flight_winner_id(sheet, fl, teams),
            }
        )
    return out


def _h2h_win_pct(races, tid, ids) -> float:
    wins = 0
    n = 0
    for race in races:
        if race["a"] not in ids or race["b"] not in ids:
            continue
        if race["a"] != tid and race["b"] != tid:
            continue
        n += 1
        if race["winner"] == tid:
            wins += 1
    return wins / n if n else 0.0


def _h2h_avg(races, tid, ids) -> float:
    total = 0.0
    n = 0
    for race in races:
        if race["a"] not in ids or race["b"] not in ids:
            continue
        if race["a"] == tid:
            total += race["sa"]
            n += 1
        elif race["b"] == tid:
            total += race["sb"]
            n += 1
    return total / n if n else 0.0


def _last_winner(races, id_a, id_b) -> int:
    last = 0
    for race in races:
        if (race["a"] == id_a and race["b"] == id_b) or (race["a"] == id_b and race["b"] == id_a):
            last = race["winner"]
    return last


def _common_opp_avg(races, tid, ids, all_ids) -> float:
    others = [i for i in all_ids if i not in ids]
    total = 0.0
    n = 0
    for race in races:
        opp = race["b"] if race["a"] == tid else (race["a"] if race["b"] == tid else 0)
        if not opp or opp not in others:
            continue
        total += race["sa"] if race["a"] == tid else race["sb"]
        n += 1
    return total / n if n else 1e9


def _pair_sailed(races, ids) -> bool:
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            if not any((r["a"] == a and r["b"] == b) or (r["a"] == b and r["b"] == a) for r in races):
                return False
    return True


def _split_by_key(group, key_fn, reverse=False):
    buckets: dict[str, list] = {}
    keys = []
    for item in group:
        n = key_fn(item)
        k = str(n)
        if k not in buckets:
            buckets[k] = []
            keys.append((k, n))
        buckets[k].append(item)
    keys.sort(key=lambda x: x[1], reverse=reverse)
    return [buckets[k] for k, _ in keys]


def _apply_d44(group, races, all_ids, steps, full_steps):
    if len(group) <= 1 or not steps:
        return [group]
    ids = [int(g["team"]["team_id"]) for g in group]
    step = steps[0]
    rest = steps[1:]
    if step == "h2hPct":
        parts = _split_by_key(group, lambda item: _h2h_win_pct(races, int(item["team"]["team_id"]), ids), reverse=True)
    elif step == "h2hAvg":
        parts = _split_by_key(group, lambda item: _h2h_avg(races, int(item["team"]["team_id"]), ids))
    elif step == "last":
        if len(group) != 2:
            return _apply_d44(group, races, all_ids, rest, full_steps)
        a = int(group[0]["team"]["team_id"])
        b = int(group[1]["team"]["team_id"])
        winner = _last_winner(races, a, b)
        if not winner:
            return _apply_d44(group, races, all_ids, rest, full_steps)
        parts = [[group[0]], [group[1]]] if winner == a else [[group[1]], [group[0]]]
    elif step == "common":
        parts = _split_by_key(group, lambda item: _common_opp_avg(races, int(item["team"]["team_id"]), ids, all_ids))
    else:
        return [group]
    if len(parts) == 1 and len(parts[0]) == len(group):
        return _apply_d44(group, races, all_ids, rest, full_steps)
    out = []
    for part in parts:
        if len(part) <= 1:
            out.append(part)
        else:
            out.extend(_apply_d44(part, races, all_ids, full_steps, full_steps))
    return out


def _rank_built(built: list[dict], races: list[dict]) -> list[dict]:
    raced = [item for item in built if item.get("scored") and item.get("team")]
    if not raced:
        return built
    equal = all(item["scored"] == raced[0]["scored"] for item in raced)
    parts = _split_by_key(raced, lambda item: item["wins"] if equal else item["win_pct"], reverse=True)
    all_ids = [int(item["team"]["team_id"]) for item in raced]
    ordered = []
    for part in parts:
        if len(part) <= 1:
            ordered.append(part)
            continue
        ids = [int(item["team"]["team_id"]) for item in part]
        between = [r for r in races if r["a"] in ids and r["b"] in ids]
        steps = ["h2hPct", "h2hAvg", "last", "common"] if _pair_sailed(between, ids) else ["common"]
        ordered.extend(_apply_d44(part, races, all_ids, steps, steps))
    rank = 1
    for group in ordered:
        for item in group:
            item["rank"] = rank
            item["rank_label"] = f"={rank}" if len(group) > 1 else str(rank)
        rank += len(group)
    return built


def gold_built(state: dict) -> list[dict]:
    """Same board the parent TSL sheet paints: rank, wins, total, F15…F1."""
    sheet = _sheet(state)
    teams = _teams(state)
    if not sheet or not teams:
        return []
    max_fl = _highest_used(sheet)
    race_nos = list(range(max_fl, 0, -1))
    races = _completed_races(sheet, teams)
    built = []
    for team in teams:
        points = 0
        scored = 0
        wins = 0
        flights = {}
        for n in race_nos:
            sc = team_flight_score(sheet, n, team["team_id"])
            if sc != "":
                points += int(float(sc))
                scored += 1
                flights[n] = sc
                if flight_winner_id(sheet, n, teams) == int(team["team_id"]):
                    wins += 1
        built.append(
            {
                "team": team,
                "team_id": int(team["team_id"]),
                "team_name": (team.get("team_name") or "").strip(),
                "result_id": team.get("result_id"),
                "points": points,
                "wins": wins,
                "scored": scored,
                "flights": flights,
                "win_pct": (wins / scored) if scored else 0.0,
            }
        )
    built = [item for item in built if item["scored"]]
    _rank_built(built, races)
    built.sort(key=lambda item: (item.get("rank") or 999, item["team_id"]))
    return built


def apply_parent_tsl_board(rows: list[dict], state: dict | None) -> list[dict]:
    """Stamp parent TSL ranks onto /api/regatta rows. Unscored teams stay unranked."""
    if not rows or not state:
        return list(rows)
    board = gold_built(state)
    if not board:
        return list(rows)
    sailed = max((max(item["flights"]) if item["flights"] else 0) for item in board)
    by_result = {item["result_id"]: item for item in board if item.get("result_id") not in (None, "")}
    by_name = {item["team_name"].strip().lower(): item for item in board if item.get("team_name")}
    out = []
    for raw in rows:
        row = dict(raw)
        name = (row.get("boat_name") or row.get("team_name") or "").strip().lower()
        item = by_result.get(row.get("result_id")) or by_name.get(name)
        if item:
            row["rank"] = item.get("rank")
            row["team_rank"] = item.get("rank")
            row["team_wins"] = item.get("wins")
            row["total_points_raw"] = item.get("points")
            row["nett_points_raw"] = item.get("points")
            row["race_scores"] = {f"F{n}": sc for n, sc in sorted(item["flights"].items(), reverse=True)}
            row["races_sailed"] = sailed
            row["scoring_system"] = row.get("scoring_system") or "Team Racing"
        out.append(row)
    out.sort(key=lambda r: (r.get("rank") in (None, ""), r.get("rank") or 999))
    return out


def overlay_tsl_rows(slug: str, rows: list[dict], fetch_json=None, state: dict | None = None) -> list[dict]:
    """If this is a TSL / team-racing card, replace empty ranks with the parent sheet."""
    if not rows:
        return list(rows)
    from event_rewrite import is_team_racing

    if not is_team_racing(rows[0], slug=slug, rows=rows):
        return list(rows)
    payload = state if state is not None else fetch_tsl_state(slug, fetch_json=fetch_json)
    return apply_parent_tsl_board(rows, payload)
