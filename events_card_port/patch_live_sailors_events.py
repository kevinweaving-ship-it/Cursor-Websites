#!/usr/bin/env python3
"""Live patch: sailors active JOIN + events parent dedupe (keep regatta URLs)."""
from pathlib import Path
import sys

path = Path(sys.argv[1])
t = path.read_text(encoding="utf-8")
changed = []

# --- 1) active=1 INNER JOIN (sailors search speed) ---
OLD_EXISTS = """                if active_on:
                    conditions.append(\"\"\"
                        EXISTS (
                            SELECT 1 FROM public.results r
                            JOIN public.regattas reg ON reg.regatta_id = r.regatta_id
                            WHERE r.raced = TRUE
                              AND (reg.end_date IS NOT NULL OR reg.start_date IS NOT NULL)
                              AND (
                                r.helm_sa_sailing_id::text = s.sa_sailing_id::text
                                OR r.crew_sa_sailing_id::text = s.sa_sailing_id::text
                              )
                        )
                    \"\"\")
                
                # Check if we should skip SA ID query"""

if "active_sailors ON active_sailors.sailor_id" not in t:
    if OLD_EXISTS not in t:
        raise SystemExit("active EXISTS block not found")
    anchor = "                    # Build sail/boat name search JOIN if needed (replaces EXISTS clause)\n                    sail_boat_join = \"\""
    if anchor not in t:
        raise SystemExit("sail_boat anchor not found")
    insert = """                    # Active sailors only: join pre-filtered set (faster than per-row EXISTS)
                    active_join = ""
                    if active_on:
                        active_join = \"\"\"
                            INNER JOIN (
                                SELECT DISTINCT sailor_id FROM (
                                    SELECT r.helm_sa_sailing_id::text AS sailor_id
                                    FROM public.results r
                                    JOIN public.regattas reg ON reg.regatta_id = r.regatta_id
                                    WHERE r.raced = TRUE
                                      AND r.helm_sa_sailing_id IS NOT NULL AND r.helm_sa_sailing_id::text != ''
                                      AND (reg.end_date IS NOT NULL OR reg.start_date IS NOT NULL)
                                    UNION
                                    SELECT r.crew_sa_sailing_id::text AS sailor_id
                                    FROM public.results r
                                    JOIN public.regattas reg ON reg.regatta_id = r.regatta_id
                                    WHERE r.raced = TRUE
                                      AND r.crew_sa_sailing_id IS NOT NULL AND r.crew_sa_sailing_id::text != ''
                                      AND (reg.end_date IS NOT NULL OR reg.start_date IS NOT NULL)
                                ) u
                            ) active_sailors ON active_sailors.sailor_id = s.sa_sailing_id::text
                        \"\"\"
                    # Build sail/boat name search JOIN if needed (replaces EXISTS clause)
                    sail_boat_join = \"\""""
    t = t.replace(anchor, insert, 1)
    t = t.replace(
        OLD_EXISTS,
        "\n                # active_on uses active_join INNER JOIN (see above)\n                \n                # Check if we should skip SA ID query",
        1,
    )
    for old_from, new_from in (
        (
            "FROM public.sas_id_personal s\n                            {sail_boat_join}",
            "FROM public.sas_id_personal s\n                            {active_join}\n                            {sail_boat_join}",
        ),
        (
            "FROM public.sas_id_personal s\n                        {sail_boat_join}",
            "FROM public.sas_id_personal s\n                        {active_join}\n                        {sail_boat_join}",
        ),
    ):
        if old_from in t:
            t = t.replace(old_from, new_from, 1)
    changed.append("active JOIN")

# --- 1b) short single-token hub+active: prefix match (Tim/Rae) not %tim% scan ---
OLD_HUB_TOK = """                            elif hub_on and tokens:
                                _append_sailor_token_sql(tokens[0], include_clubs=True)"""
NEW_HUB_TOK = """                            elif hub_on and tokens:
                                tok0 = tokens[0]
                                if active_on and len(tok0) <= 5:
                                    esc0 = _escape_like(tok0)
                                    pfx0 = f"{esc0}%"
                                    conditions.append(\"\"\"
                                        (
                                         LOWER(COALESCE(s.first_name,'')) LIKE %s
                                         OR LOWER(COALESCE(s.last_name,'')) LIKE %s
                                         OR CAST(s.sa_sailing_id AS TEXT) LIKE %s
                                        )
                                    \"\"\")
                                    params.extend([pfx0, pfx0, pfx0])
                                else:
                                    _append_sailor_token_sql(tok0, include_clubs=True)"""
if OLD_HUB_TOK in t and "pfx0 = f" not in t:
    t = t.replace(OLD_HUB_TOK, NEW_HUB_TOK, 1)
    changed.append("short name prefix search")

