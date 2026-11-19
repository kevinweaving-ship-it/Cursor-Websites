"""Publish gates + acceptance checks from the bulletproof playbook."""

from __future__ import annotations

from sailingsa.roundup.lint import fact_check, lint_text


def run_gates(payload: dict) -> list[dict]:
    failures: list[dict] = []
    cards = payload.get("cards") or []
    awaiting = payload.get("awaiting") or []
    all_html = []
    if cards:
        lead = cards[0]
        if "df95" not in lead["event_id"] and payload["week"] == "2026-10-26":
            failures.append({"id": "T3", "msg": "DF95 must lead 2026-10-26"})
        if "provisional" in lead["copy"]["headline"].lower() and lead["status"]["status"] == "final":
            failures.append({"id": "T1", "msg": "headline says provisional on a final item"})
    for sheet in awaiting:
        if sheet.get("slot") != "awaiting":
            failures.append({"id": "T12", "msg": f"{sheet['event_id']} has no results but is not awaiting"})
        if sheet["event_id"] in {c["event_id"] for c in cards}:
            failures.append({"id": "T12", "msg": "awaiting event also got a card slot"})
    for sheet in cards:
        blob = " ".join([sheet["copy"]["headline"], sheet["copy"]["kicker"], sheet["copy"]["deck"], *sheet["copy"]["paras"]])
        all_html.append(blob)
        for hit in lint_text(blob):
            failures.append({"id": "T7", "event": sheet["event_id"], "msg": hit})
        for hit in fact_check(blob, sheet):
            failures.append({"id": "T-fact", "event": sheet["event_id"], "msg": hit})
        if sheet["event_id"].startswith("2026-10-24-hmyc-dam-bottle"):
            tags = " ".join(sheet.get("class_tags") or [])
            if "DART 18" in sheet["copy"]["kicker"] and "PY" not in tags:
                failures.append({"id": "T5", "msg": "Dam Bottle kicker leaked one-design chips"})
            if "consistency" not in blob.lower() and "R1" not in blob:
                failures.append({"id": "T-angle", "msg": "Dam Bottle missing race-score angles"})
        if "ullman" in sheet["event_id"] and "provisional" in sheet["copy"]["headline"].lower():
            failures.append({"id": "T10", "msg": "Ullman series final still labelled provisional"})
        if "ullman" in sheet["event_id"] and "DART 18" in sheet["copy"]["kicker"]:
            failures.append({"id": "T5", "msg": "Ullman kicker contaminated with Dam Bottle classes"})
        if any(q in blob for q in ("Series overall", "23 May", "Lake Deneys - LDYC", "Henley Midmar - HMYC")):
            failures.append({"id": "T7", "event": sheet["event_id"], "msg": "raw DB label leak"})
        quotes_outlet = any(s.get("kind") in {"article", "gallery", "official_results"} for s in sheet.get("sources") or [])
        if "df95" in sheet["event_id"] and not any("radiosailing.org.au" in (s.get("url") or "") or "mysailingresults" in (s.get("url") or "") for s in sheet.get("sources") or []):
            failures.append({"id": "T8", "msg": "DF95 card missing official/ARYA source link"})
        if not sheet.get("sources"):
            failures.append({"id": "T8", "event": sheet["event_id"], "msg": "empty sources footer"})
        if (sheet.get("image") or {}).get("kind") == "grey":
            failures.append({"id": "T14", "msg": "grey image box"})
        if sheet.get("conflicts") and "68 sailors and 20 races" in blob and "71" not in blob:
            failures.append({"id": "T9", "msg": "published both conflict numbers without reconcile"})
    if payload["week"] == "2026-10-26":
        if not any("nw-youth" in (s["event_id"]) for s in awaiting):
            failures.append({"id": "T12", "msg": "NW Youth must be awaiting, not a card"})
        if any("nw-youth" in c["event_id"] for c in cards):
            failures.append({"id": "T12", "msg": "NW Youth received a card slot"})
        df95 = next((c for c in cards if "df95" in c["event_id"]), None)
        if df95 and df95.get("conflicts"):
            # T9: detector fired; body must not treat 68 and 71 as equal current facts.
            ok = "count_conflict_noted" in df95["status"]["flags"] or df95["status"]["status"] == "under_review"
            if not ok:
                failures.append({"id": "T9", "msg": "68 vs 71 conflict did not flag"})
    return failures


def assert_idempotent(hash_a: str, hash_b: str) -> None:
    if hash_a != hash_b:
        raise AssertionError("T15: rebuild on unchanged week produced a new hash")
