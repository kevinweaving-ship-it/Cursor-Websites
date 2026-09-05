#!/usr/bin/env python3
"""Compare packed Lipton trail JSON to live Vakaros teleapi (round-to-1s).

Exit 0 if every race has missing_vakaros_secs == 0 (we have every Vakaros 1 Hz bin).
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path

EVENT = "Lv9A35uOBSBRmGpHgXtH"
ROOT = Path(__file__).resolve().parents[1] / "sailingsa"
JS = ROOT / "frontend" / "js"


def trail_path(n: int) -> Path:
    return JS / "lipton-dev-trail.json" if n == 4 else JS / f"lipton-dev-trail-r{n}.json"


def fetch_range(after: int, before: int, limit: int = 5000) -> dict:
    q = {"after": after, "before": before, "limit": limit, "division": "J22"}
    url = f"https://teleapi.regatta.app/telemetry/event/{EVENT}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode())


def check_race(race: int) -> dict:
    t = json.loads(trail_path(race).read_text())
    grid = t["grid_start_ts_ms"]
    step = t["step_ms"]
    n = t["n"]
    end = min(t["end_ts_ms"], grid + (n - 1) * step)
    tele: dict[str, set[int]] = defaultdict(set)
    after = grid
    while after <= end:
        before = min(after + 180_000, end + 1)
        body = fetch_range(after, before)
        if not body or not body.get("Fields"):
            after = before
            continue
        idx = {f: i for i, f in enumerate(body["Fields"])}
        chunk = body.get("Rows") or []
        max_ts = after
        for row in chunk:
            ts = row[idx["ts"]]
            max_ts = max(max_ts, ts)
            if row[idx["role"]] != "competitor":
                continue
            if int(row[idx["race_number"]] or 0) != race:
                continue
            if not (grid <= ts <= end):
                continue
            i = int(round((ts - grid) / step))
            if 0 <= i < n:
                tele[row[idx["sail_number"]]].add(i)
        if not chunk:
            after = before
            continue
        after = before if max_ts + 1 <= after else max_ts + 1
        time.sleep(0.006)
    missing = 0
    extra = 0
    for name, b in t["boats"].items():
        ours = {i for i, v in enumerate(b["lat"]) if v is not None}
        tset = tele.get(name, set())
        missing += len(tset - ours)
        extra += len(ours - tset)
    return {"race": race, "missing_vakaros": missing, "extra_ours": extra}


def main() -> int:
    races = range(1, 11)
    if len(sys.argv) > 1:
        races = [int(x) for x in sys.argv[1:]]
    bad = 0
    for race in races:
        r = check_race(race)
        st = "OK" if r["missing_vakaros"] == 0 else "BAD"
        print(f"R{r['race']}: {st} missing_vakaros={r['missing_vakaros']} extra_ours={r['extra_ours']}")
        if r["missing_vakaros"]:
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
