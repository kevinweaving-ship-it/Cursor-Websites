"""Drop 404s and replace sitemap locs that 301 to another public URL.

Runs against 127.0.0.1:8000 with X-Forwarded-Proto so nginx rate limits
are not involved. Does not click GSC Validate Fix.
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse

PUBLIC = "https://sailingsa.co.za"
LOCAL = "http://127.0.0.1:8000"
HOST = "sailingsa.co.za"
WEB = Path("/var/www/sailingsa")
WORKERS = 6
# Static/HTML families 404 on the API port. Only prune DB entity files.
PRUNE_FILES = frozenset({"sitemap-regattas.xml", "sitemap-clubs.xml"})
RESERVED = frozenset(
    {
        "unknown",
        "none",
        "na",
        "n-a",
        "tbc",
        "tba",
        "tbd",
        "unnamed",
        "anonymous",
        "null",
        "undefined",
    }
)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _hit(public_url: str) -> tuple[int, str]:
    path = urlparse(public_url).path or "/"
    req = urllib.request.Request(
        LOCAL + path,
        headers={
            "User-Agent": "SailingSA-Sitemap-Prune/1.0",
            "Host": HOST,
            "X-Forwarded-Proto": "https",
            "X-Forwarded-Host": HOST,
        },
    )
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=20) as resp:
            return resp.status, resp.headers.get("Location") or ""
    except urllib.error.HTTPError as e:
        return e.code, (e.headers.get("Location") if e.headers else "") or ""
    except Exception:
        return 0, ""


def _abs(loc: str) -> str:
    if not loc:
        return ""
    if loc.startswith("/"):
        return PUBLIC + loc.split("?", 1)[0]
    p = urlparse(loc)
    return PUBLIC + (p.path or "/")


def _reserved_path(url: str) -> bool:
    parts = [p for p in (urlparse(url).path or "/").split("/") if p]
    return bool(parts) and parts[-1].lower() in RESERVED


def load_child(path: Path) -> tuple[list[str], dict[str, str], str]:
    xml = path.read_text(encoding="utf-8")
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)
    lm = dict(re.findall(r"<loc>\s*([^<\s]+)\s*</loc>\s*<lastmod>\s*([^<\s]+)\s*</lastmod>", xml))
    return locs, lm, xml


def write_child(path: Path, locs: list[str], lm: dict[str, str], today: str) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    seen = set()
    for u in locs:
        if u in seen:
            continue
        seen.add(u)
        lines.append("  <url>")
        lines.append(f"    <loc>{u}</loc>")
        lines.append(f"    <lastmod>{lm.get(u, today)}</lastmod>")
        lines.append("  </url>")
    lines.append("</urlset>")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def prune(web: Path = WEB) -> dict:
    today = date.today().isoformat()
    children = sorted(web.glob("sitemap-*.xml"))
    report = {"dropped": [], "replaced": [], "kept": 0, "files": {}}
    for child in children:
        if child.name not in PRUNE_FILES:
            continue
        locs, lm, _ = load_child(child)
        pages = [u for u in locs if not u.endswith(".xml")]
        keep: list[str] = []
        to_probe = []
        for u in pages:
            if _reserved_path(u):
                report["dropped"].append({"url": u, "reason": "reserved", "file": child.name})
                continue
            to_probe.append(u)
        results = {}
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futs = {ex.submit(_hit, u): u for u in to_probe}
            for fut in as_completed(futs):
                u = futs[fut]
                results[u] = fut.result()
        for u in to_probe:
            st, loc = results.get(u, (0, ""))
            dest = _abs(loc) if loc else ""
            if st in (301, 302, 307, 308) and dest.startswith(PUBLIC + "/"):
                dest = dest.split("?")[0]
                if dest.rstrip("/") != u.rstrip("/"):
                    if dest not in keep:
                        keep.append(dest)
                        lm.setdefault(dest, today)
                    report["replaced"].append({"from": u, "to": dest, "file": child.name})
                    continue
            if st in (404, 403) or (500 <= int(st) < 600):
                report["dropped"].append({"url": u, "reason": st, "file": child.name})
                continue
            if st == 0:
                keep.append(u)
                continue
            keep.append(u)
        write_child(child, keep, lm, today)
        report["files"][child.name] = len(keep)
        report["kept"] += len(keep)
    return report


if __name__ == "__main__":
    import json

    out = prune()
    print(json.dumps(out, indent=2))
