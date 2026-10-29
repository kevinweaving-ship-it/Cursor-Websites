#!/usr/bin/env python3
"""Audit every public URL we publish + known aliases.

Rules:
- Sitemap URLs must be 200, self-canonical, no noindex, no redirect.
- Alias URLs must 301/308 to a sitemap URL that itself is 200.
- Redirect chains must not loop, must not land on 404/5xx, max 1 hop preferred.
- Do not click GSC Validate Fix.
"""
from __future__ import annotations

import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

SITE = "https://sailingsa.co.za"
UA = "SailingSA-URL-Audit/1.0"
CTX = ssl.create_default_context()
OUT = Path("/var/lib/sailingsa/gsc-daily/url-audit")
WORKERS = 16
TIMEOUT = 20


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HeadParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.canonical = ""
        self.robots = ""
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        d = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "link" and "canonical" in d.get("rel", "").lower():
            self.canonical = d.get("href", "")
        if tag.lower() == "meta" and d.get("name", "").lower() == "robots":
            self.robots = d.get("content", "")
        if tag.lower() == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def opener():
    return urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=CTX))


def hit(url: str, method: str = "GET", max_body: int = 80_000) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    req.method = method
    t0 = time.time()
    try:
        with opener().open(req, timeout=TIMEOUT) as resp:
            body = resp.read(max_body) if method == "GET" else b""
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return {
                "status": resp.status,
                "location": hdrs.get("location") or "",
                "xrobots": hdrs.get("x-robots-tag") or "",
                "ctype": hdrs.get("content-type") or "",
                "body": body,
                "ms": int((time.time() - t0) * 1000),
            }
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read(40_000)
        except Exception:
            pass
        hdrs = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
        return {
            "status": e.code,
            "location": hdrs.get("location") or "",
            "xrobots": hdrs.get("x-robots-tag") or "",
            "ctype": hdrs.get("content-type") or "",
            "body": body,
            "ms": int((time.time() - t0) * 1000),
        }
    except Exception as e:
        return {
            "status": 0,
            "location": "",
            "xrobots": "",
            "ctype": "",
            "body": b"",
            "error": f"{type(e).__name__}: {e}",
            "ms": int((time.time() - t0) * 1000),
        }


def abs_url(maybe: str, base: str) -> str:
    if not maybe:
        return ""
    if maybe.startswith("/"):
        return SITE + maybe
    return urljoin(base, maybe)


def parse_head(body: bytes) -> tuple[str, str, str]:
    p = HeadParser()
    try:
        p.feed(body.decode("utf-8", "replace"))
    except Exception:
        pass
    return (p.canonical or "").strip(), (p.robots or "").strip(), (p.title or "").strip()


def fetch_locs(url: str) -> list[str]:
    raw = hit(url, max_body=4_000_000)
    xml = (raw.get("body") or b"").decode("utf-8", "replace")
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)


def load_sitemap() -> dict[str, list[str]]:
    index = fetch_locs(SITE + "/sitemap.xml")
    families: dict[str, list[str]] = {}
    all_urls: list[str] = []
    for child in index:
        name = child.rstrip("/").rsplit("/", 1)[-1]
        locs = fetch_locs(child)
        # child sitemaps list page URLs; skip nested sitemap indexes
        pages = [u for u in locs if not u.endswith(".xml")]
        families[name] = pages
        all_urls.extend(pages)
    # unique preserve order
    seen = set()
    uniq = []
    for u in all_urls:
        if u in seen:
            continue
        seen.add(u)
        uniq.append(u)
    families["_all"] = uniq
    families["_index"] = index
    return families


