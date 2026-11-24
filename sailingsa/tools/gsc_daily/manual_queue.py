"""Persistent Search Console manual-request queue. Record only observed outcomes."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .config import (
    IMMINENT_REGATTA_DAYS,
    RECENT_ROUNDUP_DAYS,
    STARVE_AFTER_HOURS,
    server_data_root,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS queue (
    url TEXT PRIMARY KEY,
    seen TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'pending'
);
CREATE TABLE IF NOT EXISTS quota (
    id INTEGER PRIMARY KEY,
    retry_after TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    ts TEXT NOT NULL,
    kind TEXT NOT NULL,
    detail TEXT
);
"""
QUEUE_COLS = (
    "published_at",
    "sitemap_submitted_at",
    "requested_at",
    "request_response",
    "last_crawl",
    "last_inspect",
    "coverage",
    "last_error",
    "attempts",
)
DATE_IN_PATH = re.compile(r"/(\d{4}-\d{2}-\d{2})(?:/|$)")
REGATTA_DATE = re.compile(r"/regatta/(\d{4}-\d{2}-\d{2})(?:-|/|$)")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(ts: datetime | None = None) -> str:
    return (ts or _utcnow()).isoformat()


def connect(root: Path) -> sqlite3.Connection:
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / "manual-indexing.sqlite", timeout=15)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA)
    cols = {row[1] for row in db.execute("PRAGMA table_info(queue)")}
    for col in QUEUE_COLS:
        if col not in cols:
            kind = "INTEGER NOT NULL DEFAULT 0" if col == "attempts" else "TEXT"
            db.execute(f"ALTER TABLE queue ADD COLUMN {col} {kind}")
    qcols = {row[1] for row in db.execute("PRAGMA table_info(quota)")}
    if "reason" not in qcols:
        db.execute("ALTER TABLE quota ADD COLUMN reason TEXT")
    return db


def enqueue(root: Path, urls, *, published_at: str | None = None) -> int:
    seen = published_at or _iso()
    added = 0
    with connect(root) as db:
        for url in urls:
            if urlsplit(url).netloc != "sailingsa.co.za" or not url.startswith("https://"):
                continue
            cur = db.execute(
                "INSERT OR IGNORE INTO queue(url, seen, published_at, state) VALUES (?,?,?,'pending')",
                (url, seen, seen),
            )
            if not cur.rowcount:
                continue
            added += 1
            db.execute(
                "INSERT INTO events(url, ts, kind, detail) VALUES (?,?,?,?)",
                (url, seen, "enqueued", json.dumps({"published_at": seen})),
            )
    return added


def stamp_sitemap(root: Path, urls, submitted_at: str | None = None) -> None:
    ts = submitted_at or _iso()
    with connect(root) as db:
        for url in urls:
            cur = db.execute(
                "UPDATE queue SET sitemap_submitted_at=? WHERE url=? AND sitemap_submitted_at IS NULL",
                (ts, url),
            )
            if cur.rowcount:
                db.execute(
                    "INSERT INTO events(url, ts, kind, detail) VALUES (?,?,?,?)",
                    (url, ts, "sitemap", json.dumps({"sitemap": "https://sailingsa.co.za/sitemap.xml"})),
                )


def log_event(root: Path, url: str, kind: str, detail=None) -> None:
    with connect(root) as db:
        db.execute(
            "INSERT INTO events(url, ts, kind, detail) VALUES (?,?,?,?)",
            (url, _iso(), kind, json.dumps(detail) if not isinstance(detail, str) else detail),
        )


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _path_date(url: str) -> datetime | None:
    path = urlsplit(url).path or ""
    m = REGATTA_DATE.search(path) or DATE_IN_PATH.search(path)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def priority_rank(url: str, now: datetime | None = None) -> int:
    """0 = live/imminent regatta or new roundup, 1 = other event URLs, 2 = rest."""
    now = now or _utcnow()
    path = urlsplit(url).path or ""
    dated = _path_date(url)
    if path.startswith("/regatta/") and dated:
        delta = (dated.date() - now.date()).days
        if -1 <= delta <= IMMINENT_REGATTA_DAYS:
            return 0
        return 1
    if "/sailing-roundup/issues/" in path:
        if dated and (now.date() - dated.date()).days <= RECENT_ROUNDUP_DAYS:
            return 0
        return 1
    if path.startswith("/regatta/") or path.startswith("/sailing-roundup/"):
        return 1
    return 2


def quota_pause(root: Path) -> str | None:
    now = _iso()
    with connect(root) as db:
        row = db.execute(
            "SELECT retry_after FROM quota WHERE id=1 AND retry_after>?", (now,)
        ).fetchone()
        return row["retry_after"] if row else None


def set_quota(root: Path, retry_after: str, reason: str = "") -> None:
    with connect(root) as db:
        db.execute(
            "INSERT OR REPLACE INTO quota(id, retry_after, reason) VALUES (1,?,?)",
            (retry_after, reason),
        )
        db.execute(
            "INSERT INTO events(url, ts, kind, detail) VALUES (?,?,?,?)",
            ("*", _iso(), "quota", json.dumps({"retry_after": retry_after, "reason": reason})),
        )


def clear_quota(root: Path) -> None:
    with connect(root) as db:
        db.execute("DELETE FROM quota WHERE id=1")


