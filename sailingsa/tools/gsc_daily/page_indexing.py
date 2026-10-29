"""GSC 'Why pages aren't indexed' — snapshot + live family probes.

Official Search Console API has no Page Indexing report (no cohort
totals, example lists, or Validate Fix). Do not click Validate Fix.

The counts are the sc-domain:sailingsa.co.za snapshot Kevin pasted
2026-10-29. They are excluded/junk + selection, not 6,000 good pages
waiting. Live probes check that the URL families behind each reason
still behave as we intend.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .config import SITE

SAST = ZoneInfo("Africa/Johannesburg")
UA = "SailingSA-GSC-Daily/1.0"
CTX = ssl.create_default_context()

SNAPSHOT_DATE = "2026-10-29"
GSC_PAGES = (
    "https://search.google.com/search-console/index"
    "?resource_id=sc-domain%3Asailingsa.co.za"
)

# Website-source rows can shrink as Google recrawls. Google-systems rows
# are selection. action=keep means the live response is correct.
SNAPSHOT = [
    {
        "key": "page_with_redirect",
        "label": "Page with redirect",
        "source": "website",
        "pages": 3795,
        "action": "keep",
        "meaning": (
            "Old aliases we 301: /sailor/{sas-id}, /sailor/{name}-{id}, "
            "/class/{id}-{slug}, uppercase /club/, old /regatta slugs, "
            "www/http, /home, /regatta → /events."
        ),
    },
    {
        "key": "not_found_404",
        "label": "Not found (404)",
        "source": "website",
        "pages": 1199,
        "action": "keep",
        "meaning": (
            "Dead or junk URLs: /sailor/unknown, boat-as-sailor slugs, "
            "gone events, scanner paths (.env, wp-config). Stay 404."
        ),
    },
    {
        "key": "duplicate_no_canonical",
        "label": "Duplicate without user-selected canonical",
        "source": "website",
        "pages": 408,
        "action": "fix",
        "meaning": (
            "/boats and /boat/{slug} 200 with no rel=canonical. Other "
            "thin 200s without a canonical tag."
        ),
    },
    {
        "key": "excluded_noindex",
        "label": "Excluded by ‘noindex’ tag",
        "source": "website",
        "pages": 337,
        "action": "keep",
        "meaning": "Admin/test/soft-fail HTML. Stay noindex.",
    },
    {
        "key": "blocked_robots",
        "label": "Blocked by robots.txt",
        "source": "website",
        "pages": 299,
        "action": "keep",
        "meaning": (
            "/api/ (except /api/og/ and /api/club-logo/), /auth/, /admin/, "
            "/login, /test/, /dev-1, /signup.html, /profiles."
        ),
    },
    {
        "key": "alternative_canonical",
        "label": "Alternative page with proper canonical tag",
        "source": "website",
        "pages": 143,
        "action": "keep",
        "meaning": "/index.html and /temp-landing 200 with canonical to /.",
    },
    {
        "key": "soft_404",
        "label": "Soft 404",
        "source": "website",
        "pages": 59,
        "action": "watch",
        "meaning": "Thin 200s Google treats as empty (e.g. /class/505).",
    },
    {
        "key": "server_error_5xx",
        "label": "Server error (5xx)",
        "source": "website",
        "pages": 45,
        "action": "watch",
        "meaning": "Historical API restarts. Current Googlebot logs: 0 5xx.",
    },
    {
        "key": "forbidden_403",
        "label": "Blocked due to access forbidden (403)",
        "source": "website",
        "pages": 12,
        "action": "keep",
        "meaning": "/admin and similar. Stay 403.",
    },
    {
        "key": "other_4xx",
        "label": "Blocked due to other 4xx issue",
        "source": "website",
        "pages": 0,
        "action": "watch",
        "meaning": "Count was incomplete on the pasted GSC table.",
    },
    {
        "key": "redirect_error",
        "label": "Redirect error",
        "source": "website",
        "pages": 3,
        "action": "watch",
        "meaning": "Rare multi-hop old slugs. Chains now end 200.",
    },
    {
        "key": "crawled_not_indexed",
        "label": "Crawled - currently not indexed",
        "source": "google",
        "pages": 829,
        "action": "wait",
        "meaning": (
            "Fetched and allowed, not selected. Mostly sailor profiles "
            "and some class/club hubs. Quality, not a crawl block."
        ),
    },
    {
        "key": "google_chose_canonical",
        "label": "Duplicate, Google chose different canonical than user",
        "source": "google",
        "pages": 484,
        "action": "wait",
        "meaning": (
            "We 301 + emit lowercase /club/{code}; Google still prefers "
            "an old uppercase URL until recrawl."
        ),
    },
    {
        "key": "discovered_not_indexed",
        "label": "Discovered – currently not indexed",
        "source": "google",
        "pages": 104,
        "action": "wait",
        "meaning": "Validation already Passed. Queue is shrinking.",
    },
]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _hit(url: str) -> dict:
    opener = urllib.request.build_opener(
        NoRedirect, urllib.request.HTTPSHandler(context=CTX)
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with opener.open(req, timeout=20) as resp:
            body = resp.read(8000)
            return {
                "status": resp.status,
                "location": resp.headers.get("Location") or "",
                "body": body,
                "xrobots": resp.headers.get("X-Robots-Tag") or "",
            }
    except urllib.error.HTTPError as e:
        body = e.read(4000) if e.fp else b""
        return {
            "status": e.code,
            "location": e.headers.get("Location") or "",
            "body": body,
            "xrobots": e.headers.get("X-Robots-Tag") or "",
        }
    except Exception as e:
        return {"status": 0, "location": "", "body": b"", "xrobots": "", "error": f"{type(e).__name__}: {e}"}


def _has_canonical(body: bytes) -> str:
    html = body.decode("utf-8", "replace")
    import re

    m = re.search(r'rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', html, re.I)
    if not m:
        m = re.search(r'href=["\']([^"\']+)["\'][^>]*rel=["\']canonical["\']', html, re.I)
    return m.group(1) if m else ""


def _loc_path(location: str) -> str:
    if not location:
        return ""
    if location.startswith("/"):
        return location.split("?", 1)[0]
    return urlparse(location).path or ""


def expect_redirect(row: dict, want_path: str | None = None) -> bool:
    if int(row.get("status") or 0) not in (301, 302, 307, 308):
        return False
    if not want_path:
        return True
    return _loc_path(row.get("location") or "") == want_path or (
        _loc_path(row.get("location") or "").rstrip("/") == want_path.rstrip("/")
    )


def expect_status(code: int) -> Callable[[dict], bool]:
    def _ok(row: dict) -> bool:
        return int(row.get("status") or 0) == code

    return _ok


def expect_200_canonical_to(url_or_path: str) -> Callable[[dict], bool]:
    want = url_or_path

    def _ok(row: dict) -> bool:
        if int(row.get("status") or 0) != 200:
            return False
        canon = row.get("canonical") or ""
        return canon.rstrip("/") == want.rstrip("/") or canon.endswith(want)

    return _ok


FAMILY_PROBES = [
    {
        "path": "/sailor/15515",
        "bucket": "page_with_redirect",
        "ok": lambda r: expect_redirect(r, "/sailor/ethan-kruger"),
        "note": "SAS-id sailor → name slug",
    },
    {
        "path": "/sailor/ethan-kruger-15515",
        "bucket": "page_with_redirect",
        "ok": lambda r: expect_redirect(r, "/sailor/ethan-kruger"),
        "note": "legacy name-id sailor → name slug",
    },
    {
        "path": "/class/35-formula-1",
        "bucket": "page_with_redirect",
        "ok": lambda r: expect_redirect(r, "/class/formula-1"),
        "note": "id-prefixed class → slug",
    },
    {
        "path": "/club/FBYC",
        "bucket": "page_with_redirect",
        "ok": lambda r: expect_redirect(r, "/club/fbyc"),
        "note": "uppercase club → lowercase",
    },
    {
        "path": "/home",
        "bucket": "page_with_redirect",
        "ok": lambda r: expect_redirect(r, "/"),
        "note": "/home → /",
    },
    {
        "path": "/regatta",
        "bucket": "page_with_redirect",
        "ok": lambda r: expect_redirect(r, "/events"),
        "note": "/regatta directory → /events",
    },
    {
        "path": "/sailor/unknown",
        "bucket": "not_found_404",
        "ok": expect_status(404),
        "note": "reserved sailor slug stays 404",
    },
    {
        "path": "/boats",
        "bucket": "duplicate_no_canonical",
        "ok": expect_status(200),
        "note": "boats directory 200; add rel=canonical when renderer is patched",
        "gap_if_no_canonical": True,
    },
    {
        "path": "/boat/extra-906",
        "bucket": "duplicate_no_canonical",
        "ok": expect_status(200),
        "note": "boat page 200; add rel=canonical when renderer is patched",
        "gap_if_no_canonical": True,
    },
    {
        "path": "/admin/",
        "bucket": "forbidden_403",
        "ok": expect_status(403),
        "note": "/admin/ stays 403 (slash form after 301)",
    },
    {
        "path": "/index.html",
        "bucket": "alternative_canonical",
        "ok": expect_200_canonical_to("https://sailingsa.co.za"),
        "note": "/index.html canonical → /",
    },
    {
        "path": "/temp-landing",
        "bucket": "alternative_canonical",
        "ok": expect_200_canonical_to("https://sailingsa.co.za"),
        "note": "/temp-landing canonical → /",
    },
    {
        "path": "/class/505",
        "bucket": "soft_404",
        "ok": expect_status(200),
        "note": "thin class Google called Soft 404",
        "gap_if_no_canonical": False,
    },
    {
        "path": "/api/og/sailor/ethan-kruger.png",
        "bucket": "blocked_robots",
        "ok": expect_status(200),
        "note": "OG image must stay 200 (robots Allow)",
    },
    {
        "path": "/api/club-logo/fbyc",
        "bucket": "blocked_robots",
        "ok": expect_status(200),
        "note": "club logo must stay 200 (robots Allow)",
    },
    {
        "path": "/club/abyc",
        "bucket": "google_chose_canonical",
        "ok": expect_200_canonical_to("https://sailingsa.co.za/club/abyc"),
        "note": "lowercase club canonical; Google may still prefer ABYC",
    },
]


def snapshot_total() -> int:
    return sum(int(row.get("pages") or 0) for row in SNAPSHOT)


def snapshot_by_action() -> dict[str, int]:
    out: dict[str, int] = {}
    for row in SNAPSHOT:
        out[row["action"]] = out.get(row["action"], 0) + int(row.get("pages") or 0)
    return out


def probe_families(hit: Callable[[str], dict] | None = None) -> dict:
    do_hit = hit or _hit
    rows = []
    broken = []
    known = []
    for spec in FAMILY_PROBES:
        url = SITE.rstrip("/") + spec["path"]
        raw = do_hit(url)
        raw["canonical"] = _has_canonical(raw.get("body") or b"")
        raw.pop("body", None)
        ok = False
        try:
            ok = bool(spec["ok"](raw))
        except Exception:
            ok = False
        rec = {
            "path": spec["path"],
            "bucket": spec["bucket"],
            "note": spec["note"],
            "status": raw.get("status"),
            "location": raw.get("location") or "",
            "canonical": raw.get("canonical") or "",
            "ok": ok,
            "known": bool(spec.get("known")),
            "error": raw.get("error") or "",
        }
        rows.append(rec)
        if spec.get("gap_if_no_canonical") and not (raw.get("canonical") or ""):
            known.append(rec["path"])
        if not ok:
            broken.append(
                f"{spec['path']} {raw.get('status')} {raw.get('location') or raw.get('error') or ''}".strip()
            )
    return {
        "as_of": datetime.now(SAST).isoformat(),
        "snapshot_date": SNAPSHOT_DATE,
        "gsc_pages": GSC_PAGES,
        "note": (
            "Official API has no Page Indexing report. Counts are the "
            f"{SNAPSHOT_DATE} GSC UI snapshot. Do not click Validate Fix."
        ),
        "snapshot": SNAPSHOT,
        "snapshot_total": snapshot_total(),
        "by_action": snapshot_by_action(),
        "families": rows,
        "broken": broken,
        "known_gaps": known,
    }


def render_lines(payload: dict) -> list[str]:
    lines = [
        f"Page Indexing {payload.get('snapshot_date')}: "
        f"{payload.get('snapshot_total')} excluded URLs "
        f"(not {payload.get('snapshot_total')} good pages waiting)"
    ]
    by = payload.get("by_action") or {}
    lines.append(
        "  keep {keep} | wait {wait} | watch {watch} | fix {fix}".format(
            keep=by.get("keep", 0),
            wait=by.get("wait", 0),
            watch=by.get("watch", 0),
            fix=by.get("fix", 0),
        )
    )
    interesting = (
        "page_with_redirect",
        "not_found_404",
        "crawled_not_indexed",
        "discovered_not_indexed",
        "duplicate_no_canonical",
        "blocked_robots",
    )
    bits = []
    for row in payload.get("snapshot") or []:
        if row["key"] in interesting:
            bits.append(f"{row['pages']} {row['label'].split()[0].lower()}")
    if bits:
        lines.append("  " + " | ".join(bits))
    broken = payload.get("broken") or []
    if broken:
        lines.append("  FAMILY BROKEN: " + "; ".join(broken[:6]))
    else:
        lines.append(
            "  families OK"
            + (
                f" | known gaps {len(payload.get('known_gaps') or [])}"
                if payload.get("known_gaps")
                else ""
            )
        )
    return lines


def write_page_indexing(dest: Path, payload: dict) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "page_indexing.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (dest / "page_indexing.txt").write_text(
        "\n".join(render_lines(payload)) + "\n", encoding="utf-8"
    )
    return path
