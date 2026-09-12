#!/usr/bin/env python3
"""Surgical live api.py patch: Event URL is the only source of truth.

- Event header Total Entries = COUNT of all boats entered on that event.
- /regatta/{event}/class-{slug} serves the Event's current fleet (no leftover
  independent {event}-{tail} child, no /events dump).
- Fleet-shell URLs 301 to the Event child path.
- Landing children carry class_slug + parent_regatta_id for /class- hrefs.
"""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

HELPERS = r'''
def _event_entered_boats_count(regatta_id: str) -> int:
    """Event URL truth: every entered boat on this event, not raced-only, not series max."""
    rid = str(regatta_id or "").strip()
    if not rid:
        return 0
    try:
        rows = q(
            """
            SELECT COUNT(*)::int AS n
            FROM results
            WHERE regatta_id::text = %s AND result_id IS NOT NULL
            """,
            (rid,),
        )
        return int((rows[0] or {}).get("n") or 0) if rows else 0
    except Exception:
        return 0


def _event_child_slug_from_labels(fleet_label=None, class_original=None, class_canonical=None, block_id=None) -> str:
    display = (
        str(fleet_label or "").strip()
        or str(class_original or "").strip()
        or str(class_canonical or "").strip()
    )
    display = re.sub(r"(?i)\s+fleet$", "", display).strip()
    if not display and block_id:
        tail = str(block_id).split(":")[-1]
        display = re.sub(r"(?i)-fleet$", "", tail).replace("-", " ")
    s = display.strip().lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9.-]", "", s).strip("-")
    return s


def _norm_event_child_slug(value) -> str:
    s = str(value or "").strip().lower().replace("_", "-")
    s = re.sub(r"(?i)-fleet$", "", s)
    s = re.sub(r"[^a-z0-9.-]", "", s)
    return s.strip("-")


def _event_block_child_slug(parent_regatta_id: str, block_id: str) -> str:
    rid = str(parent_regatta_id or "").strip()
    bid = str(block_id or "").strip()
    if not rid or not bid:
        return ""
    try:
        rows = q(
            """
            SELECT fleet_label, class_original, class_canonical, block_id
            FROM regatta_blocks
            WHERE regatta_id::text = %s AND block_id::text = %s
            LIMIT 1
            """,
            (rid, bid),
        )
        if not rows:
            return ""
        r = rows[0]
        return _event_child_slug_from_labels(
            r.get("fleet_label"), r.get("class_original"), r.get("class_canonical"), r.get("block_id")
        )
    except Exception:
        return _event_child_slug_from_labels(block_id=bid)


def _match_event_child_fleet(regatta_id: str, class_slug: str):
    """Resolve /class-{slug} against THIS event's current blocks only.

    Returns (canonical_slug, block_id, display_name) or None (leftover → Event URL).
    Boat classes inside a mixed fleet (420 in Open) resolve to that Event fleet.
    """
    rid = str(regatta_id or "").strip()
    want = _norm_event_child_slug(class_slug)
    if not rid or not want:
        return None
    try:
        blocks = q(
            """
            SELECT rb.block_id, rb.fleet_label, rb.class_original, rb.class_canonical,
                   COALESCE(c.class_name, '') AS result_class_name
            FROM regatta_blocks rb
            LEFT JOIN results res ON res.block_id = rb.block_id AND res.regatta_id = rb.regatta_id
            LEFT JOIN classes c ON c.class_id = COALESCE(res.class_id, rb.class_id)
            WHERE rb.regatta_id::text = %s
            """,
            (rid,),
        ) or []
    except Exception:
        return None
    by_bid = {}
    for row in blocks:
        bid = str(row.get("block_id") or "").strip()
        if not bid:
            continue
        rec = by_bid.setdefault(
            bid,
            {
                "fleet_label": row.get("fleet_label"),
                "class_original": row.get("class_original"),
                "class_canonical": row.get("class_canonical"),
                "extra": set(),
            },
        )
        extra = str(row.get("result_class_name") or row.get("class_original") or "").strip()
        if extra:
            rec["extra"].add(extra)
    for bid, rec in by_bid.items():
        canon = _event_child_slug_from_labels(
            rec.get("fleet_label"), rec.get("class_original"), rec.get("class_canonical"), bid
        )
        aliases = {canon, _norm_event_child_slug(rec.get("fleet_label")), _norm_event_child_slug(rec.get("class_original")), _norm_event_child_slug(rec.get("class_canonical"))}
        if ":" in bid:
            aliases.add(_norm_event_child_slug(bid.split(":", 1)[1]))
        for nm in rec.get("extra") or []:
            aliases.add(_norm_event_child_slug(nm))
        aliases.discard("")
        if want in aliases and canon:
            display = (
                str(rec.get("fleet_label") or "").strip()
                or str(rec.get("class_original") or "").strip()
                or str(rec.get("class_canonical") or "").strip()
                or canon
            )
            display = re.sub(r"(?i)\s+fleet$", "", display).strip() or canon
            return (canon, bid, display)
    return None

'''

