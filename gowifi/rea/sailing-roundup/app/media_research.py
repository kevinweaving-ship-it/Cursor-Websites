#!/usr/bin/env python3
"""Independent, repeatable public web + image discovery. Candidates are never assumed authentic."""
import argparse
import json
import pathlib
import re
import urllib.parse
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parent.parent
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}


def search(query, kind):
    url = (
        "https://news.google.com/rss/search?q="
        if kind == "news"
        else "https://www.bing.com/images/search?q="
        if kind == "images"
        else "https://www.bing.com/search?q="
    ) + urllib.parse.quote(query)
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    if kind == "images":
        for tag in soup.select("a.iusc"):
            try:
                d = json.loads(tag.get("m", "{}"))
                if d.get("purl") and d.get("murl"):
                    out.append(
                        {
                            "title": d.get("t", ""),
                            "source_url": d["purl"],
                            "image_url": d["murl"],
                            "thumbnail": d.get("turl"),
                            "kind": "image",
                        }
                    )
            except (ValueError, TypeError):
                pass
    elif kind == "news":
        root = ET.fromstring(r.text)
        for item in root.findall(".//item"):
            out.append(
                {
                    "title": item.findtext("title") or "",
                    "source_url": item.findtext("link") or "",
                    "snippet": BeautifulSoup(item.findtext("description") or "", "html.parser").get_text(" ", strip=True),
                    "kind": "news",
                    "published": item.findtext("pubDate"),
                }
            )
    else:
        for tag in soup.select("li.b_algo"):
            a = tag.select_one("h2 a")
            if a and a.get("href", "").startswith("http"):
                out.append(
                    {
                        "title": a.get_text(" ", strip=True),
                        "source_url": a["href"],
                        "snippet": tag.get_text(" ", strip=True)[:450],
                        "kind": "article",
                    }
                )
    return out


def terms_from_event(event: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", (event or "").lower())
    skip = {"the", "and", "for", "with", "from", "2026", "2025", "sailing"}
    out = [w for w in words if w not in skip and len(w) > 2]
    if "sailing" not in out:
        out.append("sailing")
    return out[:10] or ["sailing", "regatta"]


def score(item, terms):
    txt = (item.get("title", "") + " " + item.get("source_url", "") + " " + item.get("snippet", "")).lower()
    return sum(3 if x in txt else 0 for x in terms)


def research(issue, event, queries):
    folder = ROOT / "issues" / issue / "sources"
    folder.mkdir(parents=True, exist_ok=True)
    seen = set()
    found = []
    errors = []
    event_terms = terms_from_event(event)
    for q in queries:
        for kind in ("web", "images", "news"):
            try:
                for item in search(q, kind):
                    url = item["source_url"]
                    if url in seen:
                        continue
                    seen.add(url)
                    item["query"] = q
                    item["relevance_score"] = score(item, event_terms)
                    item["status"] = "candidate_unverified"
                    item["publication_rights"] = "unknown"
                    blob = (item["title"] + " " + item["source_url"]).lower()
                    if item["relevance_score"] >= 6 and not any(
                        k in blob for k in ("fifa", "world cup", "soccer", "football", "wikipedia.org/wiki/2026")
                    ):
                        found.append(item)
            except Exception as e:
                errors.append({"query": q, "kind": kind, "error": str(e)[:200]})
    found.sort(key=lambda x: x["relevance_score"], reverse=True)
    result = {"event": event, "queries": queries, "candidates": found, "errors": errors, "verified": False}
    dest = folder / (event + "-media-research.json")
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return {
        "file": str(dest),
        "candidates": len(found),
        "images": sum(x["kind"] == "image" for x in found),
        "errors": len(errors),
        "top": found[:5],
    }


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--issue", default="2026-09-28")
    a.add_argument("--event", required=True)
    a.add_argument("--query", action="append", required=True)
    args = a.parse_args()
    print(json.dumps(research(args.issue, args.event, args.query), ensure_ascii=False))
