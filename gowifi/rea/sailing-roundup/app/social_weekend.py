#!/usr/bin/env python3
"""Enrich an issue from already-listed social URLs plus the sailor Media-tab tool."""
import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
from social_collect import og_metadata, platform_for
from roundup import render


def run(issue):
    path = ROOT / "issues" / issue / "issue.json"
    data = json.loads(path.read_text())
    collected = []
    for article in data.get("articles") or []:
        urls = list(dict.fromkeys(article.get("sources") or []))
        social = [u for u in urls if platform_for(u)]
        article.setdefault("social_sources", [])
        for url in social:
            meta = og_metadata(url)
            if not meta:
                continue
            collected.append({"event_id": article.get("id"), "source": meta})
            if not any(x.get("url") == url for x in article["social_sources"]):
                article["social_sources"].append(meta)
    out = ROOT / "issues" / issue / "sources" / "social-weekend.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"issue": issue, "social_posts": collected}, indent=2))
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    render(issue)
    print(
        json.dumps(
            {
                "issue": issue,
                "verified_social_posts": len(collected),
                "rendered": str(ROOT / "public" / "issues" / issue / "index.html"),
            }
        )
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--issue", default="2026-09-28")
    args = p.parse_args()
    run(args.issue)
