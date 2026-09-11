#!/usr/bin/env python3
"""Surgical live api.py patches: automatic fleet-shell child URLs.

Public child slug is derived from class (ILCA 4.7 → ilca-4.7-fleet), not from a
truncated block_id tail. Class pages, events chips, and fleet headers share one
helper. No per-regatta SQL rename is required when a class is added.
"""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

HELPERS = r'''
def _block_id_raw_tail(block_id: Optional[str]) -> str:
    bid = str(block_id or "").strip()
    if ":" in bid:
        return bid.split(":", 1)[1].strip()
    return bid


_FLEET_TAIL_CLASS_SLUG_ALIASES = {
    "ilca-4": "ilca-4.7",
    "ilca-4-7": "ilca-4.7",
    "ilca-47": "ilca-4.7",
    "ilca-4-16": "ilca-4.7",
    "laser-4": "ilca-4.7",
    "laser-47": "ilca-4.7",
    "laser-4.7": "ilca-4.7",
    "ilca-6-16": "ilca-6",
}

_MIXED_FLEET_SHELL_TAILS = frozenset(
    {
        "open",
        "overall",
        "fast",
        "slow",
        "mixed",
        "handicap",
    }
)


def _regatta_is_upcoming_or_happening(end_date=None, start_date=None) -> bool:
    """True while the event has not yet ended (upcoming or in progress)."""
    from datetime import date as _date_cls
    value = end_date or start_date
    if value is None:
        return False
    if hasattr(value, "date"):
        try:
            value = value.date()
        except Exception:
            pass
    day = ""
    if hasattr(value, "isoformat"):
        try:
            day = str(value.isoformat())[:10]
        except Exception:
            day = ""
    if not day:
        s = str(value).strip()
        day = s[:10] if len(s) >= 10 else s
    if not day:
        return False
    try:
        return day >= _date_cls.today().isoformat()
    except Exception:
        return False


def _fleet_shell_public_tail(
    block_id: Optional[str] = None,
    fleet_label: Optional[str] = None,
    class_canonical: Optional[str] = None,
    class_name: Optional[str] = None,
) -> str:
    """Public child-URL tail. Upgrade truncated tails (ilca-4 → ilca-4.7-fleet)."""
    raw = _block_id_raw_tail(block_id)
    raw_l = raw.lower().strip("-")
    raw_base = re.sub(r"-fleet$", "", raw_l)
    had_fleet = bool(raw_l.endswith("-fleet"))
    display = (
        str(class_canonical or "").strip()
        or str(class_name or "").strip()
        or str(fleet_label or "").strip()
    )
    display_core = re.sub(r"(?i)\s+fleet$", "", display).strip() if display else ""
    try:
        display_slug = _class_canonical_slug(display_core) if display_core else ""
    except Exception:
        display_slug = ""
        if display_core:
            s = display_core.strip().lower().replace(" ", "-")
            display_slug = re.sub(r"[^a-z0-9.-]", "", s).strip("-")
    mixed = (
        raw_l in _MIXED_FLEET_SHELL_TAILS
        or raw_base in _MIXED_FLEET_SHELL_TAILS
        or display_slug in _MIXED_FLEET_SHELL_TAILS
    )
    if mixed:
        return raw_l or display_slug
    class_slug = display_slug
    alias = _FLEET_TAIL_CLASS_SLUG_ALIASES.get(raw_base)
    if alias and (
        not class_slug
        or class_slug in ("ilca", "laser")
        or alias.startswith(class_slug)
        or class_slug.startswith(raw_base)
    ):
        class_slug = alias
    if class_slug and raw_base and class_slug != raw_base:
        if class_slug.startswith(raw_base) and len(class_slug) > len(raw_base):
            return f"{class_slug}-fleet" if had_fleet or not raw_l else class_slug
        return raw_l
    if class_slug and not raw_l:
        return f"{class_slug}-fleet"
    return raw_l


def _fleet_shell_public_url_slug(
    parent_regatta_id: Optional[str],
    block_id: Optional[str] = None,
    fleet_label: Optional[str] = None,
    class_canonical: Optional[str] = None,
    class_name: Optional[str] = None,
) -> Optional[str]:
    parent = str(parent_regatta_id or "").strip()
    tail = _fleet_shell_public_tail(
        block_id,
        fleet_label=fleet_label,
        class_canonical=class_canonical,
        class_name=class_name,
    )
    if not parent or not tail:
        return None
    return f"{parent}-{tail}"

'''

