#!/usr/bin/env python3
"""One named-event edition row per calendar year (not per class/host leg)."""
from pathlib import Path
import sys

path = Path(sys.argv[1])
t = path.read_text(encoding="utf-8")

start = t.find("def _edition_dedupe_key(rg: dict[str, Any]) -> str:")
end = t.find("def _clean_aka_names(")
if start < 0 or end < 0 or end <= start:
    raise SystemExit(f"anchors not found start={start} end={end}")

NEW = '''def _edition_dedupe_key(rg: dict[str, Any]) -> str:
    """Stable key for named-event editions - one row per calendar year."""
    ey = edition_year_of(rg)
    if ey:
        return f"year|{ey}"
    rid = str(rg.get("regatta_id") or "").strip()
    if rid:
        return f"rid|{rid}"
    host = str(rg.get("host_abbrev") or "").strip().upper()
    name = str(rg.get("event_name") or "").strip().lower()
    return f"id|{name}|host|{host}|{id(rg)}"


def _edition_row_score(rg: dict[str, Any]) -> tuple:
    """Prefer real result rows with host + dates over class-leg / placeholder years."""
    closed = 1 if rg.get("closed") else 0
    host = 1 if str(rg.get("host_abbrev") or "").strip() else 0
    dl = str(rg.get("date_label") or "").strip()
    real_date = 1 if dl and not re.fullmatch(r"(19|20)\d{2}", dl) else 0
    rid = 1 if str(rg.get("regatta_id") or "").strip() else 0
    name = str(rg.get("event_name") or "").lower()
    class_leg_penalty = 0
    for tok in (
        "ilca", "optimist", "hobie", "29er", "finn", "505", "stadt", "rs tera", "dabchick", "mirror",
    ):
        if tok in name:
            class_leg_penalty = 1
            break
    return (closed, host, real_date, rid, -class_leg_penalty, -len(name))


def _one_row_per_edition_year(regattas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per calendar year for a named-event series (parent edition only)."""
    best: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for rg in regattas:
        key = _edition_dedupe_key(rg)
        if key not in best:
            best[key] = dict(rg)
            order.append(key)
            continue
        cur = best[key]
        if _edition_row_score(rg) > _edition_row_score(cur):
            best[key] = dict(rg)
    return [best[k] for k in order]


'''

if 'return f"year|{ey}"' in t[start:end]:
    print("already patched")
else:
    path.write_text(t[:start] + NEW + t[end:], encoding="utf-8")
    print("patched", path)
