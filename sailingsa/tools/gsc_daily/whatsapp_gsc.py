"""Compact GOOGLE/GSC block for the existing 10:30 WhatsApp daily report."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .classify import HUMAN, OK, REAL, STALE
from .seo_health import health_lines


def compact_text(payload: dict) -> str:
    auth = payload.get("auth") or "PENDING"
    lines = ["GOOGLE/GSC"]
    lines.append(f"Auth: {auth} | {payload.get('property') or 'sc-domain:sailingsa.co.za'}")
    fx = payload.get("autofix") or {}
    if payload.get("apply_fixes"):
        still = fx.get("still_broken") or []
        lines.append(
            f"Fixes: ON | did {', '.join(fx.get('actions') or ['none'])}"
            + (f" | still {', '.join(still)}" if still else " | contract clear")
        )
    else:
        lines.append("Fixes: OFF")
    sm = payload.get("sitemap") or {}
    if sm:
        lines.append(
            f"Sitemap: submitted {sm.get('submitted', '?')} | "
            f"last download {sm.get('last_downloaded') or 'n/a'} | "
            f"errors {sm.get('errors', 0)} warnings {sm.get('warnings', 0)}"
        )
    else:
        lines.append("Sitemap: not available from API this run")
    sa = payload.get("search_analytics") or {}
    if sa:
        lines.append(
            f"Search 7d: {int(sa.get('clicks') or 0)} clicks / "
            f"{int(sa.get('impressions') or 0)} impr (traffic, not index counts)"
        )
    insp = payload.get("inspect_summary") or {}
    n = insp.get("n") or 0
    if n:
        lines.append(
            f"Inspected {n} URLs: Google PASS {insp.get('pass', 0)} / "
            f"not-indexed {insp.get('not_indexed', 0)} (sample, NOT Page Indexing totals)"
        )
    else:
        lines.append("URL Inspection: skipped (no OAuth or budget 0)")
    cls = payload.get("classes") or {}
    lines.append(
        f"Live: REAL {cls.get(REAL, 0)} | STALE {cls.get(STALE, 0)} | "
        f"OK {cls.get(OK, 0)} | HUMAN {cls.get(HUMAN, 0)}"
    )
    delta = payload.get("delta") or {}
    lines.append(
        f"vs yesterday: REAL {delta.get('real_delta', 'n/a')} | "
        f"new REAL {delta.get('new_real', 0)} | now STALE {delta.get('now_stale', 0)}"
    )
    lines.append(
        "Page Indexing cohort totals: unavailable via official API — Mac fallback"
    )
    attn = payload.get("attention") or []
    health = payload.get("seo_health") or {}
    if health:
        # Compact: reuse stored seo_health plus alerts already in attention.
        fake = {
            "googlebot": health.get("googlebot") or {},
            "sitemap": health.get("sitemap") or {},
            "indexing": health.get("indexing") or {},
            "canonical_live_mismatches": [{}] * int(health.get("live_canonical_mismatches") or 0),
            "performance": health.get("performance") or {},
            "alerts": health.get("alerts") or [],
        }
        lines.extend(health_lines(fake))
    if attn:
        lines.append("ATTN:")
        for item in attn[:8]:
            lines.append(f"- {item}")
    elif not (health.get("alerts") or []):
        lines.append("HEALTHY: no new REAL defects; SEO health checks quiet")
    return "\n".join(lines)


def write_whatsapp(dest: Path, payload: dict) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    txt = compact_text(payload)
    (dest / "whatsapp_gsc.txt").write_text(txt + "\n", encoding="utf-8")
    (dest / "whatsapp_gsc.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    latest = dest.parent / "whatsapp_gsc.txt"
    latest.write_text(txt + "\n", encoding="utf-8")
    (dest.parent / "whatsapp_gsc.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return dest / "whatsapp_gsc.txt"


def class_counts(probes: list[dict]) -> dict:
    c = Counter(p.get("classification") or HUMAN for p in probes)
    return dict(c)
