#!/usr/bin/env python3
"""Backfill Hansekop meter history from raw_dps.jsonl into Arial ingest.

Does not print tokens. Reads ARIAL_METER_INGEST_TOKEN from /etc/tuya-sharing.env.
"""
from __future__ import annotations

import json
import sqlite3
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SAST = ZoneInfo("Africa/Johannesburg")
METER = "bf90676b1341ecb34dse39"
JSONL = Path("/opt/tuya-sharing/state/raw_dps.jsonl")
SQLITE = Path("/var/www/sailingsa/data/arial_meter_history.sqlite")
ENV = Path("/etc/tuya-sharing.env")
INGEST = "http://127.0.0.1:8003/api/arial/meter/ingest"
# GR2PWS scales
DP_V, DP_A, DP_W, DP_ELE, DP_WH = 20, 18, 19, 17, 102


def env_token() -> tuple[str, str]:
    url = INGEST
    token = ""
    for ln in ENV.read_text().splitlines():
        if ln.startswith("ARIAL_METER_INGEST_TOKEN="):
            token = ln.split("=", 1)[1].strip().strip("\"'")
        if ln.startswith("ARIAL_INGEST_URL="):
            url = ln.split("=", 1)[1].strip().strip("\"'") or url
    if not token:
        raise SystemExit("missing ingest token")
    return url, token


def last_sqlite_ts() -> float:
    con = sqlite3.connect(str(SQLITE))
    row = con.execute("SELECT max(ts) FROM readings WHERE device=?", (METER,)).fetchone()
    con.close()
    return float(row[0] or 0)


def last_sqlite_kwh() -> float:
    con = sqlite3.connect(str(SQLITE))
    row = con.execute(
        "SELECT kwh FROM readings WHERE device=? AND kwh IS NOT NULL ORDER BY ts DESC LIMIT 1",
        (METER,),
    ).fetchone()
    con.close()
    return float(row[0] or 0)


def samples_from_jsonl(after_ts: float) -> list[dict]:
    v = a = w = None
    kwh = last_sqlite_kwh()
    out: list[dict] = []
    last_emit = after_ts
    with JSONL.open() as f:
        for line in f:
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            wall = float(o.get("wall") or 0)
            if wall <= after_ts:
                continue
            dp = o.get("dpId")
            val = o.get("value")
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                continue
            if dp == DP_V:
                v = val / 100.0
            elif dp == DP_A:
                a = val / 1000.0
            elif dp == DP_W:
                w = val / 100.0
            elif dp == DP_ELE:
                kwh = round(kwh + val / 100.0, 3)
            if w is None:
                continue
            if wall - last_emit < 25:
                continue
            out.append(
                {
                    "ts": wall,
                    "online": True,
                    "v": round(v, 3) if v is not None else None,
                    "a": round(a, 3) if a is not None else None,
                    "w": round(w, 3),
                    "kwh": kwh,
                }
            )
            last_emit = wall
    return out


def post(url: str, token: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    url, token = env_token()
    after = last_sqlite_ts()
    pts = samples_from_jsonl(after)
    print("after_ts", datetime.fromtimestamp(after, SAST).isoformat() if after else None)
    print("points", len(pts))
    if not pts:
        print("nothing to backfill")
        return 0
    # Keep current reading separate so history chunks stay dense.
    now_pt = pts[-1]
    hist = pts[:-1]
    chunk = 500
    sent = 0
    for i in range(0, len(hist), chunk):
        batch = hist[i : i + chunk]
        payload = {
            "device": METER,
            "src": "sharing",
            "ts": now_pt["ts"],
            "online": True,
            "v": now_pt.get("v"),
            "a": now_pt.get("a"),
            "w": now_pt.get("w"),
            "kwh": now_pt.get("kwh"),
            "history": batch,
        }
        # If last history point is old, ingest still accepts it within 7 days.
        out = post(url, token, payload)
        sent += len(batch)
        print("chunk", i, "n", len(batch), "ok", out.get("ok"), "integrated", out.get("samplesIntegrated"))
        time.sleep(0.2)
    print("sent_history", sent, "current_kwh", now_pt.get("kwh"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
