"""Single-worker Search Console Request-indexing processor.

Inspect first (API + visible UI). Mark accepted only when Google confirms.
Acceptance and verified indexing stay separate. Do not use undocumented endpoints.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import MANUAL_INDEX_LOCK, REQUEST_DEDUP_HOURS, server_data_root
from .manual_queue import (
    connect,
    get_row,
    log_event,
    next_urls,
    quota_pause,
    record_inspect,
    record_request,
    set_quota,
    set_state,
    write_admin_snapshot,
)

SAST = ZoneInfo("Africa/Johannesburg")
WRAPPER = Path("/usr/local/sbin/sailingsa-gsc-manual-index")
KEVIN_ACTION = "KEVIN-ACTION.txt"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(ts: datetime | None = None) -> str:
    return (ts or _utcnow()).isoformat()


def acquire_lock(root: Path):
    path = root / MANUAL_INDEX_LOCK
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    handle.seek(0)
    handle.truncate()
    handle.write(_iso())
    handle.flush()
    return handle


def wake_worker() -> None:
    """Fire the deployed oneshot without waiting. Duplicate workers no-op on the lock."""
    cmd = None
    if WRAPPER.is_file():
        cmd = [str(WRAPPER), "--budget", "8"]
    else:
        cmd = [
            sys.executable,
            "-m",
            "sailingsa.tools.gsc_daily.manual_index_worker",
            "--budget",
            "8",
        ]
    env = os.environ.copy()
    env.setdefault("PYTHONPATH", "/opt/sailingsa-gsc")
    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        env=env,
    )


def _alert_kevin(root: Path, action: str, extra: dict | None = None) -> Path:
    dest = root / datetime.now(SAST).date().isoformat()
    dest.mkdir(parents=True, exist_ok=True)
    payload = {
        "as_of": datetime.now(SAST).isoformat(),
        "action": action,
        **(extra or {}),
    }
    (dest / KEVIN_ACTION).write_text(action.strip() + "\n", encoding="utf-8")
    (root / KEVIN_ACTION).write_text(action.strip() + "\n", encoding="utf-8")
    (dest / "challenge.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (root / "challenge.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    write_admin_snapshot(root, dest)
    return dest / KEVIN_ACTION


def _coverage_indexed(coverage: str) -> bool:
    low = (coverage or "").lower()
    if "not indexed" in low or "unknown" in low:
        return False
    return low in ("submitted and indexed", "indexed", "url is on google") or "is on google" in low


def _inspect_api(url: str) -> dict:
    from .server_api import inspect_url
    from .server_auth import access_token

    token = access_token()
    result = inspect_url(token, url)
    st = result.get("indexStatusResult") or {}
    return {
        "coverage": st.get("coverageState") or "",
        "verdict": st.get("verdict") or "",
        "last_crawl": st.get("lastCrawlTime") or "",
        "canonical": st.get("googleCanonical") or "",
        "raw": result,
    }


def reconcile_accepted(root: Path | None = None, limit: int = 40) -> dict:
    """URL Inspection API follow-up. Does not click Request indexing."""
    root = root or server_data_root()
    out = {"checked": [], "now_indexed": [], "error": ""}
    try:
        from .server_auth import access_token
        from .server_api import inspect_url

        token = access_token()
    except Exception as exc:
        out["error"] = f"{type(exc).__name__}: {exc}"[:240]
        return out
    with connect(root) as db:
        rows = list(
            db.execute(
                "SELECT url FROM queue WHERE state='accepted' ORDER BY requested_at LIMIT ?",
                (limit,),
            )
        )
    for row in rows:
        url = row["url"]
        try:
            result = inspect_url(token, url)
            st = result.get("indexStatusResult") or {}
            coverage = st.get("coverageState") or ""
            last_crawl = st.get("lastCrawlTime") or ""
            record_inspect(root, url, coverage, last_crawl, extra={"source": "api_reconcile"})
            if _coverage_indexed(coverage):
                set_state(root, url, "indexed", last_crawl=last_crawl, coverage=coverage)
                out["now_indexed"].append(url)
            out["checked"].append({"url": url, "coverage": coverage, "last_crawl": last_crawl})
        except Exception as exc:
            out["checked"].append({"url": url, "error": f"{type(exc).__name__}: {exc}"[:200]})
    write_admin_snapshot(root)
    return out


def _recent_request(row: dict | None) -> bool:
    if not row:
        return False
    raw = row.get("requested_at") or ""
    if not raw:
        return False
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return False
    return _utcnow() - ts < timedelta(hours=REQUEST_DEDUP_HOURS)


def process_url(session, root: Path, url: str) -> dict:
    row = get_row(root, url) or {}
    result = {
        "url": url,
        "ts": _iso(),
        "api_coverage": "",
        "google_response": "",
        "accepted": False,
        "indexed": False,
    }
    try:
        api = _inspect_api(url)
        result["api_coverage"] = api.get("coverage") or ""
        record_inspect(root, url, result["api_coverage"], api.get("last_crawl") or "", extra={"source": "api"})
        if _coverage_indexed(result["api_coverage"]):
            set_state(
                root,
                url,
                "indexed",
                last_crawl=api.get("last_crawl") or "",
                coverage=result["api_coverage"],
            )
            result["indexed"] = True
            result["google_response"] = result["api_coverage"]
            return result
    except Exception as exc:
        result["api_error"] = f"{type(exc).__name__}: {exc}"[:240]

    if _recent_request(row) and (row.get("state") == "accepted"):
        result["google_response"] = "already accepted; skipped duplicate request"
        return result
    if _recent_request(row) and not _coverage_indexed(result["api_coverage"]):
        # Clicked recently but not confirmed — inspect UI only, do not click again.
        result["dedup"] = True

    ui = session.inspect_and_request(url, dest=root, skip_click=bool(result.get("dedup")))
    result["google_response"] = ui.get("google_response") or ui.get("outcome") or ""
    result["ui_coverage"] = ui.get("coverage") or ""
    result["snippet"] = ui.get("snippet") or ""
    record_inspect(root, url, ui.get("coverage") or "", extra={"source": "ui", "title": ui.get("title")})
    if ui.get("indexed"):
        set_state(root, url, "indexed", coverage=ui.get("coverage") or "", request_response=result["google_response"])
        result["indexed"] = True
        return result
    if ui.get("accepted"):
        record_request(root, url, result["google_response"], accepted=True)
        result["accepted"] = True
        return result
    if result.get("dedup"):
        result["google_response"] = result["google_response"] or "waiting for Google confirmation"
        return result
    record_request(root, url, result["google_response"] or "no confirmation", accepted=False)
    set_state(root, url, "failed", last_error=result["google_response"] or "no confirmation")
    return result


def run(*, budget: int = 8, root: Path | None = None, reconcile_only: bool = False) -> dict:
    root = root or server_data_root()
    payload = {
        "as_of": datetime.now(SAST).isoformat(),
        "processed": [],
        "stopped": "",
        "quota_retry_after": quota_pause(root),
        "lock": True,
    }
    handle = acquire_lock(root)
    if handle is None:
        payload["lock"] = False
        payload["stopped"] = "another worker holds the lock"
        return payload
    try:
        recon = reconcile_accepted(root)
        payload["reconcile"] = {"checked": len(recon.get("checked") or []), "now_indexed": recon.get("now_indexed") or []}
        if reconcile_only:
            write_admin_snapshot(root)
            return payload
        pause = quota_pause(root)
        if pause:
            payload["stopped"] = f"quota pause until {pause}"
            write_admin_snapshot(root)
            return payload
        urls = next_urls(root, budget)
        if not urls:
            payload["stopped"] = "empty"
            write_admin_snapshot(root)
            return payload
        from .chrome_gsc import ChromeSession, NeedKevin, QuotaHit

        try:
            with ChromeSession() as session:
                for url in urls:
                    try:
                        row = process_url(session, root, url)
                        payload["processed"].append(row)
                    except QuotaHit as exc:
                        retry = exc.retry_after or (_utcnow() + timedelta(hours=24)).isoformat()
                        set_quota(root, retry, str(exc)[:240])
                        payload["stopped"] = "quota"
                        payload["quota_retry_after"] = retry
                        payload["quota_message"] = str(exc)[:400]
                        log_event(root, url, "quota", {"message": str(exc)[:400], "retry_after": retry})
                        break
                    except NeedKevin as exc:
                        log_event(root, url, "challenge", {"action": exc.action, "hostpath": exc.hostpath})
                        path = _alert_kevin(
                            root,
                            exc.action,
                            {"url": url, "hostpath": exc.hostpath, "title": exc.title, "shot": exc.shot},
                        )
                        payload["stopped"] = "need_kevin"
                        payload["kevin_action"] = exc.action
                        payload["kevin_file"] = str(path)
                        payload["hostpath"] = exc.hostpath
                        payload["title"] = exc.title
                        payload["shot"] = exc.shot
                        break
        except NeedKevin as exc:
            path = _alert_kevin(root, exc.action, {"hostpath": exc.hostpath, "title": exc.title, "shot": exc.shot})
            payload["stopped"] = "need_kevin"
            payload["kevin_action"] = exc.action
            payload["kevin_file"] = str(path)
        except RuntimeError as exc:
            path = _alert_kevin(root, f"Search Console Chrome failed: {exc}"[:400])
            payload["stopped"] = "need_kevin"
            payload["kevin_action"] = str(exc)[:400]
            payload["kevin_file"] = str(path)
        write_admin_snapshot(root)
        return payload
    finally:
        try:
            fcntl.flock(handle, fcntl.LOCK_UN)
        finally:
            handle.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Process the GSC manual-indexing queue")
    ap.add_argument("--budget", type=int, default=8)
    ap.add_argument("--reconcile-only", action="store_true")
    ap.add_argument("--data-root", default="")
    args = ap.parse_args(argv)
    root = Path(args.data_root) if args.data_root else server_data_root()
    payload = run(budget=args.budget, root=root, reconcile_only=args.reconcile_only)
    print(json.dumps({k: payload[k] for k in payload if k != "processed"}, indent=2))
    for row in payload.get("processed") or []:
        print(
            "{ts} {url} api={api} google={g} accepted={a} indexed={i}".format(
                ts=row.get("ts"),
                url=row.get("url"),
                api=(row.get("api_coverage") or "")[:40],
                g=(row.get("google_response") or "")[:80].replace("\n", " "),
                a=row.get("accepted"),
                i=row.get("indexed"),
            )
        )
    if payload.get("stopped") == "need_kevin":
        print("STOP_NEED_KEVIN", payload.get("kevin_action"))
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