# --- 2) events parent dedupe helpers (display only — keep regatta URLs) ---
HELPERS = '''
def _event_card_calendar_year(card: dict) -> int:
    iso = (str(card.get("start_date_iso") or card.get("end_date_iso") or ""))[:10]
    if len(iso) >= 4 and iso[4:5] == "-":
        try:
            y = int(iso[:4])
            if 1990 <= y <= 2100:
                return y
        except ValueError:
            pass
    rid = str(card.get("regatta_id") or "")
    m = re.search(r"-(19|20)\\d{2}-", f"-{rid}-")
    if m:
        return int(m.group(1))
    m2 = re.search(r"\\b(19|20)\\d{2}\\b", str(card.get("event_name") or ""))
    if m2:
        return int(m2.group(0))
    return 0


def _events_parent_card_score(card: dict) -> tuple:
    has_res = 1 if card.get("result_yes") else 0
    entries = int(card.get("entries") or card.get("entries_for_sort") or 0)
    name = str(card.get("event_name") or "")
    class_penalty = 1 if re.search(r"class\\s*fleets?", name, re.I) else 0
    return (has_res, entries, -class_penalty, -len(name))


def _merge_events_parent_group(group: list, series_key: str, year: int) -> dict:
    """Collapse same-series same-year legs — keep best card URLs (/regatta/...)."""
    best = max(group, key=_events_parent_card_score)
    merged = dict(best)
    any_results = any(bool(c.get("result_yes")) for c in group)
    canon = _yearly_canonical_display_for_key(series_key)
    base = canon or str(merged.get("event_name") or "").strip() or "—"
    display = f"{base} {year}".strip()
    if any_results and (merged.get("event_state") or "PAST") == "PAST":
        display = f"{base} {year} Results".strip()
    merged["event_name"] = base
    merged["display_title"] = display
    merged["result_yes"] = any_results
    merged["entries"] = max(int(c.get("entries") or c.get("entries_for_sort") or 0) for c in group)
    merged["entries_for_sort"] = merged["entries"]
    if any_results and merged.get("details_url", "").startswith("/regatta/"):
        merged["result_url"] = merged.get("details_url") or merged.get("result_url") or ""
    hosts = {
        str(c.get("host_code") or "").strip()
        for c in group
        if str(c.get("host_code") or "").strip() not in ("", "—", "-", "TBC", "Unk", "Unassigned")
    }
    if len(hosts) > 1:
        merged["host_code"] = "Various"
        merged["host_club"] = "Various"
        merged["host_club_fullname"] = ""
        merged["club_slug"] = ""
        merged["club_logo_url"] = ""
    return merged


def _collapse_events_page_parent_cards(cards: list) -> list:
    """One card per named series per calendar year; no URL rewrites."""
    if not cards:
        return []
    buckets: dict[tuple[str, int], list] = {}
    passthrough: list = []
    for card in cards:
        c = dict(card)
        sk = _yearly_event_series_key(str(c.get("event_name") or ""))
        yr = _event_card_calendar_year(c)
        if not sk or yr <= 0:
            passthrough.append(c)
            continue
        buckets.setdefault((sk, yr), []).append(c)
    out = list(passthrough)
    for (sk, yr), group in buckets.items():
        if len(group) == 1:
            out.append(group[0])
        else:
            out.append(_merge_events_parent_group(group, sk, yr))
    return out

'''

if "_collapse_events_page_parent_cards" not in t:
    anchor = "def _sort_past_event_cards(cards: list) -> list:"
    if anchor not in t:
        raise SystemExit("_sort_past_event_cards anchor not found")
    t = t.replace(anchor, HELPERS + "\n" + anchor, 1)
    changed.append("events collapse helpers")

OLD_SORT = """        out["past"] = _sort_past_event_cards(out["past"])
        t5 = time.time()
        print("EVENTS: rows upcoming:"""
NEW_SORT = """        if host_club_id is None:
            out["upcoming"] = _collapse_events_page_parent_cards(out["upcoming"])
            out["live"] = _collapse_events_page_parent_cards(out.get("live") or [])
            out["past"] = _collapse_events_page_parent_cards(_sort_past_event_cards(out["past"]))
        else:
            out["past"] = _sort_past_event_cards(out["past"])
        t5 = time.time()
        print("EVENTS: rows upcoming:"""

if "_collapse_events_page_parent_cards(out[\"past\"])" not in t:
    if OLD_SORT not in t:
        raise SystemExit("events sort anchor not found in _get_upcoming_events")
    t = t.replace(OLD_SORT, NEW_SORT, 1)
    changed.append("events collapse call")

OLD_TYPE = """        out["past"] = _sort_past_event_cards(out["past"])
        cur.close()"""
NEW_TYPE = """        out["upcoming"] = _collapse_events_page_parent_cards(out["upcoming"])
        out["live"] = _collapse_events_page_parent_cards(out.get("live") or [])
        out["past"] = _collapse_events_page_parent_cards(_sort_past_event_cards(out["past"]))
        cur.close()"""
if "out[\"upcoming\"] = _collapse_events_page_parent_cards" not in t.split(OLD_SORT, 1)[-1][:500]:
    if OLD_TYPE in t:
        t = t.replace(OLD_TYPE, NEW_TYPE, 1)
        changed.append("events type collapse")

# --- 3) sailors dir6 cache buster ---
t = t.replace("hub-sailor-directory.js?v=20260823dir5", "hub-sailor-directory.js?v=20260823dir6")

path.write_text(t, encoding="utf-8")
print("patched:", ", ".join(changed) or "cache buster only")
print("done", path)