REPLACEMENTS = [
    (
        '''def _cape_classic_total_entries_line_html(regatta_id: str, fleets) -> str:
    """Small line under Results-are status: Total Entries = N across all fleets."""
    if str(regatta_id or "").strip() != "2026-09-13-zvyc-cape-classic":
        return ""
    n = 0
    for fl in fleets or []:
        if not isinstance(fl, dict):
            continue
        nm = str(fl.get("name") or "").strip().lower()
        if nm in {"staff", "results pdf"} or nm.endswith(" pdf"):
            continue
        rows = fl.get("rows")
        if isinstance(rows, list) and rows:
            n += len(rows)
        else:
            try:
                n += int(fl.get("entries") or 0)
            except (TypeError, ValueError):
                pass
    if n <= 0:
        return ""
    return f'<div class="entry-total-line">Total Entries = {n}</div>'
''',
        '''def _cape_classic_total_entries_line_html(regatta_id: str, fleets=None) -> str:
    """Event URL truth: Total Entries = all boats entered on this event."""
    n = _event_entered_boats_count(regatta_id)
    if n <= 0:
        n = 0
        for fl in fleets or []:
            if not isinstance(fl, dict):
                continue
            nm = str(fl.get("name") or "").strip().lower()
            if nm in {"staff", "results pdf"} or nm.endswith(" pdf"):
                continue
            rows = fl.get("rows")
            if isinstance(rows, list) and rows:
                n += len(rows)
            else:
                try:
                    n += int(fl.get("entries") or 0)
                except (TypeError, ValueError):
                    pass
    if n <= 0:
        return ""
    return f'<div class="entry-total-line">Total Entries = {n}</div>'
''',
    ),
    (
        '''def serve_regatta_class_standalone(slug: str, class_slug: str, request: Request):
    """Serve class-filtered ladder at /regatta/{slug}/class-{class_slug}.

    Multi-fleet umbrellas (Fast+Slow, etc.): sub-URLs are **fleet_shell** `…-{fleet_tail}`, not class — see PROCESS /
    redirect to fleet_shell when the slice is one fleet block."""
    reg = _get_regatta_by_slug(slug)
    if not reg:
        return RedirectResponse(url="/events", status_code=301)
    regatta_id = reg[0]
    if _regatta_block_count(str(regatta_id).strip()) <= 1 and _single_fleet_is_mixed_or_overall(str(regatta_id).strip()):
        rid_m = quote(str(regatta_id).strip(), safe="")
        return RedirectResponse(url=f"/regatta/{rid_m}", status_code=301)
    cid, class_name = _resolve_class_slug_to_class_id(class_slug.strip())
    if not cid or not class_name:
        return RedirectResponse(url="/events", status_code=301)
    canonical_class_slug = _class_canonical_slug(class_name)
    if str(slug).strip() != str(regatta_id):
        tail = canonical_class_slug if canonical_class_slug else class_slug.strip()
        return RedirectResponse(url=f"/regatta/{regatta_id}/class-{tail}", status_code=301)
    if canonical_class_slug and class_slug.strip().lower() != canonical_class_slug.lower():
        return RedirectResponse(url=f"/regatta/{regatta_id}/class-{canonical_class_slug}", status_code=301)
    data = _get_regatta_class_page_data(regatta_id, cid)
    if not data:
        return RedirectResponse(url="/events", status_code=301)
    if len(data) >= 10:
        ev_name, host_club_name, start_d, end_d, fleets, result_status, as_at_time, host_club_province, host_club_abbrev, host_club_fullname = data[:10]
    else:
        ev_name, host_club_name, start_d, end_d, fleets, result_status, as_at_time, host_club_province = data[:8]
        host_club_abbrev, host_club_fullname = "", ""
    if len(fleets) != 1:
        return RedirectResponse(url="/events", status_code=301)
    # Multi-fleet championship: a /class-* slice that falls entirely in one block must use fleet_shell (PDF fleet ladder).
    _solo_bid = str((fleets[0] or {}).get("block_id") or "")
    if ":" in _solo_bid and _regatta_has_sibling_block(regatta_id, _solo_bid):
        _tail = _solo_bid.split(":", 1)[1]
        _dest = f"/regatta/{quote(str(regatta_id).strip(), safe='')}-{quote(_tail, safe='')}"
        return RedirectResponse(url=_dest, status_code=301)
    try:
''',
        '''def serve_regatta_class_standalone(slug: str, class_slug: str, request: Request):
    """Child of the Event URL. Current event blocks are the only source of truth."""
    reg = _get_regatta_by_slug(slug)
    if not reg:
        return RedirectResponse(url="/events", status_code=301)
    regatta_id = reg[0]
    rid_q = quote(str(regatta_id).strip(), safe="")
    matched = _match_event_child_fleet(str(regatta_id).strip(), class_slug)
    if not matched:
        return RedirectResponse(url=f"/regatta/{rid_q}", status_code=301)
    canonical_class_slug, _child_block_id, class_name = matched
    if str(slug).strip() != str(regatta_id):
        return RedirectResponse(url=f"/regatta/{rid_q}/class-{quote(canonical_class_slug, safe='')}", status_code=301)
    if (class_slug or "").strip().lower() != str(canonical_class_slug).lower():
        return RedirectResponse(url=f"/regatta/{rid_q}/class-{quote(canonical_class_slug, safe='')}", status_code=301)
    data = _get_regatta_full_page_data(str(regatta_id), only_block_id=_child_block_id)
    if not data:
        return RedirectResponse(url=f"/regatta/{rid_q}", status_code=301)
    if len(data) >= 10:
        ev_name, host_club_name, start_d, end_d, fleets, result_status, as_at_time, host_club_province, host_club_abbrev, host_club_fullname = data[:10]
    else:
        ev_name, host_club_name, start_d, end_d, fleets, result_status, as_at_time, host_club_province = data[:8]
        host_club_abbrev, host_club_fullname = "", ""
    if len(fleets) != 1:
        return RedirectResponse(url=f"/regatta/{rid_q}", status_code=301)
    try:
''',
    ),
    (
        '''        if _canon_child and requested_slug != _canon_child:
            return RedirectResponse(url=f"/regatta/{quote(_canon_child, safe='')}", status_code=301)
        reg = _get_regatta_by_regatta_id(rid_shell)
        if reg:
            only_block_id = bid_shell
''',
        '''        _class_tail = _event_block_child_slug(rid_shell, bid_shell)
        if _class_tail:
            return RedirectResponse(
                url=f"/regatta/{quote(rid_shell, safe='')}/class-{quote(_class_tail, safe='')}",
                status_code=301,
            )
        if _canon_child and requested_slug != _canon_child:
            return RedirectResponse(url=f"/regatta/{quote(_canon_child, safe='')}", status_code=301)
        reg = _get_regatta_by_regatta_id(rid_shell)
        if reg:
            only_block_id = bid_shell
''',
    ),
    (
        '''                    SELECT rb.regatta_id,
                           rb.block_id,
                           rb.fleet_label,
                           rb.class_canonical,
                           COALESCE(
                             NULLIF(TRIM(rb.block_label_raw), ''),
                             NULLIF(TRIM(rb.fleet_label), ''),
                             NULLIF(TRIM(rb.class_canonical), ''),
                             NULLIF(split_part(rb.block_id, ':', 2), '')
                           ) AS fleet_name,
                           COUNT(r.result_id)::int AS entries
                    FROM regatta_blocks rb
                    LEFT JOIN results r ON r.block_id = rb.block_id
                    WHERE rb.regatta_id = ANY(%s)
                    GROUP BY rb.regatta_id, rb.block_id, rb.block_label_raw, rb.fleet_label, rb.class_canonical
                    ORDER BY rb.regatta_id, rb.block_id
''',
        '''                    SELECT rb.regatta_id,
                           rb.block_id,
                           rb.fleet_label,
                           rb.class_canonical,
                           rb.class_original,
                           COALESCE(
                             NULLIF(TRIM(rb.block_label_raw), ''),
                             NULLIF(TRIM(rb.fleet_label), ''),
                             NULLIF(TRIM(rb.class_original), ''),
                             NULLIF(TRIM(rb.class_canonical), ''),
                             NULLIF(split_part(rb.block_id, ':', 2), '')
                           ) AS fleet_name,
                           COUNT(r.result_id)::int AS entries
                    FROM regatta_blocks rb
                    LEFT JOIN results r ON r.block_id = rb.block_id
                    WHERE rb.regatta_id = ANY(%s)
                    GROUP BY rb.regatta_id, rb.block_id, rb.block_label_raw, rb.fleet_label, rb.class_canonical, rb.class_original
                    ORDER BY rb.regatta_id, rb.block_id
''',
    ),
    (
        '''                    by_parent_blocks.setdefault(rid, []).append(
                        {
                            "regatta_id": f"{rid}-{tail}",
                            "search_label": None,
                            "fleet_label": (row.get("fleet_name") or tail).strip(),
                            "entries_count": int(row.get("entries") or 0),
                            "is_fleet_shell": True,
                        }
                    )
''',
        '''                    child_slug = _event_child_slug_from_labels(
                        row.get("fleet_label"),
                        row.get("class_original"),
                        row.get("class_canonical"),
                        bid,
                    ) or _norm_event_child_slug(tail)
                    display_name = (
                        str(row.get("fleet_label") or "").strip()
                        or str(row.get("class_original") or "").strip()
                        or str(row.get("fleet_name") or tail).strip()
                    )
                    display_name = re.sub(r"(?i)\\s+fleet$", "", display_name).strip() or display_name
                    by_parent_blocks.setdefault(rid, []).append(
                        {
                            "regatta_id": f"{rid}-{tail}",
                            "parent_regatta_id": rid,
                            "class_slug": child_slug,
                            "search_label": None,
                            "fleet_label": display_name,
                            "entries_count": int(row.get("entries") or 0),
                            "is_fleet_shell": True,
                        }
                    )
''',
    ),
    (
        '''                        cn = _fleet_label_to_catalogue_class_name(chosen, tail)
                        if cn:
                            chosen = cn
                        ch["search_label"] = _title_fleet(chosen)
                        ch["fleet_label"] = ch["search_label"]
''',
        '''                        # Event child already has class_slug from the Event sheet — do not rename to catalogue leftovers.
                        if not ch.get("class_slug"):
                            cn = _fleet_label_to_catalogue_class_name(chosen, tail)
                            if cn:
                                chosen = cn
                            ch["search_label"] = _title_fleet(chosen)
                            ch["fleet_label"] = ch["search_label"]
''',
    ),
]


INSERT_AFTER = '''    return f"{parent}-{tail}"


# --- catalogue class logo artwork fallback ---
'''

INSERT_AFTER_NEW = '''    return f"{parent}-{tail}"

''' + HELPERS + '''
# --- catalogue class logo artwork fallback ---
'''


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    text = path.read_text(encoding="utf-8")
    n_ins = text.count(INSERT_AFTER)
    if n_ins != 1:
        raise SystemExit(f"{path}: helper insert expected 1 match, found {n_ins}")
    text = text.replace(INSERT_AFTER, INSERT_AFTER_NEW, 1)
    for i, (old, new) in enumerate(REPLACEMENTS):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: expected 1 match for replacement {i}, found {n}\n{old[:180]!r}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
