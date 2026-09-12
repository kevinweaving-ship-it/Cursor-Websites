#!/usr/bin/env python3
"""Write stored product PDFs for closed events (parent + children).

Live / fluid events are skipped (generate-now on request).
Run on the live API host with the same PYTHONPATH as sailingsa-api.

  cd /var/www/sailingsa
  PYTHONPATH=/var/www/sailingsa/api:/var/www/sailingsa \
    /var/www/sailingsa/api/venv/bin/python3 \
    /var/www/sailingsa/deploy/generate_closed_event_product_pdfs.py
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime

ROOT = os.environ.get("SSA_ROOT", "/var/www/sailingsa")
# api.py lives in ROOT/api/api.py; sailingsa.backend lives in ROOT/sailingsa/.
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "api"))
os.chdir(os.path.join(ROOT, "api"))


def _today_za():
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Africa/Johannesburg")).date()
    except Exception:
        return datetime.utcnow().date()


def main() -> int:
    import api as api_mod
    from sailingsa.backend.regatta_stored_pdf import pdf_abs_path

    rebuild = getattr(api_mod, "_rebuild_regatta_stored_pdfs", None)
    if rebuild is None:
        raise SystemExit("api module is not live api.py (missing _rebuild_regatta_stored_pdfs)")

    today = _today_za()
    conn = api_mod.get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT r.regatta_id::text, r.end_date, r.start_date
        FROM regattas r
        WHERE POSITION(':' IN r.regatta_id::text) = 0
          AND EXISTS (
            SELECT 1 FROM results x
            WHERE x.regatta_id::text = r.regatta_id::text
          )
        ORDER BY COALESCE(r.end_date, r.start_date) DESC NULLS LAST
        """
    )
    rows = cur.fetchall()
    try:
        conn.close()
    except Exception:
        pass

    closed = []
    skipped_live = []
    for row in rows:
        if isinstance(row, dict):
            rid, end_d, start_d = row["regatta_id"], row["end_date"], row["start_date"]
        else:
            rid, end_d, start_d = row[0], row[1], row[2]
        rid = str(rid)
        raw = end_d or start_d
        if raw is None:
            closed.append(rid)
            continue
        d = raw.date() if hasattr(raw, "date") else raw
        try:
            if hasattr(d, "year") and d >= today:
                skipped_live.append(rid)
                continue
        except Exception:
            pass
        closed.append(rid)

    print(f"closed={len(closed)} skipped_live={len(skipped_live)} today={today}", flush=True)
    ok = fail = skip_exists = 0
    t0 = time.time()
    for i, rid in enumerate(closed, 1):
        parent = pdf_abs_path(rid)
        if parent.is_file() and parent.stat().st_size >= 500:
            skip_exists += 1
            if i % 50 == 0:
                print(f"[{i}/{len(closed)}] exists {rid}", flush=True)
            continue
        try:
            rebuild(rid)
            path = pdf_abs_path(rid)
            if path.is_file() and path.stat().st_size >= 500:
                ok += 1
                print(f"[{i}/{len(closed)}] wrote {rid} {path.stat().st_size}b", flush=True)
            else:
                fail += 1
                print(f"[{i}/{len(closed)}] EMPTY {rid}", flush=True)
        except Exception as exc:
            fail += 1
            print(f"[{i}/{len(closed)}] FAIL {rid}: {exc}", flush=True)
    print(
        f"done ok={ok} already={skip_exists} fail={fail} sec={time.time()-t0:.0f}",
        flush=True,
    )
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
