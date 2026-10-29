"""Event rich-results: pull GSC ourselves, audit live markup, do not paste.

Official Search Console API has no Enhancement report table (the Event
'Why items are invalid' grid). What we can do:

  1. Audit every sitemap /regatta/ page's JSON-LD (no Google quota)
  2. Read richResultsResult from URL Inspection we already run
  3. Inspect a few extra Event URLs (including class sheets)

Do not click Validate Fix. Do not invent offers/performer.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .config import SITE

SAST = ZoneInfo("Africa/Johannesburg")
LOCAL = "http://127.0.0.1:8000"
HOST = "sailingsa.co.za"
WEB_ROOT = Path("/var/www/sailingsa")
CLASS_AUDIT_CAP = 24
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
EVENT_TYPES = frozenset({"Event", "SportsEvent"})
REQUIRED = ("name", "startDate", "location")
# Concert/ticket fields. Sailing events do not have these; do not invent.
SKIP_WARN = frozenset({"offers", "performer"})
CLASS_HREF = re.compile(r'href="(/regatta/[^"]+/class-[^"]+)"')


def events_from_html(html: str) -> list[dict]:
    out: list[dict] = []
    for raw in LD_RE.findall(html or ""):
        try:
            data = json.loads(raw)
        except Exception:
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            item = stack.pop()
            if not isinstance(item, dict):
                continue
            typ = item.get("@type")
            types = typ if isinstance(typ, list) else [typ]
            if any(t in EVENT_TYPES for t in types if t):
                out.append(item)
            for val in item.values():
                if isinstance(val, dict):
                    stack.append(val)
                elif isinstance(val, list):
                    stack.extend(x for x in val if isinstance(x, dict))
    return out


def classify_event(item: dict) -> list[dict]:
    issues: list[dict] = []
    if not (item.get("name") or "").strip():
        issues.append({"field": "name", "severity": "ERROR"})
    if not item.get("startDate"):
        issues.append({"field": "startDate", "severity": "ERROR"})
    loc = item.get("location")
    if not loc:
        issues.append({"field": "location", "severity": "ERROR"})
    elif isinstance(loc, dict) and not loc.get("address"):
        issues.append({"field": "location.address", "severity": "ERROR"})
    if not item.get("endDate"):
        issues.append({"field": "endDate", "severity": "WARNING"})
    if not (item.get("description") or "").strip():
        issues.append({"field": "description", "severity": "WARNING"})
    if not item.get("eventStatus"):
        issues.append({"field": "eventStatus", "severity": "WARNING"})
    if not item.get("image"):
        issues.append({"field": "image", "severity": "WARNING"})
    org = item.get("organizer")
    if not org:
        issues.append({"field": "organizer", "severity": "WARNING"})
    elif isinstance(org, dict) and not org.get("url"):
        issues.append({"field": "organizer.url", "severity": "WARNING"})
    if not item.get("offers"):
        issues.append({"field": "offers", "severity": "SKIP"})
    if not item.get("performer"):
        issues.append({"field": "performer", "severity": "SKIP"})
    return issues


def issues_from_inspect(result: dict) -> list[dict]:
    rich = (result or {}).get("richResultsResult") or {}
    rows: list[dict] = []
    for detected in rich.get("detectedItems") or []:
        rtype = detected.get("richResultType") or ""
        for item in detected.get("items") or []:
            for iss in item.get("issues") or []:
                rows.append(
                    {
                        "type": rtype,
                        "name": item.get("name") or "",
                        "message": iss.get("issueMessage") or "",
                        "severity": (iss.get("severity") or "").upper(),
                    }
                )
    return rows


def summarize_inspections(inspections: dict[str, dict]) -> dict:
    errors: Counter[str] = Counter()
    warnings: Counter[str] = Counter()
    urls_fail: list[dict] = []
    for url, result in (inspections or {}).items():
        if not isinstance(result, dict):
            continue
        rows = issues_from_inspect(result)
        ev_err = [r for r in rows if r["type"] == "Events" and r["severity"] == "ERROR"]
        ev_warn = [r for r in rows if r["type"] == "Events" and r["severity"] == "WARNING"]
        for r in ev_err:
            errors[r["message"]] += 1
        for r in ev_warn:
            warnings[r["message"]] += 1
        if ev_err:
            urls_fail.append({"url": url, "errors": ev_err, "warnings": ev_warn})
    return {
        "inspected": len(inspections or {}),
        "event_error_urls": len(urls_fail),
        "errors": dict(errors),
        "warnings": dict(warnings),
        "fail_urls": urls_fail[:20],
        "note": (
            "GSC Enhancement table is not in the official API. "
            "These counts come from URL Inspection richResultsResult."
        ),
    }


def audit_html(url: str, html: str) -> dict:
    events = events_from_html(html)
    issues: list[dict] = []
    for ev in events:
        for iss in classify_event(ev):
            issues.append({"name": ev.get("name") or "", **iss})
    return {
        "url": url,
        "n_event": len(events),
        "errors": [i for i in issues if i.get("severity") == "ERROR"],
        "warnings": [i for i in issues if i.get("severity") == "WARNING"],
        "skipped": [i for i in issues if i.get("severity") == "SKIP"],
        "class_hrefs": CLASS_HREF.findall(html)[:12],
    }


def render_lines(payload: dict) -> list[str]:
    live = payload.get("live") or {}
    gsc = payload.get("gsc") or {}
    lines = [
        "EVENT RICH RESULTS (pulled here — do not paste GSC)",
        f"Live Event items: {live.get('items', 0)} | "
        f"pages with Event ERROR: {live.get('error_pages', 0)} | "
        f"pages audited: {live.get('pages', 0)}",
    ]
    live_err = live.get("errors") or {}
    if live_err:
        bits = [f"{k} {v}" for k, v in sorted(live_err.items())]
        lines.append("Live ERROR fields: " + " | ".join(bits))
    else:
        lines.append("Live ERROR fields: none (required name/startDate/location present)")
    skip = live.get("skipped") or {}
    if skip:
        lines.append(
            "Not invented: "
            + ", ".join(sorted(skip))
            + " (concert/ticket fields — sailing events)"
        )
    gsc_err = gsc.get("errors") or {}
    if gsc.get("inspected"):
        if gsc_err:
            bits = [f"{k} {v}" for k, v in sorted(gsc_err.items())]
            lines.append(
                f"GSC inspect Event ERRORS ({gsc.get('event_error_urls', 0)} URLs): "
                + " | ".join(bits)
            )
        else:
            lines.append(
                f"GSC inspect: {gsc.get('inspected')} URLs, 0 Event ERRORS"
            )
    for row in (live.get("error_urls") or [])[:6]:
        fields = ",".join(sorted({i.get("field") for i in row.get("errors") or []}))
        lines.append(f"  live {fields} {row.get('url')}")
    for row in (gsc.get("fail_urls") or [])[:6]:
        lines.append(f"  gsc {(row.get('url') or '').replace(SITE, '')}")
    return lines


def write_rich_results(dest: Path, payload: dict) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "rich_results.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (dest / "rich_results.txt").write_text("\n".join(render_lines(payload)) + "\n")
    return path


def _count_fields(rows: list[dict]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for r in rows:
        c[r.get("field") or r.get("message") or "?"] += 1
    return dict(c)


def from_audit_rows(rows: list[dict], inspections: dict[str, dict] | None = None) -> dict:
    errors: list[dict] = []
    warnings: list[dict] = []
    skipped: list[dict] = []
    error_urls: list[dict] = []
    items = 0
    class_hrefs: list[str] = []
    for row in rows:
        items += int(row.get("n_event") or 0)
        errors.extend(row.get("errors") or [])
        warnings.extend(row.get("warnings") or [])
        skipped.extend(row.get("skipped") or [])
        if row.get("errors"):
            error_urls.append({"url": row.get("url"), "errors": row.get("errors")})
        class_hrefs.extend(row.get("class_hrefs") or [])
    return {
        "as_of": datetime.now(SAST).isoformat(),
        "note": (
            "Enhancement report totals are not in the official API. "
            "Live audit is the source of truth; GSC inspect confirms Google's view."
        ),
        "live": {
            "pages": len(rows),
            "items": items,
            "error_pages": len(error_urls),
            "errors": _count_fields(errors),
            "warnings": _count_fields(warnings),
            "skipped": _count_fields(skipped),
            "error_urls": error_urls[:20],
            "class_href_sample": sorted(set(class_hrefs))[:20],
        },
        "gsc": summarize_inspections(inspections or {}),
    }


def _fetch_local(path: str) -> str:
    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        LOCAL + path,
        headers={
            "User-Agent": "SailingSA-GSC-Daily/1.0",
            "Host": HOST,
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": HOST,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return (e.read().decode("utf-8", "replace") if e.fp else "") or ""
    except Exception:
        return ""


def _sitemap_regatta_urls(web_root: Path) -> list[str]:
    xml = web_root / "sitemap-regattas.xml"
    if not xml.is_file():
        return []
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml.read_text(encoding="utf-8"))


def audit_web_root(
    web_root: Path | None = None,
    *,
    fetch=None,
    inspections: dict[str, dict] | None = None,
    dest: Path | None = None,
) -> dict:
    root = web_root or WEB_ROOT
    getter = fetch or _fetch_local
    rows: list[dict] = []
    class_seen: set[str] = set()
    for url in _sitemap_regatta_urls(root):
        path = urlparse(url).path or "/"
        html = getter(path)
        row = audit_html(url, html)
        rows.append(row)
        for href in row.get("class_hrefs") or []:
            if href in class_seen or len(class_seen) >= CLASS_AUDIT_CAP:
                continue
            class_seen.add(href)
            rows.append(audit_html(SITE + href, getter(href)))
    return run(rows=rows, inspections=inspections, dest=dest)