def next_urls(root: Path, limit: int = 10) -> list[str]:
    pause = quota_pause(root)
    if pause:
        return []
    now = _utcnow()
    with connect(root) as db:
        rows = list(
            db.execute(
                "SELECT url, seen, requested_at FROM queue WHERE state='pending'"
            )
        )
    if not rows:
        return []
    oldest_row = min(rows, key=lambda r: (_parse_dt(r["seen"]) or now, r["url"]))
    oldest = _parse_dt(oldest_row["seen"]) or now
    starve = (now - oldest) >= timedelta(hours=STARVE_AFTER_HOURS)
    ranked = sorted(
        rows,
        key=lambda r: (priority_rank(r["url"], now), _parse_dt(r["seen"]) or now, r["url"]),
    )
    if starve:
        ranked = [oldest_row] + [r for r in ranked if r["url"] != oldest_row["url"]]
    return [r["url"] for r in ranked[:limit]]


def get_row(root: Path, url: str) -> dict | None:
    with connect(root) as db:
        row = db.execute("SELECT * FROM queue WHERE url=?", (url,)).fetchone()
        return dict(row) if row else None


def set_state(root: Path, url: str, state: str, **fields) -> None:
    assignments = ["state=?"]
    values = [state]
    for key, val in fields.items():
        if key not in QUEUE_COLS and key not in {"seen"}:
            continue
        assignments.append(f"{key}=?")
        values.append(val)
    values.append(url)
    with connect(root) as db:
        cur = db.execute(
            f"UPDATE queue SET {', '.join(assignments)} WHERE url=?", values
        )
        if not cur.rowcount:
            raise KeyError(url)
        db.execute(
            "INSERT INTO events(url, ts, kind, detail) VALUES (?,?,?,?)",
            (url, _iso(), state, json.dumps(fields, default=str)),
        )


def record_inspect(root: Path, url: str, coverage: str, last_crawl: str = "", extra=None) -> None:
    fields = {"last_inspect": _iso(), "coverage": coverage, "last_crawl": last_crawl or None}
    with connect(root) as db:
        db.execute(
            "UPDATE queue SET last_inspect=?, coverage=?, last_crawl=COALESCE(?, last_crawl) WHERE url=?",
            (fields["last_inspect"], coverage, last_crawl or None, url),
        )
        db.execute(
            "INSERT INTO events(url, ts, kind, detail) VALUES (?,?,?,?)",
            (url, fields["last_inspect"], "inspected", json.dumps({"coverage": coverage, "last_crawl": last_crawl, **(extra or {})})),
        )


def record_request(root: Path, url: str, response: str, accepted: bool) -> None:
    ts = _iso()
    state = "accepted" if accepted else "pending"
    with connect(root) as db:
        db.execute(
            """UPDATE queue SET requested_at=?, request_response=?, state=?,
               attempts=COALESCE(attempts,0)+1 WHERE url=?""",
            (ts, response, state if accepted else "pending", url),
        )
        if not accepted:
            db.execute(
                "UPDATE queue SET last_error=? WHERE url=?",
                (response, url),
            )
        db.execute(
            "INSERT INTO events(url, ts, kind, detail) VALUES (?,?,?,?)",
            (
                url,
                ts,
                "accepted" if accepted else "request_response",
                json.dumps({"response": response, "accepted": accepted}),
            ),
        )


def snapshot(root: Path) -> dict:
    now = _iso()
    with connect(root) as db:
        counts = {
            row["state"]: row["n"]
            for row in db.execute("SELECT state, COUNT(*) AS n FROM queue GROUP BY state")
        }
        pause = db.execute(
            "SELECT retry_after, reason FROM quota WHERE id=1 AND retry_after>?", (now,)
        ).fetchone()
        pending = [
            dict(row)
            for row in db.execute(
                "SELECT url, seen, published_at, sitemap_submitted_at, requested_at, "
                "request_response, last_crawl, last_inspect, coverage, last_error, attempts "
                "FROM queue WHERE state='pending' ORDER BY seen, url LIMIT 50"
            )
        ]
        recent = [
            dict(row)
            for row in db.execute(
                "SELECT url, ts, kind, detail FROM events ORDER BY id DESC LIMIT 40"
            )
        ]
        failed = [
            dict(row)
            for row in db.execute(
                "SELECT url, state, last_error, request_response, last_inspect, coverage "
                "FROM queue WHERE state IN ('failed','challenge') OR last_error IS NOT NULL "
                "ORDER BY last_inspect DESC LIMIT 20"
            )
        ]
    return {
        "as_of": now,
        "counts": counts,
        "quota_retry_after": pause["retry_after"] if pause else None,
        "quota_reason": pause["reason"] if pause else None,
        "pending": pending,
        "failures": failed,
        "recent_events": recent,
    }


def write_admin_snapshot(root: Path, dest: Path | None = None) -> Path:
    payload = snapshot(root)
    dest = dest or (root / datetime.now().date().isoformat())
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / "manual_indexing.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (root / "manual_indexing.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=["next", "accepted", "indexed", "quota", "failed", "challenge", "status"],
    )
    parser.add_argument("url", nargs="?")
    parser.add_argument("--reason", default="")
    args = parser.parse_args(argv)
    root = server_data_root()
    now = _utcnow()
    if args.action == "status":
        print(json.dumps(snapshot(root), indent=2))
        return 0
    if args.action == "quota":
        set_quota(root, (now + timedelta(hours=24)).isoformat(), args.reason or "daily limit")
        return 0
    if args.action == "next":
        pause = quota_pause(root)
        if pause:
            print("Quota retry after", pause)
            return 0
        for url in next_urls(root, 10):
            print(url)
        return 0
    if not args.url:
        parser.error("URL required")
    set_state(root, args.url, args.action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
