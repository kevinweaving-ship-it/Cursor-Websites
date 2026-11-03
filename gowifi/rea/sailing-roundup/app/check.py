#!/usr/bin/env python3
"""Validate one generated roundup edition without relying on block order."""
import argparse
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def check(issue):
    base = ROOT / "public" / "issues" / issue
    d = json.loads((base / "issue.json").read_text())
    assert d["issue_id"] == issue
    ids = set()
    for a in d.get("articles") or []:
        assert a["id"] not in ids, "duplicate article"
        ids.add(a["id"])
        assert a.get("sources"), "article without sources"
        if a.get("type") == "regatta_report":
            assert any(b.get("type") == "results" for b in a.get("blocks") or []), "missing results"
        for b in a.get("blocks") or []:
            if b.get("type") == "image":
                assert b.get("source_url"), "image without provenance"
                assert b.get("rights_status") in (
                    "licensed",
                    "external_link_only",
                    "source_attributed",
                ), "unapproved image reuse"
                if b.get("rights_status") == "licensed":
                    assert b.get("verified_published_at"), "licensed image lacks publication date"
                    assert b.get("verified_event_id") == a["id"], "image not tied to event"
                    assert dt.date.fromisoformat(b["verified_published_at"][:10]) >= dt.date.fromisoformat(
                        a["id"][:10]
                    ), "image predates event"
    assert (base / "index.html").stat().st_size > 400
    pdf = base / "edition.pdf"
    assert pdf.exists() and pdf.stat().st_size > 1000, "missing PDF"
    landing = ROOT / "public" / "index.html"
    assert landing.exists() and landing.stat().st_size > 200
    return {
        "issue": issue,
        "articles": len(ids),
        "html_bytes": (base / "index.html").stat().st_size,
        "pdf_bytes": pdf.stat().st_size,
        "validated": True,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("issue", nargs="?", default="2026-09-28")
    a = p.parse_args()
    try:
        print(json.dumps(check(a.issue)))
    except Exception as e:
        print(json.dumps({"validated": False, "error": str(e)}))
        sys.exit(1)
