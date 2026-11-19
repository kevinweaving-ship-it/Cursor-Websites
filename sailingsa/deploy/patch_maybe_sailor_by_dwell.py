#!/usr/bin/env python3
"""Soft maybe-sailor hint: total dwell wins (then visits, then earliest).

Replaces reverse-alphabetical hit-count tiebreak that wrongly preferred Tim over Kevin.
"""
from __future__ import annotations

import py_compile
import shutil
from datetime import datetime, timezone
from pathlib import Path

API = Path("/var/www/sailingsa/api/api.py")

NEW_FN = '''def _public_likely_sailor_for_ip(cur, ip: str, current_path: str = "") -> dict:
    """Soft hint only: which /sailor/{slug} this IP lingered on most.

    Ranking (not an identity lock — unique visitor is always the IP):
      1) highest total dwell_seconds on that sailor
      2) more visits to that sailor
      3) earlier first visit (so a solid 1st page beats a later equal dwell)
    A 1st sailor with a bounce (very short dwell) loses to a later longer stay.
    Sailors often open themselves/family first and re-check — total dwell captures that.
    """
    out = {"name": "", "slug": "", "hits": 0, "sas_id": "", "label": "Public", "dwell_seconds": 0}
    ip = (ip or "").strip()
    if not ip:
        return out

    def _slug_from_path(pp: str) -> str:
        path_only = (str(pp or "").split("?", 1)[0] or "").strip()
        m = re.match(r"^/?sailor/([A-Za-z0-9\\-]+)", path_only, re.I)
        if m:
            slug = m.group(1).strip().lower()
        else:
            q = str(pp).split("?", 1)[1] if "?" in str(pp) else ""
            mq = re.search(r"(?:^|&)sailor=([A-Za-z0-9\\-]+)", q or "", re.I)
            slug = (mq.group(1).strip().lower() if mq else "")
        if not slug or slug.isdigit():
            return ""
        if slug.startswith(("clean-trail", "local-trail", "cleantrail")):
            return ""
        return slug

    # slug -> {hits, dwell, first_at}
    stats = {}
    try:
        cur.execute(
            """
            SELECT path, occurred_at, COALESCE(dwell_seconds, 0)::int AS dwell_seconds
            FROM public.public_page_hits
            WHERE ip_address = %s
              AND occurred_at > NOW() - INTERVAL '45 minutes'
            ORDER BY occurred_at ASC, hit_id ASC
            """,
            (ip,),
        )
        for row in cur.fetchall() or []:
            if isinstance(row, dict):
                pp = row.get("path") or ""
                occurred = row.get("occurred_at")
                dwell = int(row.get("dwell_seconds") or 0)
            else:
                pp, occurred, dwell = row[0], row[1], int(row[2] or 0)
            slug = _slug_from_path(pp)
            if not slug:
                continue
            st = stats.get(slug)
            if not st:
                stats[slug] = {"hits": 1, "dwell": max(0, dwell), "first_at": occurred}
            else:
                st["hits"] += 1
                st["dwell"] += max(0, dwell)
                if occurred is not None and (st["first_at"] is None or occurred < st["first_at"]):
                    st["first_at"] = occurred
    except Exception:
        stats = {}

    # Include current page if sailor and not yet in stats (live path, dwell unknown → 0)
    try:
        cp = _sanitize_session_path(current_path or "")
        slug = _slug_from_path(cp)
        if slug and slug not in stats:
            stats[slug] = {"hits": 1, "dwell": 0, "first_at": None}
    except Exception:
        pass

    if not stats:
        return out

    # Highest total dwell, then most visits, then earliest first visit.
    # first_at None sorts last among equals so DB rows beat synthetic current-path.
    def _rank_key(item):
        slug, st = item
        first = st.get("first_at")
        # Use string/isoformat for stable compare; missing → far future
        if first is None:
            first_key = "9999"
        else:
            first_key = first.isoformat() if hasattr(first, "isoformat") else str(first)
        return (-int(st.get("dwell") or 0), -int(st.get("hits") or 0), first_key)

    best_slug, best = sorted(stats.items(), key=_rank_key)[0]
    best_hits = int(best.get("hits") or 0)
    best_dwell = int(best.get("dwell") or 0)
    name, sas_id = _public_resolve_sailor_name(cur, best_slug)
    if not name:
        return out
    out.update(
        {
            "name": name,
            "slug": best_slug,
            "hits": best_hits,
            "dwell_seconds": best_dwell,
            "sas_id": sas_id,
            "label": name if name else "Public",
        }
    )
    return out


'''


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    shutil.copy2(API, API.with_suffix(f".bak-maybe-dwell-{stamp}"))
    text = API.read_text(encoding="utf-8")
    start = text.find("def _public_likely_sailor_for_ip")
    if start < 0:
        raise SystemExit("fn not found")
    end = text.find("\ndef _admin_public_users_full", start)
    if end < 0:
        raise SystemExit("end marker not found")
    if "highest total dwell_seconds on that sailor" in text[start:end]:
        print("already patched")
        return
    text = text[:start] + NEW_FN + text[end:]
    API.write_text(text, encoding="utf-8")
    py_compile.compile(str(API), doraise=True)
    print(f"OK patched _public_likely_sailor_for_ip (+{len(NEW_FN)} chars region)")


if __name__ == "__main__":
    main()
