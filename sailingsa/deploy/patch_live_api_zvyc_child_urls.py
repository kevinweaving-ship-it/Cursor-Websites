#!/usr/bin/env python3
"""Surgical live api.py patches for ZVYC Cape Classic 2026 child URLs / class logos."""
from pathlib import Path
import sys

API = Path("/var/www/sailingsa/api/api.py")

REPLACEMENTS = [
    (
        '''    # ILCA fleet tails from block slugs
    if tail_slug in ("ilca-4-16", "ilca-4-7", "ilca-47", "ilca-4"):
        return "ILCA 4.7"''',
        '''    # ILCA fleet tails from block slugs (strip trailing -fleet; 4.7 used a 4-only tail)
    tail_slug = re.sub(r"-fleet$", "", tail_slug)
    if tail_slug in ("ilca-4-16", "ilca-4-7", "ilca-4.7", "ilca-47", "ilca-4"):
        return "ILCA 4.7"''',
    ),
    (
        '''            SELECT
                r.regatta_id,
                r.event_name AS regatta_name,
                r.regatta_id AS regatta_slug,
                r.start_date,
                r.end_date,
                COALESCE(r.end_date, r.start_date) AS event_date,
                COALESCE(c.club_abbrev, c.club_fullname) AS club_name,
                c.club_abbrev AS host_club_code,
                COUNT(DISTINCT res.result_id) AS fleet_size,''',
        '''            SELECT
                r.regatta_id,
                r.event_name AS regatta_name,
                r.regatta_id AS regatta_slug,
                MAX(rb.block_id) AS class_block_id,
                (
                    SELECT COUNT(*)::int FROM regatta_blocks rbx
                    WHERE rbx.regatta_id = r.regatta_id
                ) AS parent_block_count,
                r.start_date,
                r.end_date,
                COALESCE(r.end_date, r.start_date) AS event_date,
                COALESCE(c.club_abbrev, c.club_fullname) AS club_name,
                c.club_abbrev AS host_club_code,
                COUNT(DISTINCT res.result_id) AS fleet_size,''',
    ),
    (
            '''            _class_n = int(r["fleet_size"]) if r.get("fleet_size") is not None else None
            _event_n = int(r["event_entries"]) if r.get("event_entries") is not None else None
            regattas.append({
                "regatta_id": r.get("regatta_id"),
                "regatta_name": r.get("regatta_name") or "",
                "regatta_slug": r.get("regatta_slug") or "",''',
            '''            _class_n = int(r["fleet_size"]) if r.get("fleet_size") is not None else None
            _event_n = int(r["event_entries"]) if r.get("event_entries") is not None else None
            _rid = str(r.get("regatta_id") or "").strip()
            _slug = str(r.get("regatta_slug") or _rid).strip()
            try:
                _nblocks = int(r.get("parent_block_count") or 0)
            except (TypeError, ValueError):
                _nblocks = 0
            _bid = str(r.get("class_block_id") or "").strip()
            if _nblocks > 1 and _bid and ":" in _bid:
                _tail = _bid.split(":", 1)[1].strip()
                if _tail:
                    _rid = f"{str(r.get('regatta_id') or '').strip()}-{_tail}"
                    _slug = _rid
            regattas.append({
                "regatta_id": _rid,
                "regatta_name": r.get("regatta_name") or "",
                "regatta_slug": _slug,''',
    ),
    (
        '''        # 4) Clubs sailing this class: Club | Sailors | Races | Last regatta | Date (from results; sailors via result_crew when present)
        clubs_sailing_class = []''',
        '''        have_regatta_ids = {str(x.get("regatta_id") or "") for x in regattas} | {
            str(x.get("regatta_slug") or "") for x in regattas
        }
        try:
            cur.execute(
                """
                SELECT r.regatta_id, r.event_name AS regatta_name,
                       r.start_date, r.end_date,
                       COALESCE(r.end_date, r.start_date) AS event_date,
                       COALESCE(c.club_abbrev, c.club_fullname) AS club_name,
                       c.club_abbrev AS host_club_code,
                       COUNT(res.result_id)::int AS fleet_size,
                       (
                         SELECT COUNT(*)::int FROM results ra
                         WHERE ra.regatta_id = r.regatta_id AND ra.raced = TRUE
                       ) AS event_entries,
                       MAX(rb.races_sailed) AS races,
                       MAX(rb.block_id) AS class_block_id,
                       (
                         SELECT COUNT(*)::int FROM regatta_blocks rbx
                         WHERE rbx.regatta_id = r.regatta_id
                       ) AS parent_block_count
                FROM regatta_blocks rb
                JOIN regattas r ON r.regatta_id = rb.regatta_id
                LEFT JOIN results res ON res.block_id = rb.block_id
                LEFT JOIN clubs c ON c.club_id = r.host_club_id
                WHERE rb.class_id = %s
                GROUP BY r.regatta_id, r.event_name, r.start_date, r.end_date,
                         c.club_abbrev, c.club_fullname
                """,
                (class_id,),
            )
            for r in cur.fetchall() or []:
                parent = str(r.get("regatta_id") or "").strip()
                if not parent:
                    continue
                _bid = str(r.get("class_block_id") or "").strip()
                _rid = parent
                try:
                    _nblocks = int(r.get("parent_block_count") or 0)
                except (TypeError, ValueError):
                    _nblocks = 0
                if _nblocks > 1 and ":" in _bid:
                    _tail = _bid.split(":", 1)[1].strip()
                    if _tail:
                        _rid = f"{parent}-{_tail}"
                if parent in have_regatta_ids or _rid in have_regatta_ids:
                    continue
                _class_n = int(r["fleet_size"]) if r.get("fleet_size") is not None else None
                _event_n = int(r["event_entries"]) if r.get("event_entries") is not None else None
                _ev_logo = None
                try:
                    _ev_left, _ = _wc_regatta_header_icon_urls(parent, r.get("regatta_name"))
                    _ev_left = (_ev_left or "").strip()
                    if _ev_left:
                        _ev_logo = _ev_left
                except Exception:
                    _ev_logo = None
                regattas.append({
                    "regatta_id": _rid,
                    "regatta_name": r.get("regatta_name") or "",
                    "regatta_slug": _rid,
                    "start_date": _date_iso(r.get("start_date")),
                    "end_date": _date_iso(r.get("end_date")),
                    "event_date": _date_iso(r.get("event_date")),
                    "club_name": r.get("club_name"),
                    "club_code": (r.get("host_club_code") or "").strip() or None,
                    "club_logo_url": _club_logo_public_url((r.get("host_club_code") or "").strip()) if (r.get("host_club_code") or "").strip() else None,
                    "event_logo_url": _prefer_class_ssot_over_event_logo(class_name, class_logo_path, _ev_logo)
                    or class_logo_path,
                    "fleet_size": _class_n,
                    "class_entries": _class_n,
                    "event_entries": _event_n,
                    "races": int(r["races"]) if r.get("races") is not None else None,
                })
                have_regatta_ids.add(_rid)
                have_regatta_ids.add(parent)
            regattas.sort(
                key=lambda x: (str(x.get("end_date") or x.get("event_date") or ""), str(x.get("regatta_id") or "")),
                reverse=True,
            )
        except Exception as _open_fleet_exc:
            print(f"[class api] mixed fleet shell rows: {_open_fleet_exc}")

        # 4) Clubs sailing this class: Club | Sailors | Races | Last regatta | Date (from results; sailors via result_crew when present)
        clubs_sailing_class = []''',
    ),
]


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else API
    text = path.read_text(encoding="utf-8")
    for old, new in REPLACEMENTS:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"{path}: expected 1 match, found {n} for:\n{old[:180]!r}")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print("patched", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
