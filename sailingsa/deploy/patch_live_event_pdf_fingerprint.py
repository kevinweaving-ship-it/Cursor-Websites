#!/usr/bin/env python3
"""Point live api.py fingerprint + rebuild stamp at regatta_pdf_diff.

The old fingerprint called q(sql, (rid, rid)). Live q() is q(sql, *args),
so that always failed, .event-truth.sha was never written, and every
/results.pdf hit for a live event rebuilt.

Run on the live host:
  python3 /var/www/sailingsa/deploy/patch_live_event_pdf_fingerprint.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

OLD_FP = '''def _event_truth_fingerprint(regatta_id: str) -> str:
    """Scores, boats, and fleets — anything Event URL shows."""
    rid = str(regatta_id or "").strip()
    if not rid:
        return ""
    try:
        rows = q(
            """
            SELECT md5(
              COALESCE((
                SELECT string_agg(rb.block_id::text, ',' ORDER BY rb.block_id)
                FROM regatta_blocks rb
                WHERE rb.regatta_id::text = %s
              ), '')
              || '||' ||
              COALESCE((
                SELECT string_agg(
                  r.result_id::text || ':' ||
                  COALESCE(r.sail_number,'') || ':' ||
                  COALESCE(r.helm_name,'') || ':' ||
                  COALESCE(r.rank::text,'') || ':' ||
                  COALESCE(r.total_points_raw::text,'') || ':' ||
                  COALESCE(r.nett_points_raw::text,'') || ':' ||
                  COALESCE(r.races_sailed::text,'') || ':' ||
                  COALESCE(r.race_scores::text,'') || ':' ||
                  COALESCE(r.block_id::text,''),
                  '|' ORDER BY r.result_id
                )
                FROM results r
                WHERE r.regatta_id::text = %s
              ), '')
            ) AS fp
            """,
            (rid, rid),
        )
        return str((rows[0] or {}).get("fp") or "") if rows else ""
    except Exception:
        return ""
'''

NEW_FP = '''def _event_truth_fingerprint(regatta_id: str) -> str:
    """Scores, boats, fleets, and the Results-are line — anything Event URL shows."""
    rid = str(regatta_id or "").strip()
    if not rid:
        return ""
    try:
        from sailingsa.backend.regatta_pdf_diff import event_truth_fingerprint
        return event_truth_fingerprint(q, rid)
    except Exception:
        return ""
'''

OLD_RETURN = '''    return write_event_pdfs(
        slug=rid,
        event_name=(ev_name or rid).strip() or rid,
        host=host,
        status_line=status_line,
        sheet_url="https://sailingsa.co.za/regatta/" + rid,
        fleets=fleet_jobs,
        left_logo=left_logo,
        right_logo=right_logo,
    )
'''

NEW_RETURN = '''    written = write_event_pdfs(
        slug=rid,
        event_name=(ev_name or rid).strip() or rid,
        host=host,
        status_line=status_line,
        sheet_url="https://sailingsa.co.za/regatta/" + rid,
        fleets=fleet_jobs,
        left_logo=left_logo,
        right_logo=right_logo,
    )
    try:
        from sailingsa.backend.regatta_pdf_diff import event_truth_fingerprint, write_stamp
        fp = event_truth_fingerprint(q, rid)
        if fp:
            write_stamp(rid, fp)
    except Exception as exc:
        print(f"[regatta-pdf] stamp {rid}: {exc}", flush=True)
    return written
'''


def main() -> int:
    text = API.read_text(encoding="utf-8")
    changed = False
    if "from sailingsa.backend.regatta_pdf_diff import event_truth_fingerprint" in text and "write_stamp" in text:
        print("already_patched")
        return 0
    if OLD_FP in text:
        text = text.replace(OLD_FP, NEW_FP, 1)
        changed = True
    elif NEW_FP in text:
        print("fingerprint_already")
    else:
        print("OLD_FP_MISSING")
        return 1
    if OLD_RETURN in text:
        text = text.replace(OLD_RETURN, NEW_RETURN, 1)
        changed = True
    elif "write_stamp(rid, fp)" in text:
        print("stamp_already")
    else:
        print("OLD_RETURN_MISSING")
        return 1
    if not changed:
        print("already_patched")
        return 0
    subprocess.run(["chattr", "-i", str(API)], check=False)
    API.write_text(text, encoding="utf-8")
    subprocess.run(["chattr", "+i", str(API)], check=False)
    print("patched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
