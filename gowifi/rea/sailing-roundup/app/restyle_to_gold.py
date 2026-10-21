#!/usr/bin/env python3
"""Restyle existing issues to the 2026-09-28 gold default.

Does not rebuild 2026-09-28. Does not invent results. Re-renders HTML/PDF
from the stored issue.json using gold chrome, title, and decks.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

from roundup import GOLD_ISSUE_TITLE, render

GOLD_LOCK = "2026-09-28"
NON_GOLD_DEFAULTS = ("2026-10-05", "2026-10-12", "2026-10-19")
DECK_TAIL = re.compile(
    r"(?P<venue>.+?)\s*·\s*(?P<nett>[\d.]+)\s*nett(?:\s*·\s*(?P<entries>\d+)\s*entries)?",
    re.I,
)


def _issue_json(issue: str) -> pathlib.Path:
    for path in (ROOT / "issues" / issue / "issue.json", ROOT / "public" / "issues" / issue / "issue.json"):
        if path.exists():
            return path
    raise FileNotFoundError(f"no issue.json for {issue}")


def gold_deck(article: dict) -> str:
    deck = article.get("deck") or ""
    match = DECK_TAIL.search(deck)
    if match:
        venue = (match.group("venue") or "").split(" · ")[-1].strip()
        nett = (match.group("nett") or "").replace(".0", "")
        bits = [venue]
        if nett:
            bits.append(f"{nett} nett")
        if match.group("entries"):
            bits.append(f"{match.group('entries')} entries")
        return " · ".join(x for x in bits if x)
    return deck


def restyle_issue(issue: str) -> dict:
    if issue == GOLD_LOCK:
        raise ValueError("refusing to restyle the gold default 2026-09-28")
    src = _issue_json(issue)
    data = json.loads(src.read_text())
    data["title"] = GOLD_ISSUE_TITLE
    for article in data.get("articles") or []:
        if article.get("type") == "feature":
            article["headline"] = GOLD_ISSUE_TITLE
            article["kicker"] = "SAILING"
        elif article.get("type") == "regatta_report":
            article["deck"] = gold_deck(article)
    src.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    public = ROOT / "public" / "issues" / issue
    public.mkdir(parents=True, exist_ok=True)
    (public / "issue.json").write_text(src.read_text())
    render(issue)
    html = (public / "index.html").read_text()
    if "The Weekend Roundup" not in html or "--accent:#8b6c43" not in html.replace(" ", ""):
        raise SystemExit(f"{issue} did not render gold chrome")
    if "folio" in html and "class='folio'" in html:
        raise SystemExit(f"{issue} still has folio chrome")
    return {"issue": issue, "action": "restyled_gold", "html": str(public / "index.html")}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--issue", action="append", default=[])
    p.add_argument("--non-gold", action="store_true", help="Restyle 2026-10-05, 10-12, 10-19 only")
    args = p.parse_args()
    issues = list(args.issue)
    if args.non_gold or not issues:
        issues = list(NON_GOLD_DEFAULTS)
    out = []
    for issue in issues:
        out.append(restyle_issue(issue))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
