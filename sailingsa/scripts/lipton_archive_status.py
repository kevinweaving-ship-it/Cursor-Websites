#!/usr/bin/env python3
"""Write Lipton Vakaros archive STATUS.txt (phone SSH + local)."""
from __future__ import annotations

import json
import re
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
SQLITE = ROOT / "data" / "lipton_telemetry.sqlite"
OUT = ROOT / "docs" / "LIPTON_ARCHIVE_STATUS.txt"
SAST = ZoneInfo("Africa/Johannesburg")
# 3-pass finished before this status writer started (R5+ still in the rest job)
KNOWN_3X = {1, 2, 3, 4, 5, 7}
PG_FIRST_LOAD = {
    1: 390096,
    2: 409702,
    3: 371528,
    4: 214240,
    5: 220139,
    6: 332574,
    7: 447777,
    8: 415809,
    9: 361768,
    10: 355022,
}


def tmux_tail() -> str:
    try:
        out = subprocess.check_output(
            [
                "tmux",
                "-f",
                "/exec-daemon/tmux.portal.conf",
                "capture-pane",
                "-t",
                "lipton-archive-rest:0.0",
                "-p",
                "-S",
                "-40",
            ],
            text=True,
            timeout=5,
        )
    except Exception as e:
        return f"(archive pane unread: {e})"
    lines = [ln.rstrip() for ln in out.splitlines() if ln.strip()]
    return "\n".join(lines[-14:])


def sqlite_counts() -> dict[int, int]:
    if not SQLITE.exists():
        return {}
    conn = sqlite3.connect(f"file:{SQLITE}?mode=ro", uri=True)
    rows = conn.execute("SELECT race, COUNT(*) FROM telemetry GROUP BY 1 ORDER BY 1").fetchall()
    conn.close()
    return {int(a): int(b) for a, b in rows}


def parse_state(tail: str) -> dict:
    race = None
    last_pass = None
    pct = None
    finished = False
    if '"sqlite"' in tail and '"races"' in tail and "EXIT:" in tail:
        finished = True
    found = [int(x) for x in re.findall(r'"race":\s*(\d+),\s*"after"', tail)]
    if found:
        race = found[-1]
    for ln in tail.splitlines():
        try:
            rec = json.loads(ln)
        except Exception:
            continue
        if isinstance(rec.get("race"), int) and "after" in rec:
            race = rec["race"]
        if "fetched" in rec and "pass" in rec and "pct" not in rec:
            last_pass = rec.get("pass")
        if "pct" in rec:
            pct = rec.get("pct")
    return {"race": race, "pass": last_pass, "pct": pct, "finished": finished}


def main() -> None:
    now = datetime.now(SAST)
    utc = datetime.now(timezone.utc)
    counts = sqlite_counts()
    tail = tmux_tail()
    st = parse_state(tail)
    if st["finished"]:
        doing = "3-pass fetch FINISHED R1–R10. Next: gzip sqlite + load extra points into live PG."
        left = [
            "gzip full sqlite and scp to /root/lipton-vakaros-archive/",
            "load extra prestart/post-finish pings into public.lipton_telemetry",
            "verify live COUNT(*) = sqlite for R1–R10",
        ]
    else:
        race = st["race"] or 5
        doing = f"3-pass teleapi fetch Race {race}"
        if st["pass"]:
            doing += f" (last completed pass {st['pass']})"
        if st["pct"] is not None:
            doing += f" — current chunk {st['pct']}%"
        left = []
        if st["pct"] is not None:
            left.append(f"finish current pass on R{race} (~{max(0, 100 - float(st['pct'])):.0f}% of this pass)")
        rest = [n for n in (5, 6, 8, 9, 10) if n > race]
        if race in (5, 6, 8, 9, 10):
            left.append(f"finish R{race} remaining passes")
        for n in rest:
            left.append(f"R{n} 3-pass (~8 min each)")
        left.append("gzip full sqlite + scp to live archive dir")
        left.append("load extra pings into public.lipton_telemetry")
        left.append("verify live counts = sqlite")

    lines = [
        "LIPTON 2026 — Vakaros archive STATUS",
        f"Updated: {now.strftime('%Y-%m-%d %H:%M:%S')} SAST  ({utc.strftime('%H:%M:%S')} UTC)",
        "This file is rewritten every 60 seconds.",
        "",
        "PHONE SSH:",
        "  ssh root@102.218.215.253",
        "  cat /root/lipton-vakaros-archive/STATUS.txt",
        "",
        f"DOING NOW: {doing}",
        "",
        "LEFT TO DO",
    ]
    for item in left:
        lines.append(f"- {item}")
    lines += [
        "",
        "DONE",
        "- Firestore full doc in live vakaros_snapshots (id 9, races 1–10)",
        "- R1–R10 already in live public.lipton_telemetry (first load; R7 is complete)",
        "- Disk: /root/lipton-vakaros-archive/ (sqlite.gz, jsonl, R7 jsonl, firestore JSON)",
        "- R7 3-pass complete (447777, pass 2/3 added 0)",
        "- R1–R4 3-pass complete (wider window: 5-min start + endTime)",
        "",
        "Replay/calcs can already use live DB. This pass fills gaps only.",
        "Do not invent GPS. No cron. DEV Live stays off.",
        "",
        "SQLITE (this VM) vs live PG first-load:",
    ]
    for n in range(1, 11):
        flag = "3x-done" if n in KNOWN_3X else "queued/in-progress"
        if st["finished"]:
            flag = "3x-done"
        elif st["race"] == n:
            flag = "IN PROGRESS"
        elif n in KNOWN_3X:
            flag = "3x-done"
        elif st["race"] and n < st["race"] and n in (5, 6, 8, 9, 10):
            flag = "3x-done"
        lines.append(
            f"  R{n:02d}  sqlite={counts.get(n, 0):7d}  live_pg~={PG_FIRST_LOAD.get(n, 0):7d}  {flag}"
        )
    lines += ["", "ARCHIVE PANE (last lines)", tail, ""]
    text = "\n".join(lines) + "\n"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    Path("/tmp/LIPTON_ARCHIVE_STATUS.txt").write_text(text)
    print(OUT)


if __name__ == "__main__":
    main()
