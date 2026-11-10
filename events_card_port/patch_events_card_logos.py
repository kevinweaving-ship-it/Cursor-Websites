#!/usr/bin/env python3
"""Live-only: attach event logos on /events coloured cards (same path as landing logo_url)."""
from pathlib import Path
import sys

path = Path(sys.argv[1])
t = path.read_text(encoding="utf-8")

fn = '''
def _attach_events_page_card_logos(cards: list, cur=None) -> None:
    """Fill event_logo_url for coloured cards — past has-results, then upcoming expect-results."""
    if not cards:
        return
    targets = []
    for c in cards:
        if not (c.get("result_yes") or c.get("expect_results")):
            continue
        if str(c.get("event_logo_url") or c.get("image_url") or "").strip():
            continue
        targets.append(c)
    if not targets:
        return
    class_logo_by_rid: dict[str, str] = {}
    icon_rids: set[str] = set()
    for c in targets:
        rid = str(c.get("regatta_id") or "").strip()
        if rid:
            try:
                icon_rids.add(_regatta_header_icon_source_regatta_id(rid))
            except Exception:
                icon_rids.add(rid)
    if icon_rids and cur is not None:
        try:
            cur.execute(
                """
                SELECT DISTINCT ON (rb.regatta_id)
                       rb.regatta_id,
                       NULLIF(btrim(cl.logo_path), '') AS logo_path
                FROM regatta_blocks rb
                LEFT JOIN classes cl ON cl.class_id = rb.class_id
                WHERE rb.regatta_id = ANY(%s)
                ORDER BY rb.regatta_id, rb.block_id
                """,
                (list(icon_rids),),
            )
            for row in cur.fetchall() or []:
                rrid = str(row.get("regatta_id") or "").strip()
                lp = str(row.get("logo_path") or "").strip()
                if rrid and lp:
                    class_logo_by_rid[rrid] = lp
        except Exception:
            try:
                if cur is not None:
                    cur.connection.rollback()
            except Exception:
                pass
    for c in targets:
        rid = str(c.get("regatta_id") or "").strip()
        rname = str(c.get("event_name") or c.get("display_title") or "").strip()
        logo = None
        if rid:
            try:
                logo = _regatta_card_event_logo_url(
                    rid, rname, cur=cur, class_logo_by_rid=class_logo_by_rid or None
                )
            except Exception:
                logo = None
        if not logo:
            try:
                logo, _href = _catalogue_regatta_left_logo(rid, rname, cur=cur)
                if logo:
                    logo = _public_artwork_url(logo)
            except Exception:
                logo = None
        if not logo:
            try:
                named = _event_logo_from_named_rules(rid, rname)
                if named:
                    logo = _public_artwork_url(named)
            except Exception:
                logo = None
        if logo:
            c["event_logo_url"] = logo

'''

wire = '''        try:
            _attach_events_page_card_logos(out["past"], cur)
            _attach_events_page_card_logos(out.get("live") or [], cur)
            _attach_events_page_card_logos(out["upcoming"], cur)
        except Exception as _logo_err:
            print(f"[events] card logos: {_logo_err}", flush=True)
        out["past"] = _sort_past_event_cards(out["past"])'''

if "_attach_events_page_card_logos" not in t:
    anchor = "def _attach_regatta_search_card_logos(rows: list, cur) -> None:"
    if anchor not in t:
        raise SystemExit("anchor missing: _attach_regatta_search_card_logos")
    t = t.replace(anchor, fn + "\n" + anchor, 1)
    print("inserted _attach_events_page_card_logos")
else:
    # Upgrade existing helper to include expect_results if still past-only
    old_tgt = "        if not c.get(\"result_yes\"):\n            continue"
    new_tgt = "        if not (c.get(\"result_yes\") or c.get(\"expect_results\")):\n            continue"
    if old_tgt in t:
        t = t.replace(old_tgt, new_tgt, 1)
        print("upgraded targets to include expect_results")
    print("helpers already present")

if "_attach_events_page_card_logos(out[\"upcoming\"]" in t:
    print("wire already includes upcoming")
elif "_attach_events_page_card_logos(out[\"past\"]" in t:
    old_wire = '''        try:
            _attach_events_page_card_logos(out["past"], cur)
        except Exception as _logo_err:
            print(f"[events] card logos: {_logo_err}", flush=True)
        out["past"] = _sort_past_event_cards(out["past"])'''
    if old_wire in t:
        t = t.replace(old_wire, wire)
        print("upgraded wire to past+live+upcoming")
    else:
        print("wire present (manual check)")
else:
    old = '        out["past"] = _sort_past_event_cards(out["past"])'
    if t.count(old) < 1:
        raise SystemExit("wire anchor missing")
    t = t.replace(old, wire, 1)
    if t.count(old) >= 1:
        t = t.replace(old, wire, 1)
    print("wired _get_upcoming_events + type filter")

path.write_text(t, encoding="utf-8")
print("done", path)