def follow_chain(url: str, limit: int = 6) -> dict:
    hops = []
    current = url
    seen = set()
    final_status = 0
    final_url = url
    body = b""
    xrobots = ""
    for _ in range(limit):
        if current in seen:
            hops.append({"url": current, "status": -1, "location": "", "loop": True})
            return {
                "url": url,
                "hops": hops,
                "final_url": current,
                "final_status": -1,
                "loop": True,
                "canonical": "",
                "robots": "",
                "title": "",
                "xrobots": "",
            }
        seen.add(current)
        raw = hit(current)
        loc = raw.get("location") or ""
        hops.append(
            {
                "url": current,
                "status": raw.get("status"),
                "location": loc,
                "error": raw.get("error") or "",
            }
        )
        final_status = int(raw.get("status") or 0)
        final_url = current
        body = raw.get("body") or b""
        xrobots = raw.get("xrobots") or ""
        if final_status in (301, 302, 307, 308) and loc:
            current = abs_url(loc, current)
            continue
        break
    canon, robots, title = parse_head(body)
    return {
        "url": url,
        "hops": hops,
        "final_url": final_url,
        "final_status": final_status,
        "loop": False,
        "canonical": canon,
        "robots": robots,
        "title": title,
        "xrobots": xrobots,
        "hop_count": max(0, len(hops) - 1),
    }


def classify_sitemap_row(row: dict, sitemap: set[str]) -> list[str]:
    issues = []
    if row.get("loop"):
        issues.append("redirect_loop")
    st = int(row.get("final_status") or 0)
    hops = row.get("hops") or []
    first = hops[0] if hops else {}
    first_st = int(first.get("status") or 0)
    if first_st in (301, 302, 307, 308):
        issues.append("sitemap_url_redirects")
    if st == 0:
        issues.append("fetch_error")
    elif 500 <= st < 600:
        issues.append("server_error_5xx")
    elif st == 404:
        issues.append("not_found_404")
    elif st == 403:
        issues.append("forbidden_403")
    elif st not in (200,):
        if first_st not in (301, 302, 307, 308):
            issues.append(f"status_{st}")
    if st == 200:
        self = row["url"].rstrip("/")
        final = (row.get("final_url") or "").rstrip("/")
        if final and final != self:
            issues.append("sitemap_url_redirects")
        canon = (row.get("canonical") or "").strip()
        if not canon:
            issues.append("missing_canonical")
        else:
            c = canon.rstrip("/")
            if c not in (self, row["url"]) and abs_url(canon, row["url"]).rstrip("/") not in (
                self,
                row["url"].rstrip("/"),
            ):
                issues.append("canonical_mismatch")
        robots = (row.get("robots") or "") + " " + (row.get("xrobots") or "")
        if re.search(r"\bnoindex\b", robots, re.I):
            issues.append("noindex_on_sitemap_url")
        title = (row.get("title") or "").lower()
        if "not found" in title or "temporarily unavailable" in title:
            issues.append("soft_or_error_title")
    if int(row.get("hop_count") or 0) > 1:
        issues.append("multi_hop")
    dest = row.get("final_url") or ""
    if dest and dest.rstrip("/") not in {u.rstrip("/") for u in sitemap} and first_st in (
        301,
        302,
        307,
        308,
    ):
        issues.append("redirect_to_non_sitemap")
    return issues


def classify_alias_row(row: dict, sitemap: set[str]) -> list[str]:
    issues = []
    if row.get("loop"):
        issues.append("redirect_loop")
        return issues
    hops = row.get("hops") or []
    first_st = int((hops[0] or {}).get("status") or 0) if hops else 0
    st = int(row.get("final_status") or 0)
    if first_st not in (301, 302, 307, 308):
        if st == 200:
            issues.append("alias_still_200")
        elif st == 404:
            issues.append("alias_404")
        elif 500 <= st < 600:
            issues.append("server_error_5xx")
        elif st == 0:
            issues.append("fetch_error")
        else:
            issues.append(f"alias_status_{st}")
        return issues
    if st == 404:
        issues.append("redirect_to_404")
    elif 500 <= st < 600:
        issues.append("redirect_to_5xx")
    elif st != 200:
        issues.append(f"redirect_to_{st}")
    dest = (row.get("final_url") or "").rstrip("/")
    sm = {u.rstrip("/") for u in sitemap}
    if dest and dest not in sm and dest.rstrip("/") + "/" not in sitemap:
        # allow trailing-slash normalisation onto a sitemap URL
        if dest.rstrip("/") not in sm:
            issues.append("redirect_to_non_sitemap")
    if int(row.get("hop_count") or 0) > 2:
        issues.append("multi_hop")
    return issues


