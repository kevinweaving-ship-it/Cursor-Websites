"""Write the daily GSC diagnosis report. No secrets."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .classify import classify
from .config import ISSUES


def _bucket(issue_key: str, probes: list[dict]) -> dict:
    still_bad = now_200 = redirect_ok = 0
    classes = Counter()
    patterns = Counter()
    examples = []
    for p in probes:
        kind = classify(issue_key, p)
        p["classification"] = kind
        classes[kind] += 1
        patterns[p.get("pattern") or "?"] += 1
        st = p.get("first_status") or p.get("status")
        if p.get("status") == 200 and not p.get("redirects"):
            now_200 += 1
        elif p.get("redirects") and p.get("status") == 200:
            redirect_ok += 1
        else:
            still_bad += 1
        if len(examples) < 8:
            examples.append(
                {
                    "url": p.get("url"),
                    "first_status": st,
                    "final_status": p.get("status"),
                    "final_url": p.get("final_url"),
                    "last_crawl": p.get("last_crawl") or "",
                    "canonical": p.get("canonical") or "",
                    "noindex": p.get("noindex"),
                    "classification": kind,
                    "pattern": p.get("pattern"),
                }
            )
    return {
        "still_bad": still_bad,
        "now_200": now_200,
        "redirect_ok": redirect_ok,
        "classes": dict(classes),
        "patterns": patterns.most_common(8),
        "examples": examples,
        "probes": probes,
    }


def build_report(day: str, pull: dict, tested: dict[str, list[dict]], yesterday: dict | None) -> dict:
    sections = []
    for issue in ISSUES:
        key = issue["key"]
        block = next((i for i in pull.get("issues") or [] if i["key"] == key), None)
        probes = tested.get(key) or []
        stats = _bucket(key, probes)
        ycount = None
        if yesterday:
            y = next((i for i in (yesterday.get("issues") or []) if i.get("key") == key), None)
            ycount = (y or {}).get("google_count")
        sections.append(
            {
                "key": key,
                "label": issue["label"],
                "google_count": (block or {}).get("google_count"),
                "yesterday_count": ycount,
                "urls_supplied": (block or {}).get("urls_supplied") or len(probes),
                "source": (block or {}).get("source"),
                "export_path": (block or {}).get("export_path"),
                "validation_status": (block or {}).get("validation_status") or "",
                **{k: stats[k] for k in ("still_bad", "now_200", "redirect_ok", "classes", "patterns", "examples")},
            }
        )
    return {
        "run_date": day,
        "property": pull.get("property"),
        "auth": "OK",
        "apply_fixes": False,
        "sections": sections,
    }


def write_report(run_path: Path, report: dict) -> Path:
    (run_path / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = [
        f"# GSC daily — {report['run_date']}",
        "",
        f"Property: {report.get('property')}",
        "Fixes applied: NO (retrieval + diagnosis only)",
        "",
    ]
    for s in report["sections"]:
        lines += [
            f"## {s['label']}",
            "",
            f"Google says {s['google_count']}",
            f"Google supplied {s['urls_supplied']} example URLs",
            f"Y currently still not clean: {s['still_bad']}",
            f"Z now 200: {s['now_200']}",
            f"N redirect correctly: {s['redirect_ok']}",
            f"validation: {s['validation_status'] or 'n/a'}",
            f"source: {s['source'] or 'n/a'}",
            f"classes: {s['classes']}",
            f"main patterns = {s['patterns']}",
            "",
        ]
        for ex in s["examples"]:
            lines.append(
                f"- {ex['url']}  first={ex['first_status']} final={ex['final_status']} "
                f"→ {ex['final_url']}  {ex['classification']}  crawl={ex['last_crawl'] or '?'}"
            )
        lines.append("")
    md = run_path / "REPORT.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    return md
