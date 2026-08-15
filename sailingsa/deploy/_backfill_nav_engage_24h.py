#!/usr/bin/env python3
"""One-shot: stamp clicked (+ scrolled if dwell>=3) on prior hit when path changes."""
from __future__ import annotations

import os

import psycopg2

DB = os.environ.get("DB_URL") or os.environ.get("DATABASE_URL")
if not DB:
    raise SystemExit("Set DB_URL")


def main() -> None:
    conn = psycopg2.connect(DB)
    cur = conn.cursor()
    cur.execute(
        """
        WITH ordered AS (
          SELECT hit_id, ip_address, path, engagement, dwell_seconds, occurred_at,
                 LEAD(path) OVER (PARTITION BY ip_address ORDER BY occurred_at, hit_id) AS next_path
          FROM public.public_page_hits
          WHERE occurred_at > NOW() - INTERVAL '24 hours'
            AND ip_address IS NOT NULL AND TRIM(ip_address) <> ''
        ),
        need AS (
          SELECT hit_id, engagement, dwell_seconds, path, next_path
          FROM ordered
          WHERE next_path IS NOT NULL
            AND NULLIF(TRIM(path), '') IS NOT NULL
            AND split_part(path, '?', 1) <> split_part(next_path, '?', 1)
        )
        SELECT hit_id, COALESCE(engagement, ''), dwell_seconds FROM need
        """
    )
    rows = cur.fetchall() or []
    updated = 0
    for hit_id, eng, dwell in rows:
        toks = []
        for part in str(eng or "").replace(";", ",").split(","):
            t = part.strip().lower()
            if t in ("scrolled", "scroll", "scroll50", "scroll_half"):
                t = "scrolled"
            elif t in ("searched", "search"):
                t = "searched"
            elif t in ("clicked", "click", "tap"):
                t = "clicked"
            else:
                continue
            if t not in toks:
                toks.append(t)
        changed = False
        if "clicked" not in toks:
            toks.append("clicked")
            changed = True
        if "scrolled" not in toks and dwell is not None and int(dwell) >= 3:
            toks.append("scrolled")
            changed = True
        if not changed:
            continue
        cur.execute(
            "UPDATE public.public_page_hits SET engagement = %s WHERE hit_id = %s",
            (",".join(toks), hit_id),
        )
        updated += 1
    conn.commit()
    print(f"OK stamped nav engage on {updated} of {len(rows)} prior hits")
    conn.close()


if __name__ == "__main__":
    main()