CORE_ALIASES = [
    SITE + "/home",
    SITE + "/index.html",
    SITE + "/index",
    SITE + "/regatta",
    SITE + "/regatta/",
    SITE + "/sailor",
    SITE + "/sailor/",
    SITE + "/club",
    SITE + "/club/",
    SITE + "/class",
    SITE + "/class/",
    SITE + "/results",
    SITE + "/events/",
    SITE + "/sailors/",
    SITE + "/clubs/",
    SITE + "/classes/",
    "https://www.sailingsa.co.za/",
    "https://www.sailingsa.co.za/events",
    "http://sailingsa.co.za/",
]


def extra_aliases_from_sitemap(urls: list[str]) -> list[str]:
    """Club case variants + trailing-slash samples. Full sailor SAS-id set comes from DB."""
    out = []
    slash_budget = {"sailor": 0, "regatta": 0, "class": 0, "club": 0}
    for u in urls:
        path = urlparse(u).path or "/"
        parts = [p for p in path.split("/") if p]
        if len(parts) != 2:
            continue
        kind, rest = parts[0], parts[1]
        if kind == "club":
            if rest != rest.upper():
                out.append(SITE + "/club/" + rest.upper())
            if rest != rest.lower():
                out.append(SITE + "/club/" + rest.lower())
        if kind in slash_budget and slash_budget[kind] < 8:
            out.append(SITE + path + "/")
            slash_budget[kind] += 1
    seen = set()
    uniq = []
    for u in out:
        if u in seen:
            continue
        seen.add(u)
        uniq.append(u)
    return uniq


def db_aliases() -> list[str]:
    """Historical public aliases that must 301 to a living sitemap URL."""
    url = os.environ.get("DB_URL") or ""
    if not url:
        return []
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        return []
    out: list[str] = []
    conn = psycopg2.connect(url)
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            """
            SELECT DISTINCT BTRIM(s.sa_sailing_id::text) AS sas_id
            FROM sas_id_personal s
            WHERE s.sa_sailing_id IS NOT NULL
              AND EXISTS (
                SELECT 1 FROM results r
                WHERE r.helm_sa_sailing_id::text = s.sa_sailing_id::text
                   OR r.crew_sa_sailing_id::text = s.sa_sailing_id::text
              )
            """
        )
        for r in cur.fetchall() or []:
            sas = (r.get("sas_id") or "").strip()
            if sas.isdigit():
                out.append(SITE + "/sailor/" + sas)
        cur.execute(
            """
            SELECT class_id, class_name FROM classes
            WHERE class_id IS NOT NULL AND class_name IS NOT NULL
            """
        )
        for r in cur.fetchall() or []:
            cid = r.get("class_id")
            name = (r.get("class_name") or "").strip()
            if cid is None or not name:
                continue
            slug = re.sub(r"[^\w\s\-]", "", name.lower().replace("&", " and "))
            slug = re.sub(r"\s+", "-", slug)
            slug = re.sub(r"-+", "-", slug).strip("-")
            if slug:
                out.append(SITE + f"/class/{cid}-{slug}")
    finally:
        conn.close()
    return out


