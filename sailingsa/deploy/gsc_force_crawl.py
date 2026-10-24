#!/usr/bin/env python3
"""Use every Google API available on the live box to force a crawl."""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

secret = json.loads(Path("/etc/sailingsa/gsc/client_secret.json").read_text())
blk = secret.get("installed") or secret.get("web")
tok = json.loads(Path("/etc/sailingsa/gsc/token.json").read_text())
data = urllib.parse.urlencode(
    {
        "client_id": blk["client_id"],
        "client_secret": blk["client_secret"],
        "refresh_token": tok["refresh_token"],
        "grant_type": "refresh_token",
    }
).encode()
with urllib.request.urlopen(
    urllib.request.Request("https://oauth2.googleapis.com/token", data=data), timeout=20
) as resp:
    access = json.loads(resp.read())["access_token"]
print("token_ok file_scopes", tok.get("scopes"))


def call(method: str, url: str, body=None):
    headers = {"Authorization": "Bearer " + access, "Content-Type": "application/json"}
    payload = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=payload, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")[:400]


site = urllib.parse.quote("sc-domain:sailingsa.co.za", safe="")
for feed in (
    "https://sailingsa.co.za/sitemap-roundups.xml",
    "https://sailingsa.co.za/sitemap-news.xml",
):
    url = "https://www.googleapis.com/webmasters/v3/sites/%s/sitemaps/%s" % (
        site,
        urllib.parse.quote(feed, safe=""),
    )
    status, raw = call("PUT", url, {})
    print("SITEMAP_PUT", feed.rsplit("/", 1)[-1], status, raw.replace("\n", " ")[:180])

for url in (
    "https://sailingsa.co.za/sailing-roundup/latest/",
    "https://sailingsa.co.za/sailing-roundup/",
    "https://sailingsa.co.za/sailing-roundup/issues/2026-10-19/",
):
    status, raw = call(
        "POST",
        "https://indexing.googleapis.com/v3/urlNotifications:publish",
        {"url": url, "type": "URL_UPDATED"},
    )
    print("INDEXING", url, status, raw.replace("\n", " ")[:180])

for feed in (
    "https://sailingsa.co.za/sitemap-roundups.xml",
    "https://sailingsa.co.za/sitemap-news.xml",
    "https://sailingsa.co.za/sitemap.xml",
):
    ping = "https://www.google.com/ping?sitemap=" + urllib.parse.quote(feed, safe="")
    try:
        with urllib.request.urlopen(ping, timeout=15) as resp:
            print("PING", feed.rsplit("/", 1)[-1], resp.status)
    except urllib.error.HTTPError as exc:
        print("PING", feed.rsplit("/", 1)[-1], exc.code)

urls = [
    "https://sailingsa.co.za/sailing-roundup/latest/",
    "https://sailingsa.co.za/sailing-roundup/",
    "https://sailingsa.co.za/sitemap-roundups.xml",
    "https://sailingsa.co.za/sitemap-news.xml",
    "https://sailingsa.co.za/sitemap.xml",
    "https://sailingsa.co.za/sailing-roundup/issues/2026-10-19/",
    "https://sailingsa.co.za/sailing-roundup/issues/2026-10-12/",
    "https://sailingsa.co.za/sailing-roundup/issues/2026-10-05/",
    "https://sailingsa.co.za/sailing-roundup/issues/2026-09-28/",
    "https://sailingsa.co.za/",
    "https://sailingsa.co.za/sailors",
    "https://sailingsa.co.za/about",
    "https://sailingsa.co.za/events",
    "https://sailingsa.co.za/home",
    "https://www.sailingsa.co.za/sailing-roundup/",
]
try:
    xml = urllib.request.urlopen("https://sailingsa.co.za/sitemap-roundups.xml", timeout=20).read().decode()
    extra = [u for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml) if "/issues/" in u]
    extra.sort(reverse=True)
    for url in extra:
        if url not in urls:
            urls.append(url)
except Exception as exc:
    print("sitemap_read", exc)

inspect = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
rows = []
for url in urls:
    status, raw = call(
        "POST",
        inspect,
        {"inspectionUrl": url, "siteUrl": "sc-domain:sailingsa.co.za"},
    )
    verdict = ""
    crawled = ""
    try:
        payload = json.loads(raw)
        idx = (payload.get("inspectionResult") or {}).get("indexStatusResult") or {}
        verdict = idx.get("coverageState") or idx.get("verdict") or ""
        crawled = idx.get("lastCrawlTime") or ""
    except Exception:
        verdict = raw[:80]
    print("INSPECT", status, verdict, crawled, url)
    rows.append({"url": url, "status": status, "verdict": verdict, "lastCrawl": crawled})
    time.sleep(0.12)
Path("/tmp/gsc-inspect-now.json").write_text(json.dumps({"count": len(rows), "results": rows}, indent=2))
print("WROTE", len(rows))