REPLACEMENTS = [
    (
        '''    return candidates[0] if candidates else None



# --- catalogue class logo artwork fallback ---''',
        '''    return candidates[0] if candidates else None

'''
        + HELPERS
        + '''
# --- catalogue class logo artwork fallback ---''',
    ),
    (
        '''                    SELECT rb.regatta_id,
                           rb.block_id,
                           COALESCE(
                             NULLIF(TRIM(rb.block_label_raw), ''),
                             NULLIF(TRIM(rb.fleet_label), ''),
                             NULLIF(split_part(rb.block_id, ':', 2), '')
                           ) AS fleet_name,
                           COUNT(r.result_id)::int AS entries
                    FROM regatta_blocks rb
                    LEFT JOIN results r ON r.block_id = rb.block_id
                    WHERE rb.regatta_id = ANY(%s)
                    GROUP BY rb.regatta_id, rb.block_id, rb.block_label_raw, rb.fleet_label
                    ORDER BY rb.regatta_id, rb.block_id''',
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
                    ORDER BY rb.regatta_id, rb.block_id''',
    ),
    (
        '''                    rid = str(row["regatta_id"] or "").strip()
                    bid = str(row["block_id"] or "").strip()
                    tail = bid.split(":", 1)[1] if ":" in bid else bid
                    if not rid or not tail:
                        continue
                    by_parent_blocks.setdefault(rid, []).append(
                        {
                            "regatta_id": f"{rid}-{tail}",''',
        '''                    rid = str(row["regatta_id"] or "").strip()
                    bid = str(row["block_id"] or "").strip()
                    tail = _fleet_shell_public_tail(
                        bid,
                        fleet_label=row.get("fleet_label"),
                        class_canonical=row.get("class_canonical"),
                        class_name=row.get("fleet_name"),
                    )
                    if not rid or not tail:
                        continue
                    by_parent_blocks.setdefault(rid, []).append(
                        {
                            "regatta_id": f"{rid}-{tail}",''',
    ),
    (
        '''        if n_blocks > 1 and ":" in bid:
            tail = bid.split(":", 1)[1]
            bl["fleet_shell_href"] = f"/regatta/{quote(rid_s, safe='')}-{quote(tail, safe='')}"''',
        '''        if n_blocks > 1 and ":" in bid:
            tail = _fleet_shell_public_tail(
                bid,
                fleet_label=bl.get("fleet_label"),
                class_canonical=bl.get("class_canonical"),
                class_name=bl.get("name") or bl.get("block_label_raw"),
            )
            if tail:
                bl["fleet_shell_href"] = f"/regatta/{quote(rid_s, safe='')}-{quote(tail, safe='')}"''',
    ),
    (
        '''            if len(rows) != 1:
                return None
            block_id = str(rows[0].get("block_id") or "").strip()
            rid = str(rows[0].get("regatta_id") or "").strip()
            if not block_id or not rid:
                return None
            return (rid, block_id)''',
        '''            if len(rows) != 1:
                # Canonical tail may differ from block_id (ilca-4-fleet → ilca-4.7-fleet).
                cur.execute(
                    """
                    SELECT rb.block_id, rb.regatta_id, rb.fleet_label, rb.class_canonical
                    FROM regatta_blocks rb
                    JOIN regattas r ON r.regatta_id = rb.regatta_id
                    WHERE strpos(rb.block_id::text, ':') > 0
                      AND array_length(string_to_array(rb.block_id::text, ':'), 1) = 2
                      AND %s LIKE (rb.regatta_id || '-%%')
                    """,
                    (s,),
                )
                matched = []
                for row in cur.fetchall() or []:
                    rid_m = str(row.get("regatta_id") or "").strip()
                    bid_m = str(row.get("block_id") or "").strip()
                    if not rid_m or not bid_m or not s.startswith(rid_m + "-"):
                        continue
                    req_tail = s[len(rid_m) + 1 :]
                    req_canon = _fleet_shell_public_tail(f"{rid_m}:{req_tail}") if req_tail else ""
                    block_canon = _fleet_shell_public_tail(
                        bid_m,
                        fleet_label=row.get("fleet_label"),
                        class_canonical=row.get("class_canonical"),
                    )
                    raw_tail = _block_id_raw_tail(bid_m)
                    raw_pub = f"{rid_m}-{raw_tail}" if raw_tail else ""
                    pub = f"{rid_m}-{block_canon}" if block_canon else ""
                    if s in (pub, raw_pub) or (req_canon and block_canon and req_canon == block_canon):
                        matched.append((len(rid_m), rid_m, bid_m))
                matched.sort(reverse=True)
                if len({(a[1], a[2]) for a in matched}) >= 1:
                    _best = matched[0]
                    rows = [{"regatta_id": _best[1], "block_id": _best[2]}]
            if len(rows) != 1:
                return None
            block_id = str(rows[0].get("block_id") or "").strip()
            rid = str(rows[0].get("regatta_id") or "").strip()
            if not block_id or not rid:
                return None
            return (rid, block_id)''',
    ),
    (
        '''    shell = _resolve_fleet_shell_public_slug(requested_slug)
    if shell:
        rid_shell, bid_shell = shell
        reg = _get_regatta_by_regatta_id(rid_shell)
        if reg:
            only_block_id = bid_shell''',
        '''    shell = _resolve_fleet_shell_public_slug(requested_slug)
    if shell:
        rid_shell, bid_shell = shell
        try:
            _canon_child = _fleet_shell_public_url_slug(rid_shell, bid_shell)
        except Exception:
            _canon_child = None
        if _canon_child and requested_slug != _canon_child:
            return RedirectResponse(url=f"/regatta/{quote(_canon_child, safe='')}", status_code=301)
        reg = _get_regatta_by_regatta_id(rid_shell)
        if reg:
            only_block_id = bid_shell''',
    ),
    (
        '''    if _resolve_fleet_shell_public_slug(fleet_shell_candidate):
        return RedirectResponse(url=f"/regatta/{quote(fleet_shell_candidate, safe='')}", status_code=301)''',
        '''    _shell_hit = _resolve_fleet_shell_public_slug(fleet_shell_candidate)
    if _shell_hit:
        _dest = fleet_shell_candidate
        try:
            _pub = _fleet_shell_public_url_slug(_shell_hit[0], _shell_hit[1])
            if _pub:
                _dest = _pub
        except Exception:
            pass
        return RedirectResponse(url=f"/regatta/{quote(_dest, safe='')}", status_code=301)''',
    ),
    (
        '''                MAX(rb.block_id) AS class_block_id,
                (
                    SELECT COUNT(*)::int FROM regatta_blocks rbx
                    WHERE rbx.regatta_id = r.regatta_id
                ) AS parent_block_count,''',
        '''                MAX(rb.block_id) AS class_block_id,
                MAX(rb.fleet_label) AS fleet_label,
                MAX(rb.class_canonical) AS class_canonical,
                (
                    SELECT COUNT(*)::int FROM regatta_blocks rbx
                    WHERE rbx.regatta_id = r.regatta_id
                ) AS parent_block_count,''',
    ),
    (
        '''            _bid = str(r.get("class_block_id") or "").strip()
            _parent_rid = str(r.get("regatta_id") or "").strip()
            _live_window = _parent_rid.startswith("2026-09-13-zvyc-cape-classic")
            try:
                from datetime import date as _date_cls
                _end = r.get("end_date") or r.get("start_date")
                if hasattr(_end, "date"):
                    _end = _end.date()
                elif isinstance(_end, str) and len(_end) >= 10:
                    _end = _date_cls.fromisoformat(_end[:10])
                if hasattr(_end, "isoformat") and str(_end)[:10] >= _date_cls.today().isoformat():
                    _live_window = True
            except Exception:
                pass
            if _live_window and _nblocks > 1 and _bid and ":" in _bid:
                _tail = _bid.split(":", 1)[1].strip()
                if _tail:
                    _rid = f"{str(r.get('regatta_id') or '').strip()}-{_tail}"
                    _slug = _rid''',
        '''            _bid = str(r.get("class_block_id") or "").strip()
            _parent_rid = str(r.get("regatta_id") or "").strip()
            _live_window = _regatta_is_upcoming_or_happening(r.get("end_date"), r.get("start_date"))
            if _live_window and _nblocks > 1 and _bid and ":" in _bid:
                _tail = _fleet_shell_public_tail(
                    _bid,
                    fleet_label=r.get("fleet_label"),
                    class_canonical=r.get("class_canonical") or class_name,
                    class_name=class_name,
                )
                if _tail:
                    _rid = f"{str(r.get('regatta_id') or '').strip()}-{_tail}"
                    _slug = _rid''',
    ),
    (
        '''                       MAX(rb.block_id) AS class_block_id,
                       (
                         SELECT COUNT(*)::int FROM regatta_blocks rbx
                         WHERE rbx.regatta_id = r.regatta_id
                       ) AS parent_block_count
                FROM regatta_blocks rb
                JOIN regattas r ON r.regatta_id = rb.regatta_id
                LEFT JOIN results res ON res.block_id = rb.block_id
                LEFT JOIN clubs c ON c.club_id = r.host_club_id
                WHERE rb.class_id = %s
                  AND r.regatta_id = '2026-09-13-zvyc-cape-classic'
                GROUP BY r.regatta_id, r.event_name, r.start_date, r.end_date,
                         c.club_abbrev, c.club_fullname''',
        '''                       MAX(rb.block_id) AS class_block_id,
                       MAX(rb.fleet_label) AS fleet_label,
                       MAX(rb.class_canonical) AS class_canonical,
                       (
                         SELECT COUNT(*)::int FROM regatta_blocks rbx
                         WHERE rbx.regatta_id = r.regatta_id
                       ) AS parent_block_count
                FROM regatta_blocks rb
                JOIN regattas r ON r.regatta_id = rb.regatta_id
                LEFT JOIN results res ON res.block_id = rb.block_id
                LEFT JOIN clubs c ON c.club_id = r.host_club_id
                WHERE rb.class_id = %s
                  AND COALESCE(r.end_date, r.start_date) >= CURRENT_DATE
                GROUP BY r.regatta_id, r.event_name, r.start_date, r.end_date,
                         c.club_abbrev, c.club_fullname''',
    ),
    (
        '''                if _nblocks > 1 and ":" in _bid:
                    _tail = _bid.split(":", 1)[1].strip()
                    if _tail:
                        _rid = f"{parent}-{_tail}"''',
        '''                if _nblocks > 1 and ":" in _bid and _regatta_is_upcoming_or_happening(
                    r.get("end_date"), r.get("start_date")
                ):
                    _tail = _fleet_shell_public_tail(
                        _bid,
                        fleet_label=r.get("fleet_label"),
                        class_canonical=r.get("class_canonical") or class_name,
                        class_name=class_name,
                    )
                    if _tail:
                        _rid = f"{parent}-{_tail}"''',
    ),
]


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    text = path.read_text(encoding="utf-8")
    for i, (old, new) in enumerate(REPLACEMENTS, start=1):
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: replacement {i}: expected 1 match, found {n} for:\n{old[:220]!r}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path, "replacements", len(REPLACEMENTS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