def sample_class_id_aliases() -> list[str]:
    """Live class pages often 301 from /class/{id}-{slug}."""
    return [
        SITE + "/class/35-formula-1",
        SITE + "/class/39-hobie-14",
    ]


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    families = load_sitemap()
    sitemap_urls = families["_all"]
    sitemap_set = set(sitemap_urls)
    print(f"SITEMAP {len(sitemap_urls)} across {len(families)-2} children", flush=True)

    aliases = list(CORE_ALIASES)
    aliases.extend(extra_aliases_from_sitemap(sitemap_urls))
    aliases.extend(sample_class_id_aliases())
    db_a = db_aliases()
    print(f"DB_ALIASES {len(db_a)}", flush=True)
    aliases.extend(db_a)
    # known SAS-id / name-id sailor aliases from earlier Googlebot logs
    aliases.extend(
        [
            SITE + "/sailor/15515",
            SITE + "/sailor/ethan-kruger-15515",
            SITE + "/sailor/michael-nel-13571",
            SITE + "/sailor/unknown",
            SITE + "/temp-landing",
            SITE + "/dev-1",
            SITE + "/boats",
            SITE + "/boat/extra-906",
            SITE + "/rankings",
            SITE + "/signup.html",
        ]
    )
    seen_a = set()
    alias_urls = []
    for u in aliases:
        if u in seen_a or u in sitemap_set:
            continue
        seen_a.add(u)
        alias_urls.append(u)
    print(f"ALIASES {len(alias_urls)}", flush=True)

    sitemap_rows = []
    alias_rows = []

    def work(url: str) -> dict:
        return follow_chain(url)

    print("PROBING sitemap…", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(work, u): u for u in sitemap_urls}
        done = 0
        for fut in as_completed(futs):
            row = fut.result()
            row["issues"] = classify_sitemap_row(row, sitemap_set)
            row["role"] = "sitemap"
            sitemap_rows.append(row)
            done += 1
            if done % 250 == 0:
                print(f"  sitemap {done}/{len(sitemap_urls)}", flush=True)

    print("PROBING aliases…", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(work, u): u for u in alias_urls}
        done = 0
        for fut in as_completed(futs):
            row = fut.result()
            row["issues"] = classify_alias_row(row, sitemap_set)
            row["role"] = "alias"
            alias_rows.append(row)
            done += 1
            if done % 250 == 0:
                print(f"  alias {done}/{len(alias_urls)}", flush=True)

    def bucket(rows):
        c = {}
        for r in rows:
            if not r.get("issues"):
                c["ok"] = c.get("ok", 0) + 1
            for i in r.get("issues") or []:
                c[i] = c.get(i, 0) + 1
        return c

    summary = {
        "sitemap_n": len(sitemap_rows),
        "alias_n": len(alias_rows),
        "sitemap_issues": bucket(sitemap_rows),
        "alias_issues": bucket(alias_rows),
        "families": {k: len(v) for k, v in families.items() if not k.startswith("_")},
        "broken_sitemap": [
            {"url": r["url"], "status": r["final_status"], "issues": r["issues"], "canonical": r.get("canonical")}
            for r in sitemap_rows
            if r.get("issues")
        ],
        "broken_alias": [
            {
                "url": r["url"],
                "status": r["final_status"],
                "final": r.get("final_url"),
                "issues": r["issues"],
                "hops": r.get("hops"),
            }
            for r in alias_rows
            if r.get("issues")
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (OUT / "sitemap_rows.json").write_text(
        json.dumps(
            [
                {k: v for k, v in r.items() if k != "hops" or r.get("issues")}
                for r in sitemap_rows
            ],
            indent=2,
        )
        + "\n"
    )
    (OUT / "alias_rows.json").write_text(json.dumps(alias_rows, indent=2) + "\n")
    lines = [
        f"SITEMAP {summary['sitemap_n']} issues={ {k:v for k,v in summary['sitemap_issues'].items() if k!='ok'} }",
        f"  ok {summary['sitemap_issues'].get('ok',0)}",
        f"ALIASES {summary['alias_n']} issues={ {k:v for k,v in summary['alias_issues'].items() if k!='ok'} }",
        f"  ok {summary['alias_issues'].get('ok',0)}",
        f"families {summary['families']}",
        "",
        "SITEMAP BROKEN (first 40)",
    ]
    for r in summary["broken_sitemap"][:40]:
        lines.append(f"  {r['status']} {r['issues']} {r['url']}")
    lines.append("")
    lines.append("ALIAS BROKEN (first 40)")
    for r in summary["broken_alias"][:40]:
        lines.append(f"  {r['status']} {r['issues']} {r['url']} -> {r['final']}")
    (OUT / "REPORT.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines), flush=True)
    print(f"SAVED {OUT}", flush=True)
    return summary


if __name__ == "__main__":
    run()
